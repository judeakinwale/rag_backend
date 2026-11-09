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
    ChatMessageReferences,
    ChatResponse,
    CreateChatRequest,
    SimpleChat,
    UpdateChatRequest,
)
from rag_packages.contracts.types.shared_types import BoolStr
from rag_packages.shared.ai.openai import ActorRole
from rag_packages.shared.database.query import QueryParams
from rag_packages.shared.exception.exception import BadRequestException

router = APIRouter(prefix="/chats", tags=["Chats"])

# ----- queries

stream_query = Query(
    settings.flag_stream,  # True,
    description="If true, stream the response from the ai assistant",
)
sse_query = Query(
    settings.flag_stream,  # True,
    description="If true and stream is true, stream the response from the ai assistant as a server-sent event",
)
process_messages_query = Query(
    settings.flag_process_messages,
    description="If true, process the chat messages before creation",
)
show_references_query = Query(
    BoolStr.FALSE,
    description="If true, show the chat message references",
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
    sse: bool = sse_query,
    # service: Annotated[OpenAIService, Depends(get_openai_service)],
    # current_user: Annotated[EntraUser, Depends(get_current_user)],
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
            if not sse:
                yield chunk

            chat_json = SimpleChat(
                prompt=body.prompt,
                response=chunk,
            ).model_dump_json()

            # Standard SSE requires prefixing with "data: " and ending with two newlines
            yield f"data: {chat_json}\n\n"

    return responses.StreamingResponse(
        stream(),  # generate_response(body.prompt),
        media_type="text/event-stream" if sse else "text/plain",
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
    service: Annotated[OpenAIService, Depends(get_openai_service)],
    current_user: Annotated[EntraUser, Depends(get_current_user)],
    stream: bool = stream_query,
    sse: bool = sse_query,
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
            # "application/x-ndjson" for newline delimited json streaming, "text/plain" for plain text and "text/event-stream" for server sent events
            media_type="text/event-stream" if sse else "text/plain",
            headers={
                "Transfer-Encoding": "chunked",
                "Cache-Control": "no-cache, no-transform",  # "no-cache",
                "X-Accel-Buffering": "no",
            },
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
    service: Annotated[ChatService, Depends(get_chat_service)],
    producer: Annotated[ChatProducer, Depends(get_chat_producer)],
    current_user: Annotated[EntraUser, Depends(get_current_user)],
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
    service: Annotated[ChatService, Depends(get_chat_service)],
    rag_service: Annotated[RagService, Depends(get_rag_service)],
    current_user: Annotated[EntraUser, Depends(get_current_user)],
    stream: bool = stream_query,
    sse: bool = sse_query,
    process_messages: bool = process_messages_query,
) -> ChatAPIResponse | str:

    if stream:
        response, references = await rag_service.create_chat(
            body, process_messages=process_messages, stream=stream
        )
        create_wrapper = rag_service.get_create_response_completion_wrapper(references)

        return responses.StreamingResponse(
            process_openai_response_stream(
                response,
                payload=body,
                return_sse=sse,
                process_completion_fn=create_wrapper,
            ),
            # "text/plain" for plain text and "text/event-stream" for server sent events
            media_type="text/event-stream" if sse else "text/plain",
            headers={
                "Transfer-Encoding": "chunked",
                "Cache-Control": "no-cache, no-transform",  # "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    created_chat = await rag_service.create_chat(
        body, process_messages=process_messages, stream=stream
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
    service: Annotated[ChatService, Depends(get_chat_service)],
    # service: Annotated[ChatService, Depends(get_chat_service)],
    current_user: Annotated[EntraUser, Depends(get_current_user)],
    show_references: BoolStr = show_references_query,
) -> ChatAPIResponse:
    chat = await service.get_chat_by_id(chat_id, show_references)

    return ChatAPIResponse(
        success=True,
        data=chat,
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
    rag_service: Annotated[RagService, Depends(get_rag_service)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    current_user: Annotated[EntraUser, Depends(get_current_user)],
    stream: bool = stream_query,
    sse: bool = sse_query,
    process_messages: bool = process_messages_query,
    show_references: BoolStr = show_references_query,
) -> ChatAPIResponse:

    if stream:
        response, references = await rag_service.update_chat(
            body, chat_id=chat_id, process_messages=process_messages, stream=stream
        )
        update_wrapper = rag_service.get_update_response_completion_wrapper(
            chat_id, references
        )

        return responses.StreamingResponse(
            process_openai_response_stream(
                response,
                payload=body,
                return_sse=sse,
                process_completion_fn=update_wrapper,
            ),
            # "text/plain" for plain text and "text/event-stream" for server sent events
            media_type="text/event-stream" if sse else "text/plain",
            headers={
                "Transfer-Encoding": "chunked",
                "Cache-Control": "no-cache, no-transform",  # "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    updated_chat = await rag_service.update_chat(
        body, chat_id=chat_id, process_messages=process_messages, stream=stream
    )

    return ChatAPIResponse(
        success=True,
        data=updated_chat,
    )


update_with_prompt_kwargs = {
    "status_code": status.HTTP_200_OK,
    "response_model": ChatAPIResponse,  # APIResponse
    "response_model_exclude_none": True,
    "response_model_exclude_unset": True,
    "summary": "Update a chat with a prompt",
}


@router.post("/{chat_id}/prompt", **update_with_prompt_kwargs)
@router.post("/prompt", **update_with_prompt_kwargs)
async def update_chat_with_prompt(
    request: Request,
    body: AddPromptRequest,
    rag_service: Annotated[RagService, Depends(get_rag_service)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    current_user: Annotated[EntraUser, Depends(get_current_user)],
    chat_id: int | None = None,
    stream: bool = stream_query,
    sse: bool = sse_query,
    process_messages: bool = process_messages_query,
    show_references: BoolStr = show_references_query,
) -> ChatAPIResponse:  # APIResponse:

    payload = rag_service.convert_add_prompt_request_to_update_chat_request(body)

    if stream:
        response, references = await rag_service.update_chat(
            payload,
            chat_id=chat_id,
            session_id=body.session_id,
            process_messages=process_messages,
            stream=stream,
        )
        update_wrapper = rag_service.get_update_response_completion_wrapper(
            chat_id, references
        )

        return responses.StreamingResponse(
            process_openai_response_stream(
                response,
                payload=payload,
                return_sse=sse,
                process_completion_fn=update_wrapper,
            ),
            # "text/plain" for plain text and "text/event-stream" for server sent events
            media_type="text/event-stream" if sse else "text/plain",
            headers={
                "Transfer-Encoding": "chunked",
                "Cache-Control": "no-cache, no-transform",  # "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    updated_chat = await rag_service.update_chat(
        payload, chat_id=chat_id, process_messages=process_messages, stream=stream
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
    service: Annotated[ChatService, Depends(get_chat_service)],
    current_user: Annotated[EntraUser, Depends(get_current_user)],
) -> ChatAPIResponse:
    # deleted_chat = await service.delete_chat(chat_id)

    return ChatAPIResponse(
        success=True,
        # data=deleted_chat,
        # message=f"Chat with ID {chat_id} has been deleted.",
        message="Chat deletion not allowed.",
    )


# TODO: pull from github on the prod vm
