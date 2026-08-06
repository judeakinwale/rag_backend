from datetime import datetime

import orjson
from app.core.redis import generate_cache_key, r
from app.events.chat_events import (
    ChatCreatedEvent,
    ChatDeletedEvent,
    ChatUpdatedEvent,
)
from app.models.chat import Chat
from app.producers.chat_producer import ChatProducer
from app.repositories.chat_repository import ChatRepository
from pydantic import TypeAdapter
from rag_packages.contracts.dto.chat import (
    ChatMessage,
    ChatResponse,
    CreateChatRequest,
    UpdateChatRequest,
)
from rag_packages.contracts.dto.document import (
    DocumentResponse,
    DocumentResponseJSON,
)

# TODO: uncomment this after the container rebuild
from rag_packages.contracts.dto.vector_document import (
    VectorDocumentFileMetadata,
    VectorDocumentResponse,
    VectorDocumentResponseJSON,
)
from rag_packages.shared.database.query import QueryParams
from rag_packages.shared.database.uow import UnitOfWork
from rag_packages.shared.exception.exception import NotFoundException
from rag_packages.shared.utils.format import (
    dicts_to_markdown,
    get_datetime_from_timestamp_ms,
    normalize_datetime_to_timestamp_ms,
    normalize_timestamp_to_milliseconds,
    normalize_timestamp_to_seconds,
)

# TODO: delete this after the container rebuild
# class VectorDocumentFileMetadataJSON(VectorDocumentFileMetadata):
#     last_modified: datetime | int | None = None  # timestamp in ms (13 digit int)


# class VectorDocumentResponseJSON(VectorDocumentResponse):
#     file_metadata: VectorDocumentFileMetadataJSON | None = None

#     initiated_at: datetime | int | None = None  # timestamp in ms (13 digit int)
#     completed_at: datetime | int | None = None  # timestamp in ms (13 digit int)


# class DocumentResponseJSON(DocumentResponse):
#     last_modified: datetime | int | None = None
#     ingest_initiated_at: datetime | int | None = None
#     prev_batch_ingest_init: datetime | int | None = None
#     created_at: datetime | int | None = None
#     updated_at: datetime | int | None = None


class ChatService:
    def __init__(
        self,
        uow: UnitOfWork,
        repo: ChatRepository,
        producer: ChatProducer,
        # outbox_repo: None = None,
    ):
        self.uow = uow
        self.repo = repo
        self.producer = producer
        # self.outbox_repo = outbox_repo
        self._response_adapter = TypeAdapter(tuple[list[ChatResponse], int])

    @staticmethod
    def normalize_chat_message_documents(
        doc: DocumentResponse | DocumentResponseJSON,
    ) -> DocumentResponseJSON:
        doc.last_modified = normalize_datetime_to_timestamp_ms(doc.last_modified)
        doc.ingest_initiated_at = normalize_datetime_to_timestamp_ms(
            doc.ingest_initiated_at
        )
        doc.prev_batch_ingest_init = normalize_datetime_to_timestamp_ms(
            doc.prev_batch_ingest_init
        )
        doc.created_at = normalize_datetime_to_timestamp_ms(doc.created_at)
        doc.updated_at = normalize_datetime_to_timestamp_ms(doc.updated_at)

        norm_doc = DocumentResponseJSON.model_validate(doc)

        return norm_doc

    @staticmethod
    def get_vector_doc_details(
        doc: VectorDocumentResponse, exclude_keys: list[str] | None = None
    ) -> dict:
        details = doc.details.model_dump() if doc.details else {}

        if exclude_keys:
            for key in exclude_keys:
                if key in details:
                    del details[key]

        return details

    @staticmethod
    def normalize_chat_message_vector_documents(
        vector_doc: VectorDocumentResponse | VectorDocumentResponseJSON,
        include_details: bool = False,
    ) -> VectorDocumentResponseJSON:
        if vector_doc.file_metadata is not None:
            vector_doc.file_metadata.last_modified = normalize_datetime_to_timestamp_ms(
                vector_doc.file_metadata.last_modified
            )

        vector_doc.initiated_at = normalize_datetime_to_timestamp_ms(
            vector_doc.initiated_at
        )
        vector_doc.completed_at = normalize_datetime_to_timestamp_ms(
            vector_doc.completed_at
        )

        norm_vector_doc = VectorDocumentResponseJSON.model_validate(vector_doc)

        if include_details and vector_doc.details is not None:
            details_dict = ChatService.get_vector_doc_details(
                vector_doc,
                exclude_keys=["headings", "captions", "tables", "figures"],  # "pages",
            )
            # norm_vector_doc.details_dict = details_dict

            # force package reinstall
            # only the pages are somewhat relevant for this use case
            norm_vector_doc.details_markdown = dicts_to_markdown(
                [details_dict],
                ["pages"],  # , "headings", "captions", "tables", "figures"
                section_title="Document Details",
                # subtitle_key="headings",
                base_header_prefix="\n####",
            )

        return norm_vector_doc

    def _normalize_chat_message_datetimes(self, message: ChatMessage) -> ChatMessage:
        message.timestamp = normalize_datetime_to_timestamp_ms(message.timestamp)

        if message.references:
            message.references.documents = [
                self.normalize_chat_message_documents(doc)
                for doc in message.references.documents
            ]
            message.references.vector_documents = [
                self.normalize_chat_message_vector_documents(vector_doc)
                for vector_doc in message.references.vector_documents
            ]
        return message

    def _normalize_chat_messages(
        self, messages: list[ChatMessage]
    ) -> list[ChatMessage]:
        norm_messages = [
            self._normalize_chat_message_datetimes(message) for message in messages
        ]
        return norm_messages

    async def get_chats(
        self, params: QueryParams | None = None
    ) -> tuple[list[ChatResponse], int]:
        cache_key = generate_cache_key(
            f"all:{params.model_dump_json()}" if params else "all"
        )
        cached = await r.get(cache_key)

        if cached is not None:
            try:
                chats, count = orjson.loads(cached)
                return [ChatResponse.model_validate(chat) for chat in chats], count

            except orjson.JSONDecodeError:
                print(
                    f"[chat-service] Failed to decode cached data for key {cache_key}. Invalidating cache."
                )
                await r.delete(cache_key)  # invalidate corrupted cache

        chats, count = await self.repo.get_all(params)
        valid_chats = [ChatResponse.model_validate(chat) for chat in chats]

        json_str = self._response_adapter.dump_json((valid_chats, count)).decode()
        await r.set(cache_key, json_str)
        # await r.set(cache_key, orjson.dumps((valid_chats, count)))
        return valid_chats, count

    async def create_multiple_chats(
        self, payloads: list[CreateChatRequest]
    ) -> list[ChatResponse] | None:
        for payload in payloads:
            payload.messages = self._normalize_chat_messages(payload.messages)

        async with self.uow:
            chats: list[Chat] = await self.repo.create_multiple(payloads)

            # ensure the chats are persisted and
            await self.uow.session.flush()
            # access the persisted chats' ids before committing and sending the events
            chat_ids = [chat.id for chat in chats]
            print(f"Created chats with IDs: {chat_ids}")

            events = [ChatCreatedEvent.model_validate(chat) for chat in chats]
            response = [ChatResponse.model_validate(chat) for chat in chats]

        for event in events:
            await self.producer.chat_created(event)
        return response

    async def create_chat(self, payload: CreateChatRequest) -> ChatResponse:
        payload.messages = self._normalize_chat_messages(payload.messages)
        async with self.uow:
            chat: Chat = await self.repo.create(payload)

            # ensure the chat is persisted and
            await self.uow.session.flush()
            # access the persisted chat's id before committing and sending the event
            chat_id = chat.id
            print(f"Created chat with ID: {chat_id}, details: {chat}")

            event = ChatCreatedEvent.model_validate(chat)
            response = ChatResponse.model_validate(chat)

        await self.producer.chat_created(event)
        return response

    async def get_chat_by_id(self, chat_id: int) -> ChatResponse | None:
        cache_key = generate_cache_key(str(chat_id))
        cached = await r.get(cache_key)

        if cached is not None:
            return ChatResponse.model_validate_json(cached)

        chat = await self.repo.get_by_id(chat_id)
        if chat is None:
            raise NotFoundException(f"Chat with id: {chat_id} not found.")

        valid_chat = ChatResponse.model_validate(chat)

        await r.set(cache_key, valid_chat.model_dump_json())
        return valid_chat

    async def get_chat_by_session_id(self, session_id: str) -> ChatResponse | None:
        cache_key = generate_cache_key(f"session:{session_id}")
        cached = await r.get(cache_key)

        if cached is not None:
            return ChatResponse.model_validate_json(cached)

        chat = await self.repo.get_by_session(session_id)
        if chat is None:
            raise NotFoundException(f"Chat with session_id: {session_id} not found.")

        valid_chat = ChatResponse.model_validate(chat)

        await r.set(cache_key, valid_chat.model_dump_json())
        return valid_chat

    async def get_last_user_chat(self, email: str) -> ChatResponse | None:
        cache_key = generate_cache_key(f"email:{email}:last")
        cached = await r.get(cache_key)

        if cached is not None:
            return ChatResponse.model_validate_json(cached)

        chat = await self.repo.get_last_user_chat(email)
        if chat is None:
            return None

        valid_chat = ChatResponse.model_validate(chat)

        # short expiry as this becomes stale fast
        await r.set(cache_key, valid_chat.model_dump_json(), ex=10)
        return valid_chat

    async def update_chat(
        self, chat_id: int, payload: UpdateChatRequest
    ) -> ChatResponse | None:
        payload.messages = self._normalize_chat_messages(payload.messages)
        async with self.uow:
            print(f"Updating chat with ID: {chat_id}, payload: {payload}")
            chat: Chat | None = await self.repo.update(chat_id, payload)
            if chat is None:
                raise NotFoundException(f"Chat with id: {chat_id} not found.")

            event = ChatUpdatedEvent.model_validate(chat)
            response = ChatResponse.model_validate(chat)

        event.updated = list(payload.model_dump(exclude_unset=True).keys())
        await self.producer.chat_updated(event)

        return response

    async def delete_chat(self, chat_id: int) -> ChatResponse | None:
        async with self.uow:
            chat: Chat | None = await self.repo.delete(chat_id)
            if chat is None:
                raise NotFoundException(f"Chat with id: {chat_id} not found.")

            event = ChatDeletedEvent.model_validate(chat)
            response = ChatResponse.model_validate(chat)

        await self.producer.chat_deleted(event)
        return response
