from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from rag_packages.contracts.dto.chat import AddPromptRequest, ChatMessage, CreateChatRequest, UpdateChatRequest
from rag_packages.shared.ai.openai import ResponseMethod
from app.services import chat_service as chat_service_module
from app.services.chat_service import ChatService
from app.services.rag_service import RagService
from rag_packages.shared.exception.exception import BadRequestException


class FakeUnitOfWork:
    def __init__(self):
        self.session = SimpleNamespace(flush=AsyncMock())

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=60, nx=False):
        self.store[key] = value
        return True

    async def delete(self, key):
        self.store.pop(key, None)
        return True


class FakeRepo:
    def __init__(self, existing_chat=None):
        self.existing_chat = existing_chat
        self.created_payload = None
        self.created_payloads = None
        self.updated_payload = None

    async def create(self, payload):
        self.created_payload = payload
        return make_chat(messages=payload.messages)

    async def create_multiple(self, payloads):
        self.created_payloads = payloads
        return [
            make_chat(chat_id=index + 1, messages=payload.messages)
            for index, payload in enumerate(payloads)
        ]

    async def get_by_id(self, chat_id):
        return self.existing_chat

    async def get_by_session(self, session_id):
        return self.existing_chat

    async def update(self, chat_id, payload):
        self.updated_payload = payload
        updated_messages = payload.messages if payload.messages is not None else self.existing_chat.messages
        return make_chat(chat_id=chat_id, messages=updated_messages)


class FakeOpenAIService:
    def __init__(self, response_text="assistant reply"):
        self.response_text = response_text
        self.calls = []

    async def create_response(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.response_text)


def make_message(role="user", content="hello"):
    return ChatMessage(role=role, content=content, timestamp=datetime.now(UTC))


def make_chat(chat_id=1, messages=None):
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=chat_id,
        email="user@example.com",
        messages=messages or [],
        session_id="session-1",
        site_url="https://example.com",
        created_at=now,
        created_by_id=None,
        updated_at=now,
        updated_by_id=None,
        is_active=True,
        is_deleted=False,
    )


class FakeAsyncStream:
    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    monkeypatch.setattr(chat_service_module, "r", FakeRedis())


@pytest.mark.asyncio
async def test_create_chat_appends_assistant_response_for_non_empty_messages():
    repo = FakeRepo()
    producer = SimpleNamespace(chat_created=AsyncMock(), chat_updated=AsyncMock(), chat_deleted=AsyncMock())
    openai_service = FakeOpenAIService("generated response")
    service = ChatService(FakeUnitOfWork(), repo, producer, openai_service)

    payload = CreateChatRequest(
        email="user@example.com",
        messages=[make_message(content="How are you?")],
        session_id="session-1",
        site_url="https://example.com",
    )

    response = await service.create_chat(payload)

    assert len(repo.created_payload.messages) == 2
    assert repo.created_payload.messages[0].role == "user"
    assert repo.created_payload.messages[1].role == "assistant"
    assert repo.created_payload.messages[1].content == "generated response"
    assert openai_service.calls[0]["conversation"][0]["content"] == "How are you?"
    assert response.messages[-1].content == "generated response"


@pytest.mark.asyncio
async def test_create_multiple_chats_appends_assistant_responses_for_non_empty_messages():
    repo = FakeRepo()
    producer = SimpleNamespace(chat_created=AsyncMock(), chat_updated=AsyncMock(), chat_deleted=AsyncMock())
    openai_service = FakeOpenAIService("batch response")
    service = ChatService(FakeUnitOfWork(), repo, producer, openai_service)

    payloads = [
        CreateChatRequest(
            email="user1@example.com",
            messages=[make_message(content="First prompt")],
            session_id="session-1",
            site_url="https://example.com/1",
        ),
        CreateChatRequest(
            email="user2@example.com",
            messages=[],
            session_id="session-2",
            site_url="https://example.com/2",
        ),
    ]

    responses = await service.create_multiple_chats(payloads)

    assert repo.created_payloads is not None
    assert len(repo.created_payloads[0].messages) == 2
    assert repo.created_payloads[0].messages[-1].role == "assistant"
    assert repo.created_payloads[0].messages[-1].content == "batch response"
    assert repo.created_payloads[1].messages == []
    assert len(openai_service.calls) == 1
    assert openai_service.calls[0]["conversation"][0]["content"] == "First prompt"
    assert responses is not None
    assert responses[0].messages[-1].content == "batch response"
    assert responses[1].messages == []


@pytest.mark.asyncio
async def test_update_chat_with_prompt_appends_prompt_and_assistant_response():
    existing_chat = make_chat(messages=[make_message(content="existing message")])
    repo = FakeRepo(existing_chat=existing_chat)
    producer = SimpleNamespace(chat_created=AsyncMock(), chat_updated=AsyncMock(), chat_deleted=AsyncMock())
    openai_service = FakeOpenAIService("prompt response")
    service = ChatService(FakeUnitOfWork(), repo, producer, openai_service)

    payload = AddPromptRequest(prompt="new prompt", session_id="session-1")

    response = await service.update_chat_with_prompt(payload=payload, chat_id=1)

    assert len(repo.updated_payload.messages) == 3
    assert repo.updated_payload.messages[-2].role == "user"
    assert repo.updated_payload.messages[-2].content == "new prompt"
    assert repo.updated_payload.messages[-1].role == "assistant"
    assert repo.updated_payload.messages[-1].content == "prompt response"
    assert openai_service.calls[0]["prompt"] == "new prompt"
    assert len(openai_service.calls[0]["prev_conversation"]) == 1
    assert response.messages[-1].content == "prompt response"


@pytest.mark.asyncio
async def test_update_chat_with_new_messages_appends_assistant_response():
    existing_chat = make_chat(
        messages=[
            make_message(content="existing user"),
            make_message(role="assistant", content="existing assistant"),
        ]
    )
    repo = FakeRepo(existing_chat=existing_chat)
    producer = SimpleNamespace(chat_created=AsyncMock(), chat_updated=AsyncMock(), chat_deleted=AsyncMock())
    openai_service = FakeOpenAIService("follow-up response")
    service = ChatService(FakeUnitOfWork(), repo, producer, openai_service)

    payload = UpdateChatRequest(
        new_messages=[make_message(content="follow-up question")]
    )

    response = await service.update_chat(1, payload)

    assert len(repo.updated_payload.messages) == 4
    assert repo.updated_payload.messages[-2].content == "follow-up question"
    assert repo.updated_payload.messages[-1].role == "assistant"
    assert repo.updated_payload.messages[-1].content == "follow-up response"
    assert len(openai_service.calls[0]["conversation"]) == 3
    assert response.messages[-1].content == "follow-up response"


@pytest.mark.asyncio
async def test_stream_response_text_collects_response_api_deltas():
    service = RagService(None, None)
    stream = FakeAsyncStream(
        [
            SimpleNamespace(type="response.created"),
            SimpleNamespace(type="response.output_text.delta", delta="Hello "),
            SimpleNamespace(type="response.output_text.delta", delta="world"),
        ]
    )

    response_text = await service._stream_response_text(stream)

    assert response_text == "Hello world"


@pytest.mark.asyncio
async def test_stream_response_text_collects_chat_completion_deltas():
    service = RagService(None, None)
    stream = FakeAsyncStream(
        [
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello "))]),
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="world"))]),
        ]
    )

    response_text = await service._stream_response_text(
        stream, response_method=ResponseMethod.CHAT_COMPLETION
    )

    assert response_text == "Hello world"


@pytest.mark.asyncio
async def test_stream_response_text_raises_for_empty_stream():
    service = RagService(None, None)

    with pytest.raises(BadRequestException):
        await service._stream_response_text(FakeAsyncStream([]))
