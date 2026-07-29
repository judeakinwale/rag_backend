import logging
import httpx
from rag_packages.shared.processing.qdrant import QdrantService, ScoredPoint
from rag_packages.shared.ai.openai import (
    OpenAIService,
    OpenAIResponse,
    OpenAIStreamResponse,
    Response,
    ActorRole,
    ResponseMethod,
    # ___________________
    ResponseStreamEvent,
    ChatCompletionChunk,
)
from rag_packages.contracts.dto.document import (
    DocumentListAPIResponse,
    DocumentResponse,
)
from rag_packages.contracts.dto.chat import (
    AddPromptRequest,
    CreateChatRequest,
    ChatMessage,
    OpenAIChatMessage,
    ChatMessageReferences,
    UpdateChatRequest,
    ChatResponse,
)
from rag_packages.contracts.dto.vector_document import VectorDocumentResponse
from rag_packages.shared.exception.exception import BadRequestException

from app.core.config import settings
from app.services.chat_service import ChatService, Chat
from app.services.prompt_builder_service import PromptBuilder
from rag_packages.shared.utils.format import dicts_to_markdown

# from app.repositories.chat_repository import ChatRepository


logger = logging.getLogger(__name__)

# Query Rewriter
# Document Search Service (PostgreSQL)
# Vector Search Service
# Context Builder
# Prompt Builder
# OpenAI Service


class RagService:
    _rewrite_instructions = (
        "You are a helpful assistant that rewrites user queries to be more specific and relevant "
        "based on the previous conversation context. "
        "You should use the previous conversation to understand the user's intent and provide a "
        "rewritten query that is clear, concise, and focused on the user's needs. "
        "Do not add any additional information or context that is not present in the previous conversation. "
        "If the previous conversation does not provide enough context, return the original query without changes."
    )

    def __init__(
        self,
        # chat_repository: ChatRepository,
        chat_service: ChatService,
        qdrant_service: QdrantService,
        openai_service: OpenAIService | None = None,
        root_cert_path: str | None = None,
    ):
        # self.chat_repository = chat_repository
        self.chat_service = chat_service
        self.qdrant_service = qdrant_service
        self.openai_service = openai_service
        self.prompt_builder = PromptBuilder()

        self.root_cert_path = (
            root_cert_path if root_cert_path is not None else settings.ROOT_CERT_PATH
        )
        self._ingest_service_origin = settings.INGEST_SERVICE_ORIGIN
        self._get_documents_path = settings.GET_DOCUMENTS_PATH

    # rewrite might be expensive, so added skip flag for testing and debugging
    async def _rewrite_query(
        self, query: str, prev_conversation: list[ChatMessage], enabled: bool = False
    ) -> str:
        if not enabled:
            return query

        if self.openai_service is None:
            logger.warning("OpenAI service is not initialized.")
            return query

        valid_prev_conversation = [
            OpenAIChatMessage.model_validate(
                message.model_dump(exclude_unset=True, exclude_none=True)
            )
            for message in prev_conversation
        ]

        response: Response = await self.openai_service.create_response(
            prompt=query,
            instructions=self._rewrite_instructions,
            prev_conversation=valid_prev_conversation,
        )
        rewritten_query = response.output_text
        return rewritten_query

    def _get_last_prompt(self, messages: list[ChatMessage]) -> str:
        if not messages:
            return ""

        last_message = messages[-1]
        if isinstance(last_message.content, str):
            return last_message.content

        last_prompt_list = [
            part.get("text", "")
            for part in last_message.content
            if part.get("type") == "input_text"
        ]
        last_prompt = " ".join(last_prompt_list)

        return last_prompt

    def _update_last_prompt(
        self,
        prompt: str,
        messages: list[ChatMessage],
        references: ChatMessageReferences | None = None,
    ) -> list[ChatMessage]:
        if not messages or not prompt:
            return messages

        last_message = messages[-1]
        if isinstance(last_message.content, str):
            last_message.content = prompt
            return messages

        for part in last_message.content:
            if part.get("type") == "input_text":
                part["text"] = prompt
                break

        if references:
            last_message.references = references

        return messages

    async def get_query_matching_documents(
        self, query: str, limit: int = 5
    ) -> list[DocumentResponse]:
        print({"root_cert_path": self.root_cert_path})
        async with httpx.AsyncClient(verify=self.root_cert_path, timeout=30) as client:
            print(
                {
                    "get_documents_url": f"{self._ingest_service_origin}/{self._get_documents_path}",
                    "ingest_service_origin": self._ingest_service_origin,
                    "get_documents_path": self._get_documents_path,
                }
            )
            response = await client.get(
                f"{self._ingest_service_origin}/{self._get_documents_path}",
                params={"query": query, "limit": limit},
            )
            response.raise_for_status()
            response_json = response.json()

            doc_response = DocumentListAPIResponse.model_validate(response_json)
            documents = doc_response.data if doc_response.data is not None else []
            return documents

    async def _get_matching_documents(
        self, query: str | list[str], limit: int = 5
    ) -> list[DocumentResponse]:
        is_list = isinstance(query, list)
        queries = query if is_list else [query]

        documents: list[DocumentResponse] = []
        for query_item in queries:
            docs = await self.get_query_matching_documents(
                query=query_item, limit=limit
            )
            documents.extend(docs)

        return documents

    async def _get_matching_vector_documents(
        self, query: str | list[str], limit: int = 5
    ) -> list[ScoredPoint]:
        """
        Retrieve the limit most relevant documents from the vector database based on the query.
        """
        points = await self.qdrant_service.search(query=query, limit=limit)
        return points

    def _get_point_payload(self, point: ScoredPoint) -> VectorDocumentResponse:
        payload = point.payload
        return VectorDocumentResponse.model_validate(payload)

    def _get_vector_doc_details(
        self, doc: VectorDocumentResponse, exclude_keys: list[str] | None = None
    ) -> dict:
        details = doc.details.model_dump() if doc.details else {}

        if exclude_keys:
            for key in exclude_keys:
                if key in details:
                    del details[key]

        return details

    # build markdown context strings from the retrieved documents and vector documents
    async def _build_document_context(
        self, query: str | list[str], limit: int = 5
    ) -> tuple[str, ChatMessageReferences]:

        points = await self._get_matching_vector_documents(query=query, limit=limit)
        payloads = [self._get_point_payload(point) for point in points]
        documents = await self._get_matching_documents(query=query, limit=limit)

        # TODO: add the payload details and the document metadata to the context
        # Look into moving this into prompt_builder

        vector_doc_markdown = dicts_to_markdown(
            [
                self.chat_service.normalize_chat_message_vector_documents(
                    payload
                ).model_dump()
                for payload in payloads
            ],
            ["text", "file_metadata"],
            section_title="Retrieved Vector Documents",
            subtitle_key="file_name",
        )

        vector_doc_details_markdown = dicts_to_markdown(
            [self._get_vector_doc_details(payload) for payload in payloads],
            ["pages", "headings", "captions"],  # , "tables", "figures"
            section_title="Retrieved Vector Document Details",
            subtitle_key="headings",
        )

        # documents_markdown = dicts_to_markdown(
        #     [self.chat_service.normalize_chat_message_documents(doc).model_dump() for doc in documents],
        #     ["text", "file_metadata"],
        #     section_title="Retrieved Document References",
        #     subtitle_key="file_name",
        # )

        context = f"{vector_doc_markdown}\n{vector_doc_details_markdown}\n"
        # context = (
        #     f"{'\n'.join([payload.text for payload in payloads])} \n"
        #     f"{'\n'.join([str(payload.details.model_dump()) for payload in payloads])} \n"
        #     f"{'\n'.join([str(payload.file_metadata.model_dump()) for payload in payloads])} \n"
        #     # f"{'\n'.join([document.file_metadata for document in documents])} \n"
        # )

        references = ChatMessageReferences(
            vector_documents=payloads,
            documents=documents or [],
        )

        return context, references

    def _get_response_text(self, response: OpenAIResponse) -> str:
        response_text = getattr(response, "output_text", None)
        # the response is of type Response
        if response_text is not None:
            return response_text

        choices = getattr(response, "choices", None) or []
        # the response is of type ChatCompletion
        if choices and choices[0].message.content:
            return choices[0].message.content

        raise BadRequestException("OpenAI service returned an empty chat response.")

    def _get_stream_event_text(self, event: ResponseStreamEvent) -> str:
        text: str = ""

        match event.type:
            case "response.output_text.delta":
                text = event.delta

            case "response.completed":
                msg = "OpenAI service returned a completed response: response streaming completed."
                logger.info(msg)
                # response = event.response
                # text = response.output_text
                # completed = True

            case "response.failed":
                default_err_msg = "OpenAI service returned a failed response."
                raise RuntimeError(event.response.error or default_err_msg)

        if text:
            # TODO: stream the text to the frontend using websockets or SSE (Server-Sent Events)
            pass

        return text

    def _get_chat_chunk_text(self, chunk: ChatCompletionChunk) -> str:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            return ""

        delta = getattr(choices[0], "delta", None)

        text = getattr(delta, "content", "") or ""
        if text:
            # TODO: stream the text to the frontend using websockets or SSE (Server-Sent Events)
            pass

        return text

    async def _stream_response_text(
        self,
        stream: OpenAIStreamResponse,
        response_method: ResponseMethod = ResponseMethod.RESPONSE,
    ) -> str:

        text_parts: list[str] = []
        async for event in stream:
            if response_method == ResponseMethod.CHAT_COMPLETION:
                text = self._get_chat_chunk_text(event)
            else:
                text = self._get_stream_event_text(event)

            if text:
                text_parts.append(text)

        response_text = "".join(text_parts).strip()
        if response_text:
            return response_text

        raise BadRequestException("OpenAI service returned an empty chat response.")

    # TODO: rewrite this and _append_assistant_reply to be less redundant later
    # ? should this and _append_assistant_reply be merged
    async def _generate_assistant_message(
        self,
        conversation: list[ChatMessage],
        *,
        prompt: str | None = None,
        instructions: str | None = None,
        file_url: str | None = None,
        b64_file: str | None = None,
        file_mime_type: str | None = None,
        stream: bool = False,
        references: ChatMessageReferences | None = None,
    ) -> ChatMessage:
        if self.openai_service is None:
            raise BadRequestException(
                "OpenAI service is not configured for chat responses."
            )

        valid_conversation = [
            OpenAIChatMessage.model_validate(message).model_dump(
                exclude_unset=True, exclude_none=True
            )
            for message in conversation
        ]
        print({"valid_conversation": valid_conversation})

        if prompt is not None:
            response = await self.openai_service.create_response(
                prompt=prompt,
                prev_conversation=valid_conversation,
                instructions=instructions,
                file_url=file_url,
                b64_file=b64_file,
                b64_file_mime_type=file_mime_type,
                stream=stream,
            )
        else:
            response = await self.openai_service.create_response(
                conversation=valid_conversation,
                instructions=instructions,
                stream=stream,
            )

        if stream:
            response_text = await self._stream_response_text(response)
        else:
            response_text = self._get_response_text(response)

        return self.prompt_builder.create_chat_message(
            role=ActorRole.ASSISTANT, content=response_text, references=references
        )

    async def _append_assistant_reply(
        self,
        messages: list[ChatMessage],
        *,
        prompt: str | None = None,
        file_url: str | None = None,
        b64_file: str | None = None,
        file_mime_type: str | None = None,
        # use messages as previous conversation context
        # the new prompt is already added to the messages list, so exclude it (the last message)
        # ? this seems dumb, the openai_service already handles the previous conversation
        use_prev_conversation: bool = False,
        references: ChatMessageReferences | None = None,
    ) -> list[ChatMessage]:
        assistant_message = await self._generate_assistant_message(
            messages if not use_prev_conversation else messages[:-1],
            prompt=prompt,
            file_url=file_url,
            b64_file=b64_file,
            file_mime_type=file_mime_type,
            references=references,
        )
        return [*messages, assistant_message]

    # TODO: rewrite this later to return only the document context as markdown for use as instructions
    async def _prepare_prompt(
        self, prompt: str | None = None, messages: list[ChatMessage] | None = None
    ) -> tuple[str, list[ChatMessage], ChatMessageReferences]:
        if prompt is None and not messages:
            raise BadRequestException(
                "A prompt and / or conversation messages must be provided."
            )

        # add documents, context and or rewritten prompt
        last_prompt = prompt or self._get_last_prompt(messages)
        messages = messages or []
        messages_copy: list[ChatMessage] = []

        rewritten_prompt = await self._rewrite_query(last_prompt, messages)

        document_context, references = await self._build_document_context(
            rewritten_prompt, limit=10
        )

        updated_prompt = f"""
## User Question

-------
{rewritten_prompt}

## Context
-------

### Retrieved Knowledge
-------

The following information comes from a knowledge base. Use it to answer the question.

{document_context}
"""

        if messages:
            messages_copy = self.prompt_builder.copy_messages(messages)
            messages_with_context = self._update_last_prompt(
                updated_prompt, messages_copy
            )

        return updated_prompt, messages_with_context, references

    async def _add_file_to_last_message(
        self,
        messages: list[ChatMessage],
        b64_file: str,
        b64_file_type: str | None = None,
    ) -> list[ChatMessage]:
        # update the last message content with a file if a b64 file is provided
        file = await self.openai_service._create_file(
            b64_file_str=b64_file, b64_file_type=b64_file_type
        )
        b64_file_id = file.id

        if isinstance(messages[-1].content, str):
            messages[-1].content = [
                {"type": "input_text", "text": messages[-1].content},
                {"type": "input_file", "file_id": b64_file_id},
            ]
        else:
            messages[-1].content.append({"type": "input_file", "file_id": file.id})

        return messages

    async def _init_chat_messages(
        self,
        messages: list[ChatMessage],
        b64_file: str | None = None,
        b64_file_type: str | None = None,
    ) -> list[ChatMessage]:
        if not messages:
            return []

        # # add documents, context and or rewritten prompt
        # last_prompt = self._get_last_prompt(messages)
        # rewritten_prompt = await self._rewrite_query(last_prompt, messages)

        # document_context, references = await self._build_document_context(rewritten_prompt, limit=5)
        # updated_prompt = f"{rewritten_prompt}\n\n{document_context}"

        # messages_copy = self.prompt_builder.copy_messages(messages)
        # messages_copy = self._update_last_prompt(updated_prompt, messages_copy)

        # messages = await self._append_assistant_reply(messages_copy)
        # return messages

        if b64_file is not None:
            messages = await self._add_file_to_last_message(
                messages, b64_file, b64_file_type=b64_file_type
            )

        prompt, messages_with_context, references = await self._prepare_prompt(
            messages=messages
        )

        assistant_message = await self._generate_assistant_message(
            messages_with_context, references=references
        )
        messages = [*messages, assistant_message]

        return messages

    async def _update_chat_messages(
        self,
        existing_messages: list[ChatMessage],
        payload: UpdateChatRequest,
        b64_file: str | None = None,
        b64_file_type: str | None = None,
    ) -> list[ChatMessage]:
        existing_messages = self.prompt_builder.copy_messages(existing_messages)
        replacement_messages = self.prompt_builder.copy_messages(payload.messages)
        has_replacement_messages = bool(replacement_messages)

        merged_messages = existing_messages or []
        if has_replacement_messages:
            merged_messages = replacement_messages

        if payload.new_messages:
            merged_messages.extend(payload.new_messages)

        if merged_messages and (has_replacement_messages or payload.new_messages):
            # # add documents, context and or rewritten prompt
            # last_prompt = self._get_last_prompt(merged_messages)
            # rewritten_prompt = await self._rewrite_query(last_prompt, merged_messages)

            # document_context, references = await self._build_document_context(
            #     rewritten_prompt, limit=5
            # )
            # updated_prompt = f"{rewritten_prompt}\n\n{document_context}"

            # merged_messages_copy = self.prompt_builder.copy_messages(merged_messages)
            # merged_messages_copy = self._update_last_prompt(
            #     updated_prompt, merged_messages_copy
            # )

            # merged_messages = await self._append_assistant_reply(merged_messages_copy)

            if b64_file is not None:
                merged_messages = await self._add_file_to_last_message(
                    merged_messages,
                    b64_file or payload.b64_file,
                    b64_file_type=b64_file_type or payload.b64_file_type,
                )

            prompt, messages_with_context, references = await self._prepare_prompt(
                messages=merged_messages
            )

            assistant_message = await self._generate_assistant_message(
                messages_with_context, references=references
            )
            merged_messages = [*merged_messages, assistant_message]

        return merged_messages

    async def _prepare_create_payload(
        self, payload: CreateChatRequest, b64_file: str | None = None
    ) -> CreateChatRequest:
        messages = await self._init_chat_messages(
            payload.messages,
            b64_file=payload.b64_file,
            b64_file_type=payload.b64_file_type,
        )

        return CreateChatRequest(
            email=payload.email,
            messages=messages,
            session_id=payload.session_id,
            site_url=payload.site_url,
        )

    async def _prepare_update_payload(
        self, existing_messages: list[ChatMessage], payload: UpdateChatRequest
    ) -> UpdateChatRequest:
        merged_messages = await self._update_chat_messages(
            existing_messages,
            payload,
            b64_file=payload.b64_file,
            b64_file_type=payload.b64_file_type,
        )

        return UpdateChatRequest(
            email=payload.email,
            messages=merged_messages,
            session_id=payload.session_id,
            site_url=payload.site_url,
        )

    async def process_prompt(
        self,
        payload: AddPromptRequest,
        existing_messages: list[ChatMessage] | None = None,
        generate_assistant_message: bool = True,
        b64_file: str | None = None,
        b64_file_type: str | None = None,
    ) -> tuple[UpdateChatRequest, ChatMessageReferences]:
        existing_messages = existing_messages or []
        updated_messages = self.prompt_builder.copy_messages(existing_messages)

        # # add documents, context and or rewritten prompt
        # initial_prompt = f"{payload.prompt}"
        # rewritten_prompt = await self._rewrite_query(initial_prompt, existing_messages)

        # document_context, references = await self._build_document_context(rewritten_prompt, limit=5)
        # updated_prompt = f"{rewritten_prompt}\n\n{document_context}"

        file_id: str | None = None
        if b64_file is not None:
            file = await self.openai_service._create_file(
                b64_file_str=b64_file, b64_file_type=b64_file_type
            )
            file_id = file.id

        # store the initial prompt, unchanged in payload, in the messages list
        new_message = self.prompt_builder.create_chat_message(
            role=ActorRole.USER,
            content=self.prompt_builder.build_prompt_content(payload, file_id=file_id),
        )
        updated_messages.append(new_message)

        # # use the updated prompt for the assistant reply
        # updated_messages = await self._append_assistant_reply(
        #     updated_messages,
        #     prompt=updated_prompt,
        #     # prompt=payload.prompt,
        #     file_url=payload.file_url,
        #     b64_file=payload.b64_file,
        #     file_type=payload.file_type,
        #     use_prev_conversation=True,
        # )

        prompt, messages_with_context, references = await self._prepare_prompt(
            # prompt=payload.prompt,
            messages=updated_messages
        )

        if generate_assistant_message:
            assistant_message = await self._generate_assistant_message(
                messages_with_context, references=references
            )
            updated_messages = [*updated_messages, assistant_message]

        update_payload = UpdateChatRequest(messages=updated_messages)

        return update_payload, references

    async def create_chat(
        self,
        payload: CreateChatRequest,
        process_messages: bool = True,
    ) -> ChatResponse:

        prepared_payload = payload
        if process_messages:
            prepared_payload = await self._prepare_create_payload(payload)

        created_chat = await self.chat_service.create_chat(prepared_payload)
        return created_chat

    async def _get_chat(
        self, chat_id: int | None = None, session_id: str | None = None
    ) -> ChatResponse:
        if chat_id is None and session_id is None:
            raise BadRequestException("Either chat_id or session_id must be provided.")

        if chat_id is not None:
            chat = await self.chat_service.get_chat_by_id(chat_id)
            if not chat:
                raise BadRequestException(f"Chat with ID {chat_id} not found.")
            return chat

        if session_id is not None:
            chat = await self.chat_service.get_chat_by_session_id(session_id)
            if not chat:
                raise BadRequestException(
                    f"Chat with session ID {session_id} not found."
                )
            return chat

        raise RuntimeError("Unexpected error: unable to get chat.")

    async def update_chat(
        self,
        payload: UpdateChatRequest,
        chat_id: int | None = None,
        session_id: str | None = None,
        process_messages: bool = True,
    ) -> ChatResponse:
        existing_chat = await self._get_chat(chat_id, session_id)

        prepared_payload = payload
        if process_messages:
            prepared_payload = await self._prepare_update_payload(
                existing_chat.messages, payload
            )

        updated_chat = await self.chat_service.update_chat(chat_id, prepared_payload)
        return updated_chat

    async def update_chat_with_prompt(
        self,
        payload: AddPromptRequest,
        chat_id: int | None = None,
        session_id: str | None = None,
        update_chat: bool = True,
        generate_assistant_message: bool = True,
    ) -> tuple[ChatResponse, ChatMessageReferences]:
        existing_chat = await self._get_chat(chat_id, session_id)
        print({"existing_chat": existing_chat})
        update_payload, references = await self.process_prompt(
            payload,
            existing_messages=existing_chat.messages,
            generate_assistant_message=generate_assistant_message,
            b64_file=payload.b64_file,
            b64_file_type=payload.file_type,
        )

        if update_chat:
            updated_chat = await self.chat_service.update_chat(
                existing_chat.id, update_payload
            )
        else:
            updated_chat = ChatResponse.model_validate(existing_chat)

        return updated_chat, references
