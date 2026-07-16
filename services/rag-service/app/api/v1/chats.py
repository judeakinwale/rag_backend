from typing import Annotated
from fastapi import APIRouter, Depends, Request, status, Query
from rag_packages.contracts.dto.chat import (
    AddPromptRequest,
    ChatAPIResponse,
    CreateChatRequest,
    UpdateChatRequest,
    ChatListAPIResponse,
)
from app.dependencies.chat import (
    get_chat_service,
    get_chat_producer,
    ChatService,
    ChatProducer,
    get_rag_service,
    RagService,
)
from rag_packages.shared.database.query import QueryParams
from rag_packages.shared.exception.exception import BadRequestException


router = APIRouter(prefix="/chats", tags=["Chats"])

# TODO: replace chat service with rag service for create, update and prompt endpoints


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=ChatListAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Get all chats",
)
async def get_chats(
    query: Annotated[QueryParams, Query()],
    service: ChatService = Depends(get_chat_service),
    producer: ChatProducer = Depends(get_chat_producer),
) -> ChatListAPIResponse:
    chats, count = await service.get_chats(query)

    return ChatListAPIResponse(
        success=True,
        data=chats,
        count=count,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Create a new chat",
)
async def create_chat(
    request: Request,
    body: CreateChatRequest,
    service: ChatService = Depends(get_chat_service),
    rag_service: RagService = Depends(get_rag_service),
    skip_processing: bool = Query(
        False, description="If true, skip processing the chat messages before creation"
    ),
) -> ChatAPIResponse:
    if skip_processing:
        created_chat = await service.create_chat(body)
    else:
        created_chat = await rag_service.create_chat(body)

    return ChatAPIResponse(
        success=True,
        data=created_chat,
    )


@router.get(
    "/{chat_id}",
    status_code=status.HTTP_200_OK,
    response_model=ChatAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Get a chat by ID",
)
async def get_chat(
    chat_id: int,
    service: ChatService = Depends(
        get_chat_service,
    ),
) -> ChatAPIResponse:
    chat = await service.get_chat_by_id(chat_id)

    return ChatAPIResponse(
        success=True,
        data=chat,
    )


update_with_prompt_kwargs = {
    "status_code": status.HTTP_200_OK,
    "response_model": ChatAPIResponse,
    "response_model_exclude_none": True,
    "response_model_exclude_unset": True,
    "summary": "Update a chat with a prompt",
}


@router.post("/{chat_id}/prompt", **update_with_prompt_kwargs)
@router.post("/prompt", **update_with_prompt_kwargs)
async def update_chat_with_prompt(
    request: Request,
    body: AddPromptRequest,
    chat_id: int | None = None,
    service: RagService = Depends(get_rag_service),
) -> ChatAPIResponse:

    if chat_id is None and body.session_id is None:
        raise BadRequestException("Either chat_id or session_id must be provided.")

    updated_chat = await service.update_chat_with_prompt(
        chat_id=chat_id, session_id=body.session_id, payload=body
    )

    return ChatAPIResponse(
        success=True,
        data=updated_chat,
    )


update_kwargs = {
    "status_code": status.HTTP_200_OK,
    "response_model": ChatAPIResponse,
    "response_model_exclude_none": True,
    "response_model_exclude_unset": True,
    "summary": "Update a chat by ID",
}


@router.patch("/{chat_id}", **update_kwargs)
@router.put("/{chat_id}", **update_kwargs)
async def update_chat(
    chat_id: int,
    body: UpdateChatRequest,
    rag_service: RagService = Depends(get_rag_service),
    service: ChatService = Depends(get_chat_service),
    skip_processing: bool = Query(
        False, description="If true, skip processing the chat messages before creation"
    ),
) -> ChatAPIResponse:
    if skip_processing:
        updated_chat = await service.update_chat(chat_id, body)
    else:
        updated_chat = await rag_service.update_chat(chat_id, body)

    # updated_chat = await service.update_chat(chat_id, body)

    return ChatAPIResponse(
        success=True,
        data=updated_chat,
    )


@router.delete(
    "/{chat_id}",
    status_code=status.HTTP_200_OK,
    response_model=ChatAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Delete a chat by ID",
)
async def delete_chat(
    chat_id: int,
    service: ChatService = Depends(get_chat_service),
) -> ChatAPIResponse:
    deleted_chat = await service.delete_chat(chat_id)

    return ChatAPIResponse(
        success=True,
        data=deleted_chat,
        message=f"Chat with ID {chat_id} has been deleted.",
    )
