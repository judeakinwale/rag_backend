import asyncio
import datetime
import logging
import time
from typing import Literal, overload

import httpx
import torch
import torch.nn.functional as F
from app.core.config import settings
from app.services.chat_service import Chat, ChatService
from app.services.prompt_builder_service import PromptBuilder
from app.types.stream import ResponseCompletionFN
from app.utils.build_prompt import (
    RewrittenQuery,
    build_prompt_with_context,
    build_rewrite_prompt,
    parse_rewritten_user_query,
)
from app.utils.skip_words import general_skip_list
from openai import AsyncStream
from openai.types.responses import Response, ResponseInputParam, ResponseStreamEvent
from qdrant_client.http.models import ExtendedPointId
from rag_packages.contracts.dto.chat import (
    AddPromptRequest,
    ChatMessage,
    ChatMessageReferences,
    ChatResponse,
    CreateChatRequest,
    DocumentResponseJSON,
    OpenAIChatMessage,
    UpdateChatRequest,
)
from rag_packages.contracts.dto.document import (
    DocumentListAPIResponse,
    DocumentResponse,
)
from rag_packages.contracts.dto.shared_dto import BaseDTO
from rag_packages.contracts.dto.vector_document import VectorDocumentResponse
from rag_packages.shared.ai.openai import (
    ActorRole,
    ChatCompletionChunk,
    OpenAIResponse,
    OpenAIService,
    OpenAIStreamResponse,
    Response,
    ResponseMethod,
    ResponseStreamEvent,
)
from rag_packages.shared.exception.exception import BadRequestException
from rag_packages.shared.processing.qdrant import QdrantService, ScoredPoint
from rag_packages.shared.utils.format import dicts_to_markdown

# from fastembed import TextEmbedding
# force rebuild

logger = logging.getLogger(__name__)


# ----- example print msg
# f"[rag service - testing - update_chat] process_messages: {process_messages}\n"
# -----

# ----- move these to utils


def decode_escapes(text: str = "") -> str:
    cleaned_str = bytes(text, "utf-8").decode("unicode_escape")
    return cleaned_str


@overload
def update_str(initial: str, new: str, separator: str = "\n") -> str: ...


@overload
def update_str(initial: list[str], new: list[str]) -> list[str]: ...


@overload
def update_str(initial: list[str], new: str) -> list[str]: ...


def update_str(
    initial: str | list[str], new: str | list[str], separator: str = "\n"
) -> str | list[str]:
    is_initial_str = isinstance(initial, str)
    is_new_str = isinstance(new, str)

    if is_new_str:
        if is_initial_str:
            return f"{initial}{separator}{new}\n"

        return initial.append(new)

    return initial.extend(new)


# ----- move these to types


class B64File(BaseDTO):
    name: str | None = None
    content: str
    type: str
    mime_type: str | None = None  # ideally, this is a duplicate of type


# ----- move these


class RagService:
    # _rewrite_instructions = ("")

    # used only for building context for multiple queries
    _query_semaphore = asyncio.Semaphore(12)
    # used for everything else
    _semaphore = asyncio.Semaphore(12)

    def __init__(
        self,
        # chat_repository: ChatRepository,
        chat_service: ChatService,
        qdrant_service: QdrantService,
        openai_service: OpenAIService | None = None,
        root_cert_path: str | None = None,
        skip_list: list[str] = general_skip_list,
    ):
        # self.chat_repository = chat_repository
        self.chat_service = chat_service
        self.qdrant_service = qdrant_service
        self.openai_service = openai_service
        self.prompt_builder = PromptBuilder()

        # # self.model_name = "BAAI/bge-base-en"
        # self.embedding_model = TextEmbedding(
        #     # model_name=self.model_name,
        #     lazy_load=True,
        # )

        self.root_cert_path = (
            root_cert_path if root_cert_path is not None else settings.ROOT_CERT_PATH
        )
        self._ingest_service_origin = settings.INGEST_SERVICE_ORIGIN
        self._get_documents_path = settings.GET_DOCUMENTS_PATH
        self._skip_list = skip_list
        self._skip_list_embeddings: list[list[float]] = []

    # async def _generate_vector_embeddings(self, texts: list[str]) -> list[list[float]]:
    #     if not texts:
    #         raise ValueError(
    #             f"[{self.service_name}] texts are required to generate embeddings."
    #         )

    #     # NOTE: if unstable under heavy concurrency, protect embedding calls with an asyncio.Lock or use a small worker pool.
    #     embeddings = await asyncio.to_thread(
    #         lambda: [
    #             embedding.tolist() for embedding in self.embedding_model.embed(texts)
    #         ]
    #     )
    #     if not embeddings:
    #         raise ValueError(
    #             f"[{self.service_name}] Failed to generate embeddings for the supplied texts."
    #         )

    #     return embeddings

    async def _get_skip_list_embeddings(self) -> list[list[float]]:
        if not self._skip_list_embeddings:
            self._skip_list_embeddings = (
                await self.qdrant_service.generate_vector_embeddings(self._skip_list)
            )

        return self._skip_list_embeddings

    async def _rewrite_query(
        self,
        query: str,
        prev_conversation: list[ChatMessage] | None = None,
        enabled: bool = False,
    ) -> str:
        if not enabled:
            return query

        if self.openai_service is None:
            logger.warning("OpenAI service is not initialized.")
            return query

        if not settings.flag_generate_assistant_message:
            return RewrittenQuery(queries=[query]).model_dump_json()

        rewrite_prompt = build_rewrite_prompt(query, prev_conversation)

        valid_prev_conversation: OpenAIChatMessage | None = None
        if prev_conversation:
            valid_prev_conversation = [
                OpenAIChatMessage.model_validate(message.model_dump())
                for message in prev_conversation
            ]

        # TODO: fix openai_service.create_response to accept and properly manage prev_conversation
        # TODO: add the previous conversation as part of the instructions as sending it directly breaks the code
        response: Response = await self.openai_service.create_response(
            prompt=rewrite_prompt,
            # prev_conversation=valid_prev_conversation or [],
        )

        rewritten_query = self._get_response_text(response)
        return rewritten_query

    # ----- interact with the last message and / or messages

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

    def _append_to_messages(
        self,
        data: str | ChatMessage,
        messages: list[ChatMessage],
        role: ActorRole = ActorRole.ASSISTANT,
        references: ChatMessageReferences | None = None,
    ) -> list[ChatMessage]:
        message = data
        if isinstance(message, str):
            message = self.prompt_builder.create_chat_message(
                role=role, content=data, references=references
            )

        messages.append(message)
        return messages

    # -----

    # ---- fetching context
    # * done
    async def get_matching_documents(
        self, query: str, limit: int = 5
    ) -> list[DocumentResponse]:
        """
        Retrieve the limit most relevant documents (document references) from the database based on the query.
        """
        async with httpx.AsyncClient(verify=self.root_cert_path, timeout=30) as client:
            response = await client.get(
                f"{self._ingest_service_origin}/{self._get_documents_path}",
                params={"query": query, "limit": limit},
            )
            response.raise_for_status()
            response_json = response.json()

            doc_response = DocumentListAPIResponse.model_validate(response_json)
            documents = doc_response.data if doc_response.data is not None else []
            return documents

    # * done
    async def _get_all_matching_documents(
        self, query: str | list[str], limit: int = 5
    ) -> list[DocumentResponse]:
        if not settings.flag_fetch_related_documents:
            return []

        queries = query if isinstance(query, list) else [query]

        if settings.flag_use_asyncio_gather:
            match_tasks = [self.get_matching_documents(q, limit) for q in queries]
            docs_responses = await asyncio.gather(*match_tasks)

            documents = [doc for docs in docs_responses for doc in docs]
            # documents = [*docs for docs in docs_responses] # for python 3.15+
        else:
            documents: list[DocumentResponse] = []
            for q in queries:
                docs = await self.get_matching_documents(q, limit)
                documents.extend(docs)

        return documents

    # * done
    async def _get_matching_vector_documents(
        self, query: str | list[str], limit: int = 5
    ) -> list[ScoredPoint]:
        """
        Retrieve the limit most relevant documents from the vector database based on the query.
        """
        points = await self.qdrant_service.search(query=query, limit=limit)
        return points or []

    # -----

    # * done
    # check if the prompt contains mostly generic and / or skip words and / or phrases
    async def _should_skip_context_building(
        self, prompt: str | None = None, threshold: float = 0.9
    ) -> bool:
        cleaned_prompt = [prompt.strip()] if prompt else None
        if not cleaned_prompt:
            return not cleaned_prompt

        if settings.flag_use_asyncio_gather:
            prompt_embeddings, skip_embeddings = await asyncio.gather(
                self.qdrant_service.generate_vector_embeddings(cleaned_prompt),
                self._get_skip_list_embeddings(),
            )
        else:
            prompt_embeddings = await self.qdrant_service.generate_vector_embeddings(
                cleaned_prompt
            )
            skip_embeddings = await self._get_skip_list_embeddings()

        single_prompt_embedding = prompt_embeddings[0] if prompt_embeddings else None
        prompt_tensor = torch.tensor(single_prompt_embedding)

        for emb in skip_embeddings:
            emb_tensor = torch.tensor(emb)
            score = F.cosine_similarity(
                prompt_tensor.unsqueeze(0), emb_tensor.unsqueeze(0)
            ).item()

            if score >= threshold:
                return True

        return False

    # * done
    # build markdown context strings from the retrieved documents and vector documents
    async def _build_document_context(
        self,
        query: str | list[str],
        limit: int = 100,
        relevance_threshold: float = 0.75,  # 0.8 seems too strict
        min_query_length: int = 8,
        processed_points: list[ExtendedPointId] | None = None,
    ) -> tuple[str, ChatMessageReferences | None]:
        is_query_str = isinstance(query, str)
        query = query.strip() if is_query_str else query

        default_return = f"{query if is_query_str else ', '.join(query)}", None
        extra = {"query": query}

        is_short_query = len(query) < min_query_length if is_query_str else False
        if is_short_query:
            info_msg = "[RagService - _build_document_context] The Query is too short to build any meaningful context. Skipping context building."
            logger.info(info_msg, extra=extra)
            return default_return

        should_skip = await self._should_skip_context_building(query)
        if should_skip:
            info_msg = "[RagService - _build_document_context] The query is too generic or common to build any meaningful context. Skipping context building."
            logger.info(info_msg, extra=extra)
            return default_return

        if settings.flag_use_asyncio_gather:
            points, documents = await asyncio.gather(
                self._get_matching_vector_documents(query=query, limit=limit),
                self._get_all_matching_documents(query=query, limit=limit),
            )
        else:
            points = await self._get_matching_vector_documents(query=query, limit=limit)
            documents = await self._get_all_matching_documents(query=query, limit=limit)

        # ----- utility fns

        def get_point_payload(point: ScoredPoint) -> VectorDocumentResponse:
            payload = point.payload
            return VectorDocumentResponse.model_validate(payload)

        def process_point(
            point: ScoredPoint, processed_points: list[ExtendedPointId] | None
        ) -> VectorDocumentResponse | None:
            if processed_points is not None and point.id not in processed_points:
                processed_points.append(point.id)

            payload = get_point_payload(point)

            if (
                point.score >= relevance_threshold
                and payload.text
                and len(payload.text.strip()) > min_query_length
            ):
                del payload.details.tables
                del payload.details.bbox
                del payload.details.figures
                # del payload.details.captions
                # del payload.details.headings

                return payload

        # -----

        payloads = [
            doc
            for point in points
            if ((doc := process_point(point, processed_points)) is not None)
        ]

        normalize_vector_docs, normalize_docs = (
            self.chat_service.normalize_chat_message_vector_documents,
            self.chat_service.normalize_chat_message_documents,
        )
        vector_docs_markdown = dicts_to_markdown(
            [normalize_vector_docs(payload, True).model_dump() for payload in payloads],
            ["text", "file_metadata", "details_markdown"],
            section_title="Retrieved Vector Documents",
            subtitle_key="file_name",
        )
        docs_markdown = dicts_to_markdown(
            [normalize_docs(doc).model_dump() for doc in documents],
            ["name", "file_url", "file_metadata"],
            section_title="Retrieved Document References",
            subtitle_key="file_name",
        )

        context = f"{vector_docs_markdown}\n{docs_markdown}\n"
        references = ChatMessageReferences(
            vector_documents=payloads, documents=documents
        )

        return context, references

    # ----- OpenAIResponse / ResponseStreamEvent / OpenAIStreamResponse text extraction
    # * done
    def _get_response_text(self, response: OpenAIResponse) -> str:
        if response is None:
            return ""

        if response.output_text:
            return response.output_text

        choice = response.choices[0] if response.choices else None
        if choice and choice.message.content:
            return choice.message.content

        raise BadRequestException("OpenAI service returned an empty chat response.")

    # ------ text / event streaming (UNUSED)

    def _get_stream_event_text(self, event: ResponseStreamEvent) -> str:
        # this is handled in the routes (using utils/stream.py)
        if event.type == "response.output_text.delta":
            return event.delta
        return

    def _get_chat_chunk_text(self, chunk: ChatCompletionChunk) -> str:
        choice = chunk.choices[0] if chunk and chunk.choices else None
        if choice is not None:
            text = choice.delta.content if choice.delta else ""
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

    # ------
    # -----

    # ----- hot path rewrite

    # * done
    def convert_add_prompt_request_to_update_chat_request(
        self, data: AddPromptRequest
    ) -> UpdateChatRequest:
        converted = UpdateChatRequest.model_validate({**data.model_dump()})

        # store the initial prompt, unchanged in data, in the messages list
        new_message = self.prompt_builder.create_chat_message(
            role=ActorRole.USER, content=data.prompt
        )
        converted.new_messages = [new_message]

        # converted.b64_file and converted.b64_file_type is used to create a B64File instance
        file_type: str = data.file_mime_type or data.file_type
        converted.b64_file_type = file_type

        return converted

    # * done
    # ? str context is not updated in memory, only list[str] context is
    async def get_partial_context(
        self,
        query: list[str],
        context: str | list[str],
        references: ChatMessageReferences,
        processed_points: list[ExtendedPointId] | None = None,
        limit: int = 100,
    ) -> tuple[str, ChatMessageReferences]:
        refs = references

        # async with self._query_semaphore:
        _q_context, _q_references = await self._build_document_context(
            query, limit=limit, processed_points=processed_points
        )

        context = update_str(context, _q_context)  # eg. f"{context}\n{_q_context}\n"

        if _q_references is None:
            return context, references

        refs.documents.extend(_q_references.documents)
        refs.document_chunks.extend(_q_references.document_chunks)
        refs.vector_documents.extend(_q_references.vector_documents)

        return context, references

    # * done
    async def _add_file_to_last_message(
        self,
        messages: list[ChatMessage],
        b64_file: B64File,
    ) -> list[ChatMessage]:
        # update the last message content with a file if a b64 file is provided
        file = await self.openai_service._create_file(
            b64_file_str=b64_file.content, b64_file_type=b64_file.type
        )

        if isinstance(messages[-1].content, str):
            messages[-1].content = [
                {"type": "input_text", "text": messages[-1].content},
                {"type": "input_file", "file_id": file.id},
            ]
            return messages

        messages[-1].content = messages[-1].content or []
        messages[-1].content.append({"type": "input_file", "file_id": b64_file.id})
        return messages

    # * done
    def _add_references_to_last_message(
        self,
        messages: list[ChatMessage],
        references: ChatMessageReferences | None = None,
    ) -> list[ChatMessage]:
        if references:
            messages[-1].references = references

        return messages

    def _remove_references(self, message: ChatMessage) -> ChatMessage:
        message.references = ChatMessageReferences()
        # message.references = []
        return message

    # ? this mutates the messages array provided
    async def _prepare_prompt(
        self,
        prompt: str | None = None,
        messages: list[ChatMessage] | None = None,
        file: B64File | None = None,
        min_length: int = 8,  # min length of query for building context
        rewrite: bool = True,
    ) -> tuple[
        str, list[ChatMessage], ChatMessageReferences | None, list[ChatMessage] | None
    ]:
        if prompt is None and not messages:
            raise BadRequestException(
                "A prompt and / or conversation messages must be provided."
            )

        last_prompt = prompt or self._get_last_prompt(messages)
        default_return = last_prompt, messages or [], None, messages
        extra = {"prompt": last_prompt}

        # check if the function should continue
        is_short_prompt = len(last_prompt.strip()) < min_length
        if is_short_prompt:
            info_msg = "[rag service - testing - _prepare_prompt] The Prompt is too short to build any meaningful context. Skipping context building."
            logger.info(info_msg, extra=extra)
            return default_return

        should_skip = await self._should_skip_context_building(last_prompt)
        if should_skip:
            info_msg = "[rag service - testing - _prepare_prompt] The prompt is too generic or common to build any meaningful context. Skipping context building."
            logger.info(info_msg, extra=extra)
            return default_return

        # create an openai file reference and add it to the user's message
        if file is not None:
            messages = await self._add_file_to_last_message(messages, file)

        # ----- add documents context and or rewritten prompt

        start_time = time.perf_counter_ns()
        # ------ timer

        rewritten_prompt = await self._rewrite_query(last_prompt, messages, rewrite)

        # get prompt queries list
        prompt_queries = [rewritten_prompt]
        limit = 250
        if rewrite:
            prompt_queries = parse_rewritten_user_query(rewritten_prompt).queries
            limit = 100

        # ------
        end_time = time.perf_counter_ns()
        # Calculate elapsed time
        execution_time = (end_time - start_time) * 1e-6
        print_msg = f"[rag service - testing - _prepare_prompt] Prompt Rewrite and Parsing time: {execution_time:.6f} milliseconds"
        print(print_msg)
        # ------

        # ----- get the related vector docs and documents

        document_context = ""
        references = ChatMessageReferences(
            vector_documents=[],
            documents=[],
            document_chunks=[],
        )
        processed_points: list[ExtendedPointId] = []

        start_time = time.perf_counter_ns()
        # ------ timer

        if settings.flag_use_asyncio_gather:
            context_tasks = [
                self.get_partial_context(
                    query, document_context, references, processed_points, limit
                )
                for query in prompt_queries
            ]
            results = await asyncio.gather(*context_tasks)
            document_context = "".join([ctx for ctx, ref in results])
        else:
            partial_context = ""
            for query in prompt_queries:
                partial_context, references = await self.get_partial_context(
                    query, partial_context, references, processed_points, limit
                )
            document_context = partial_context

        # -----
        end_time = time.perf_counter_ns()
        # Calculate elapsed time
        execution_time = (end_time - start_time) * 1e-6
        print_msg = f"[rag service - testing - _prepare_prompt] Context Building Execution time: {execution_time:.6f} milliseconds"
        print(print_msg)
        # -----

        messages = self._add_references_to_last_message(messages, references)
        updated_prompt = build_prompt_with_context(
            prompt, document_context, rewritten_prompt
        )

        # ? this replaces the user's prompt with a more detailed prompt with instructions and context ie. updated_prompt
        messages_with_context = self.prompt_builder.copy_messages(messages)
        if messages:
            messages_with_context = self._update_last_prompt(
                updated_prompt, messages_with_context
            )

        return updated_prompt, messages_with_context, references, messages

    # * done
    async def get_assistant_response(
        self,
        conversation: list[ChatMessage],
        *,
        prompt: str | None = None,
        instructions: str | None = None,
        file_url: str | None = None,
        b64_file: str | None = None,
        file_mime_type: str | None = None,
        stream: bool = True,
    ) -> AsyncStream[ResponseStreamEvent] | str | None:
        print_msg = f"[rag service - testing - get_assistant_response] generate_assistant_message: {settings.flag_generate_assistant_message}"
        print(print_msg)

        if not settings.flag_generate_assistant_message:
            return

        if self.openai_service is None:
            raise BadRequestException(
                "OpenAI service is not configured for chat responses or completions."
            )

        if not conversation and not prompt:
            raise BadRequestException(
                "Either a conversation or prompt is required to generate a response."
            )

        valid_conversation: ResponseInputParam | None = [
            OpenAIChatMessage.model_validate(message)  # .model_dump()
            for message in conversation
        ]

        prev_conversation = valid_conversation if prompt else None

        response = await self.openai_service.create_response(
            conversation=valid_conversation,
            prompt=prompt,
            prev_conversation=prev_conversation,
            instructions=instructions,
            file_url=file_url,
            b64_file=b64_file,
            b64_file_mime_type=file_mime_type,
            stream=stream,
        )

        if stream:
            response_stream: AsyncStream[ResponseStreamEvent] = response
            return response_stream

        response_text = self._get_response_text(response)
        return response_text

    # * done
    async def generate_assistant_response(
        self,
        messages: list[ChatMessage],
        file: B64File | None = None,
        stream: bool = True,
        append_str_response: bool = True,
    ) -> tuple[
        AsyncStream[ResponseStreamEvent] | str | None,
        list[ChatMessage],
        ChatMessageReferences | None,
    ]:
        # add references to messages and return a copy of messages with the last message's input_text (the prompt) rewritten and updated with context
        _prompt, messages_with_context, references, _ = await self._prepare_prompt(
            messages=messages, file=file
        )
        response = await self.get_assistant_response(
            messages_with_context, stream=stream
        )

        # only the full response text (not stream) can be added to messages as a ChatMessage
        if append_str_response and not stream and isinstance(response, str):
            self._append_to_messages(response, messages)

        return response, messages, references

    # -----

    # ----- create chat

    @overload
    async def create_chat(
        self,
        payload: CreateChatRequest,
        *,
        stream: Literal[True] = True,
        process_messages: bool = settings.flag_process_messages,
        save_to_db: bool = settings.flag_save_to_db,
    ) -> tuple[AsyncStream[ResponseStreamEvent], ChatMessageReferences | None]: ...

    @overload
    async def create_chat(
        self,
        payload: CreateChatRequest,
        *,
        stream: Literal[False] = False,
        process_messages: bool = settings.flag_process_messages,
        save_to_db: bool = settings.flag_save_to_db,
    ) -> ChatResponse: ...

    async def create_chat(
        self,
        payload: CreateChatRequest,
        *,
        stream: bool = True,
        process_messages: bool = settings.flag_process_messages,
        save_to_db: bool = settings.flag_save_to_db,
    ) -> (
        ChatResponse
        | tuple[AsyncStream[ResponseStreamEvent], ChatMessageReferences | None]
    ):

        if process_messages:
            file: B64File | None = None
            if payload.b64_file and payload.b64_file_type:
                file = B64File(content=payload.b64_file, type=payload.b64_file_type)

            response, messages, references = await self.generate_assistant_response(
                payload.messages, file, stream
            )

            if stream:
                return response, references

            payload.messages = messages

        if not save_to_db:
            info_msg = "[RagService - create_chat] Skipping saving to the database."
            logger.info(info_msg)

            mock_payload = {
                **payload.model_dump(),
                "id": "0000",
                "created_at": datetime.datetime.now(tz=datetime.UTC),
                "is_active": True,
                "is_deleted": False,
            }
            mock_chat = ChatResponse.model_validate(mock_payload)
            return ChatService.cleanChatResponse(mock_chat)

        # -----
        payload.messages = [self._remove_references(msg) for msg in payload.messages]

        created_chat = await self.chat_service.create_chat(payload)
        return ChatService.cleanChatResponse(created_chat)

    def get_create_response_completion_wrapper(
        self,
        references: ChatMessageReferences,
    ) -> ResponseCompletionFN:
        async def create_wrapper(payload: CreateChatRequest, complete_prompt: str):
            # ? the assistant message is created and added to messages in process_openai_response_stream
            payload.messages = self._add_references_to_last_message(
                payload.messages, references
            )

            return await self.create_chat(payload, process_messages=False, stream=False)

        return create_wrapper

    # -----

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

    # ----- update chat

    @overload
    async def update_chat(
        self,
        payload: UpdateChatRequest,
        chat_id: int | None = None,
        session_id: str | None = None,
        *,
        stream: Literal[True] = True,
        process_messages: bool = settings.flag_process_messages,
        save_to_db: bool = settings.flag_save_to_db,
    ) -> tuple[AsyncStream[ResponseStreamEvent], ChatMessageReferences | None]: ...

    @overload
    async def update_chat(
        self,
        payload: UpdateChatRequest,
        chat_id: int | None = None,
        session_id: str | None = None,
        *,
        stream: Literal[False] = False,
        process_messages: bool = settings.flag_process_messages,
        save_to_db: bool = settings.flag_save_to_db,
    ) -> ChatResponse: ...

    async def update_chat(
        self,
        payload: UpdateChatRequest,
        chat_id: int | None = None,
        session_id: str | None = None,
        *,
        stream: bool = True,
        process_messages: bool = settings.flag_process_messages,
        save_to_db: bool = settings.flag_save_to_db,
    ) -> (
        ChatResponse
        | tuple[AsyncStream[ResponseStreamEvent], ChatMessageReferences | None]
    ):

        existing_chat = await self._get_chat(chat_id, session_id)
        existing_chat = ChatService.cleanChatResponse(existing_chat)

        def merge_messages(
            current: list[ChatMessage] | None, new: list[ChatMessage] | None
        ) -> list[ChatMessage]:
            current = current or []  # self.prompt_builder.copy_messages(current)
            new = new or []  # self.prompt_builder.copy_messages(new)

            current.extend(new)
            return current

        if process_messages:
            file: B64File | None = None
            if payload.b64_file and payload.b64_file_type:
                file = B64File(content=payload.b64_file, type=payload.b64_file_type)

            # if messages are provided in payload, it should replace the existing chat messages
            chat_messages = payload.messages or existing_chat.messages
            payload.messages = merge_messages(chat_messages, payload.new_messages)
            # ensure an email is provided (if missing, sse breaks)
            payload.email = payload.email or existing_chat.email

            response, messages, references = await self.generate_assistant_response(
                payload.messages, file, stream
            )

            if stream:
                return response, references

            payload.messages = messages

        if not save_to_db:
            info_msg = "[RagService - update_chat] Skipping saving to the database."
            logger.info(info_msg)

            mock_payload = {
                **existing_chat.model_dump(),
                **payload.model_dump(),
            }
            mock_chat = ChatResponse.model_validate(mock_payload)
            return ChatService.cleanChatResponse(mock_chat)

        # -----
        payload.messages = [self._remove_references(msg) for msg in payload.messages]
        payload.new_messages = []

        updated_chat = await self.chat_service.update_chat(existing_chat.id, payload)
        return ChatService.cleanChatResponse(updated_chat)

    def get_update_response_completion_wrapper(
        self,
        chat_id: int | None = None,
        session_id: str | None = None,
        references: ChatMessageReferences | None = None,
    ) -> ResponseCompletionFN:
        async def update_wrapper(payload: UpdateChatRequest, complete_prompt: str):
            # ? the assistant message is created and added to messages in process_openai_response_stream
            payload.messages = self._add_references_to_last_message(
                payload.messages, references
            )

            return await self.update_chat(
                payload,
                chat_id=chat_id,
                session_id=session_id,
                process_messages=False,
                stream=False,
            )

        return update_wrapper

    # -----
