from typing import Annotated

from app.dependencies.auth import EntraUser, get_current_user
from app.dependencies.chat import (
    ChatProducer,
    ChatService,
    OpenAIService,
    RagService,
    get_chat_producer,
    get_chat_service,
    get_openai_service,
    get_rag_service,
)
from fastapi import APIRouter, Depends, Query, Request, status
from rag_packages.contracts.dto.chat import (
    AddPromptRequest,
    APIResponse,
    ChatAPIResponse,
    ChatListAPIResponse,
    ChatResponse,
    CreateChatRequest,
    SimpleChat,
    UpdateChatRequest,
)
from rag_packages.shared.database.query import QueryParams
from rag_packages.shared.exception.exception import BadRequestException

router = APIRouter(prefix="/chats", tags=["Chats"])

# TODO: ensure     current_user: EntraUser = Depends(get_current_user)      works for validating user from entra access token (jwt)


@router.post(
    "/test/prompt",
    status_code=status.HTTP_200_OK,
    response_model=SimpleChat,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="send a prompt to the llm and get a response",
)
async def test_chat(
    body: SimpleChat,
    service: OpenAIService = Depends(get_openai_service),
) -> SimpleChat:
    response = await service.create_response(body.prompt)
    response_text = response.output_text

    return SimpleChat(
        prompt=body.prompt,
        response=response_text,
    )


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
    current_user: EntraUser = Depends(get_current_user),
    skip_processing: bool = Query(
        False, description="If true, skip processing the chat messages before creation"
    ),
) -> ChatAPIResponse:
    # if skip_processing:
    #     created_chat = await service.create_chat(body)
    # else:

    # created_chat = await rag_service.create_chat(body, process_messages=not skip_processing)
    # TODO: remove the above code after testing
    created_chat = await rag_service.create_chat(
        body, process_messages=not skip_processing
    )

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
    # service: Annotated[
    #     ChatService,
    #     Depends(
    #         get_chat_service,
    #     ),
    # ],
) -> ChatAPIResponse:
    chat = await service.get_chat_by_id(chat_id)

    return ChatAPIResponse(
        success=True,
        data=chat,
    )


update_with_prompt_kwargs = {
    "status_code": status.HTTP_200_OK,
    "response_model": ChatAPIResponse,
    # "response_model": APIResponse,
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
    current_user: EntraUser = Depends(get_current_user),
) -> ChatAPIResponse:
    # ) -> APIResponse:

    if chat_id is None and body.session_id is None:
        raise BadRequestException("Either chat_id or session_id must be provided.")

    updated_chat, references = await service.update_chat_with_prompt(
        chat_id=chat_id,
        session_id=body.session_id,
        payload=body,
        # # TODO: remove these after testing
        # update_chat=False,
        # generate_assistant_message=False,
    )

    # data = {"chat": updated_chat, "references": references}

    return ChatAPIResponse(
        # return APIResponse(
        success=True,
        data=updated_chat,
        # data=data,
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
    current_user: EntraUser = Depends(get_current_user),
    skip_processing: bool = Query(
        False, description="If true, skip processing the chat messages before creation"
    ),
) -> ChatAPIResponse:
    # if skip_processing:
    #     updated_chat = await service.update_chat(chat_id, body)
    # else:
    #     updated_chat = await rag_service.update_chat(chat_id, body)

    # # updated_chat = await service.update_chat(chat_id, body)

    updated_chat = await rag_service.update_chat(
        body, chat_id=chat_id, process_messages=not skip_processing
    )

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
