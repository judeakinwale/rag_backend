from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.v1.chats import update_chat as update_chat_route
from app.services.rag_service import RagService
from rag_packages.contracts.dto.chat import ChatResponse, UpdateChatRequest


def make_chat(chat_id: int = 17, session_id: str = "session-17") -> ChatResponse:
    now = datetime.now(UTC)
    return ChatResponse(
        id=chat_id,
        email="user@example.com",
        messages=[],
        session_id=session_id,
        site_url="https://example.com",
        created_at=now,
        updated_at=now,
        is_active=True,
        is_deleted=False,
    )


@pytest.mark.asyncio
async def test_update_chat_route_passes_payload_and_chat_id_by_name():
    payload = UpdateChatRequest(messages=[])
    updated_chat = make_chat()
    rag_service = SimpleNamespace(update_chat=AsyncMock(return_value=updated_chat))

    response = await update_chat_route(
        chat_id=updated_chat.id,
        body=payload,
        rag_service=rag_service,
        service=None,
        skip_processing=False,
    )

    rag_service.update_chat.assert_awaited_once_with(
        payload, chat_id=updated_chat.id, process_messages=True
    )
    assert response.data == updated_chat


@pytest.mark.asyncio
async def test_update_chat_by_session_persists_using_resolved_chat_id():
    payload = UpdateChatRequest(messages=[])
    existing_chat = make_chat()
    chat_service = SimpleNamespace(
        get_chat_by_session_id=AsyncMock(return_value=existing_chat),
        update_chat=AsyncMock(return_value=existing_chat),
    )
    service = RagService(chat_service=chat_service, qdrant_service=None)

    response = await service.update_chat(
        payload, session_id=existing_chat.session_id, process_messages=False
    )

    chat_service.update_chat.assert_awaited_once_with(existing_chat.id, payload)
    assert response == existing_chat