import orjson
from app.repositories.chat_repository import ChatRepository
from app.producers.chat_producer import ChatProducer
from app.events.chat_events import (
    ChatCreatedEvent,
    ChatUpdatedEvent,
    ChatDeletedEvent,
)
from app.models.chat import Chat
from app.core.redis import generate_cache_key, r
from rag_packages.contracts.dto.chat import (
    AddPromptRequest,
    CreateChatRequest,
    UpdateChatRequest,
    ChatResponse,
)
from rag_packages.shared.database.uow import UnitOfWork
from rag_packages.shared.database.query import QueryParams
from rag_packages.shared.exception.exception import NotFoundException
from rag_packages.shared.ai.openai import OpenAIService

from rag_packages.shared.exception.exception import BadRequestException


# TODO: update the create and update methods to use the OpenAIService for responses and updating / creating chat messages
class ChatService:
    def __init__(
        self,
        uow: UnitOfWork,
        repo: ChatRepository,
        producer: ChatProducer,
        openai_service: OpenAIService | None = None,
        # outbox_repo: None = None,
    ):
        self.uow = uow
        self.repo = repo
        self.producer = producer
        self.openai_service = openai_service

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

        await r.set(cache_key, orjson.dumps((valid_chats, count)))
        return valid_chats, count

    async def create_multiple_chats(
        self, payloads: list[CreateChatRequest]
    ) -> list[ChatResponse] | None:
        async with self.uow:
            chats: list[Chat] = await self.repo.create_multiple(payloads)

            # ensure the chats are persisted and
            await self.uow.session.flush()
            # access the persisted chats' ids before committing and sending the events
            chat_ids = [chat.id for chat in chats]
            print(f"Created chats with IDs: {chat_ids}")

        events = [ChatCreatedEvent.model_validate(chat) for chat in chats]

        for event in events:
            await self.producer.chat_created(event)

        return [ChatResponse.model_validate(chat) for chat in chats]

    async def create_chat(self, payload: CreateChatRequest) -> ChatResponse:
        async with self.uow:
            chat: Chat = await self.repo.create(payload)

            # ensure the chat is persisted and
            await self.uow.session.flush()
            # access the persisted chat's id before committing and sending the event
            chat_id = chat.id
            print(f"Created chat with ID: {chat_id}, details: {chat}")

        event = ChatCreatedEvent.model_validate(chat)
        await self.producer.chat_created(event)

        return ChatResponse.model_validate(chat)

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

    async def get_last_user_chat(self, email: str) -> ChatResponse | None:
        cache_key = generate_cache_key(str(email))
        cached = await r.get(cache_key)

        if cached is not None:
            return ChatResponse.model_validate_json(cached)

        chat = await self.repo.get_last_user_chat(email)
        if chat is None:
            return None

        valid_chat = ChatResponse.model_validate(chat)

        await r.set(cache_key, valid_chat.model_dump_json())
        return valid_chat

    async def update_chat_with_prompt(
        self,
        payload: AddPromptRequest,
        chat_id: int | None = None,
        session_id: str | None = None,
    ) -> ChatResponse | None:

        if chat_id is None and session_id is None:
            raise BadRequestException(
                "Either chat_id or session_id must be provided to update a chat with a prompt."
            )

        # prefer chat_id if provided, else use session_id

        if session_id is not None and chat_id is None:
            chat = await self.repo.get_by_session(session_id)
            if chat is None:
                raise NotFoundException(
                    f"Chat with session_id: {session_id} not found."
                )
            chat_id = chat.id

        async with self.uow:
            chat: Chat | None = await self.repo.update(chat_id, payload)
            if chat is None:
                raise NotFoundException(f"Chat with id: {chat_id} not found.")

        event = ChatUpdatedEvent.model_validate(chat)
        event.updated = list(payload.model_dump(exclude_unset=True).keys())
        await self.producer.chat_updated(event)

        return ChatResponse.model_validate(chat)

    async def update_chat(
        self, chat_id: int, payload: UpdateChatRequest
    ) -> ChatResponse | None:
        async with self.uow:
            chat: Chat | None = await self.repo.update(chat_id, payload)
            if chat is None:
                raise NotFoundException(f"Chat with id: {chat_id} not found.")

        event = ChatUpdatedEvent.model_validate(chat)
        event.updated = list(payload.model_dump(exclude_unset=True).keys())
        await self.producer.chat_updated(event)

        return ChatResponse.model_validate(chat)

    async def delete_chat(self, chat_id: int) -> ChatResponse | None:
        async with self.uow:
            chat: Chat | None = await self.repo.delete(chat_id)
            if chat is None:
                raise NotFoundException(f"Chat with id: {chat_id} not found.")

        event = ChatDeletedEvent.model_validate(chat)
        await self.producer.chat_deleted(event)

        return ChatResponse.model_validate(chat)
