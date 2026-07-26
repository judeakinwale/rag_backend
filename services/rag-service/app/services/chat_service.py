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
)  # , DocumentResponseJSON

# TODO: uncomment this after the container rebuild
from rag_packages.contracts.dto.vector_document import (
    VectorDocumentFileMetadata,
    VectorDocumentResponse,
    # VectorDocumentResponseJSON,
)
from rag_packages.shared.database.query import QueryParams
from rag_packages.shared.database.uow import UnitOfWork
from rag_packages.shared.exception.exception import NotFoundException


# TODO: delete this after the container rebuild
class VectorDocumentFileMetadataJSON(VectorDocumentFileMetadata):
    last_modified: datetime | int | None = None  # timestamp in ms (13 digit int)


class VectorDocumentResponseJSON(VectorDocumentResponse):
    file_metadata: VectorDocumentFileMetadataJSON | None = None

    initiated_at: datetime | int | None = None  # timestamp in ms (13 digit int)
    completed_at: datetime | int | None = None  # timestamp in ms (13 digit int)


class DocumentResponseJSON(DocumentResponse):
    last_modified: datetime | int | None = None
    ingest_initiated_at: datetime | int | None = None
    prev_batch_ingest_init: datetime | int | None = None
    created_at: datetime | int | None = None
    updated_at: datetime | int | None = None


# TODO: move this to shared utils


def normalize_timestamp_to_seconds(ts: int) -> float:
    # 1_000_000_000_000 separates seconds from milliseconds
    seconds = ts / 1000.0 if ts >= 1_000_000_000_000 else float(ts)
    return seconds


def normalize_timestamp_to_milliseconds(ts: float | int) -> int:
    milliseconds = int(ts * 1000) if ts < 1_000_000_000_000 else int(ts)
    return milliseconds


def normalize_datetime_to_timestamp_ms(dt: datetime | int | str | None) -> int | None:
    if dt is None:
        return None

    if isinstance(dt, int):
        return normalize_timestamp_to_milliseconds(dt)

    if isinstance(dt, datetime):
        return int(dt.timestamp() * 1000)

    if isinstance(dt, str):
        date = datetime.fromisoformat(dt)
        return int(date.timestamp() * 1000)

    raise TypeError(
        f"Invalid timestamp type: {type(dt)}. Expected int, datetime, or str."
    )


def get_datetime_from_timestamp_ms(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None

    if isinstance(timestamp, float):
        timestamp = int(timestamp)

    if isinstance(timestamp, int):
        if len(str(timestamp)) == 10:
            timestamp = timestamp / 1000

        return datetime.fromtimestamp(timestamp)

    raise TypeError(f"Invalid timestamp type: {type(timestamp)}. Expected int.")


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


def normalize_chat_message_vector_documents(
    vector_doc: VectorDocumentResponse | VectorDocumentResponseJSON,
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

    return norm_vector_doc


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

    def _normalize_chat_message_datetimes(self, message: ChatMessage) -> ChatMessage:
        message.timestamp = normalize_datetime_to_timestamp_ms(message.timestamp)

        if message.references:
            message.references.documents = [
                normalize_chat_message_documents(doc)
                for doc in message.references.documents
            ]
            message.references.vector_documents = [
                normalize_chat_message_vector_documents(vector_doc)
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
