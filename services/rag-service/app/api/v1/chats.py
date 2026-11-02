import asyncio
import datetime
import json
from collections.abc import AsyncGenerator
from functools import partial
from typing import Annotated, Any

from app.core.config import settings
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
from app.utils.stream import process_openai_response_stream
from fastapi import APIRouter, Depends, Query, Request, responses, status
from openai import AsyncOpenAI, AsyncStream
from openai.types.responses import Response, ResponseInputParam, ResponseStreamEvent
from rag_packages.contracts.dto.chat import (
    AddPromptRequest,
    APIResponse,
    ChatAPIResponse,
    ChatListAPIResponse,
    ChatMessage,
    ChatResponse,
    CreateChatRequest,
    SimpleChat,
    UpdateChatRequest,
)
from rag_packages.shared.ai.openai import ActorRole
from rag_packages.shared.database.query import QueryParams
from rag_packages.shared.exception.exception import BadRequestException

router = APIRouter(prefix="/chats", tags=["Chats"])

# ----- queries

stream_query = Query(
    False, description="If true, stream the response from the ai assistant"
)
sse_query = Query(
    False,
    description="If true and stream is true, stream the response from the ai assistant as a server-sent event",
)
process_messages_query = Query(
    settings.flag_process_messages,
    description="If true, process the chat messages before creation",
)


@router.post(
    "/test/stream",
    status_code=status.HTTP_200_OK,
    response_model=SimpleChat,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="test response streaming",
)
async def test_chat_stream(
    body: SimpleChat,
    # service: OpenAIService = Depends(get_openai_service),
    # current_user: EntraUser = Depends(get_current_user),
) -> SimpleChat | str:

    async def generate_response(prompt: str) -> AsyncGenerator[Any, str]:
        """
        Simulates an AI response being generated incrementally.
        Replace this with your actual AI/model function.
        """
        response = (
            f"You asked: {prompt}. "
            "This is an example of a streamed response from FastAPI. "
            "Each piece of text is sent to the frontend as it becomes available."
        )

        words = response.split(" ")

        for word in words:
            yield word + " "
            await asyncio.sleep(0.15)

    async def stream():
        async for chunk in generate_response(body.prompt):
            # yield chunk
            chat_json = SimpleChat(
                prompt=body.prompt,
                response=chunk,
            ).model_dump_json()

            # Standard SSE requires prefixing with "data: " and ending with two newlines
            yield f"data: {chat_json}\n\n"

    return responses.StreamingResponse(
        stream(),
        # generate_response(body.prompt),
        # media_type="application/json",
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

    # response = await service.create_response(body.prompt)
    # response_text = response.output_text

    # return SimpleChat(
    #     prompt=body.prompt,
    #     response=response_text,
    # )


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
    stream: bool = stream_query,
    sse: bool = sse_query,
    # stream: Annotated[bool,Query(False, description="If true, stream the response from the ai assistant"),],
    service: OpenAIService = Depends(get_openai_service),
    current_user: EntraUser = Depends(get_current_user),
) -> SimpleChat | str:
    response = await service.create_response(body.prompt, stream=stream)

    if stream:
        payload = None
        if sse:
            msg = ChatMessage(
                role=ActorRole.USER,
                content=body.prompt,
                timestamp=datetime.datetime.now(tz=datetime.UTC),
            )
            payload = UpdateChatRequest(email="placeholder@rag.com", messages=[msg])

        return responses.StreamingResponse(
            process_openai_response_stream(response, payload=payload, return_sse=sse),
            # media_type="application/x-ndjson", # for newline delimited json streaming
            media_type="text/event-stream",  # same as media_type="text/plain"
            # headers={
            #     "Cache-Control": "no-cache",
            #     "X-Accel-Buffering": "no",
            # },
        )

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
    current_user: EntraUser = Depends(get_current_user),
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
    stream: bool = stream_query,
    sse: bool = sse_query,
    process_messages: bool = process_messages_query,
    service: ChatService = Depends(get_chat_service),
    rag_service: RagService = Depends(get_rag_service),
    current_user: EntraUser = Depends(get_current_user),
) -> ChatAPIResponse | str:

    # if stream:
    #     response = await rag_service.create_response(body.prompt, stream=stream)
        
    #     payload = None
    #     if sse:
    #         payload = UpdateChatRequest(**body.model_dump())
            
    #     create_wrapper = partial(
    #         rag_service.create_chat, process_messages=process_messages
    #     )
        
    #     # create_wrapper = lambda body: rag_service.create_chat(
    #     #     body, process_messages=process_messages
    #     # )
            
    #     return responses.StreamingResponse(
    #         process_openai_response_stream(
    #             response,
    #             payload=payload,
    #             return_sse=sse,
    #             process_completion_fn=create_wrapper,
    #         ),
    #         media_type="text/event-stream",
    #     )

    # working non streaming code
    created_chat = await rag_service.create_chat(
        body, process_messages=process_messages
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
    service: ChatService = Depends(get_chat_service),
    # service: Annotated[ChatService, Depends(get_chat_service)],
    current_user: EntraUser = Depends(get_current_user),
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
    stream: bool = stream_query,
    sse: bool = sse_query,
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
    current_user: EntraUser = Depends(get_current_user),
) -> ChatAPIResponse:
    # deleted_chat = await service.delete_chat(chat_id)

    return ChatAPIResponse(
        success=True,
        # data=deleted_chat,
        # message=f"Chat with ID {chat_id} has been deleted.",
        message="Chat deletion not allowed.",
    )


# TODO: pull from github on the prod vm
