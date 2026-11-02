import datetime
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Annotated, Any

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

logger = logging.getLogger(__name__)


async def process_openai_response_stream(
    stream: AsyncStream[ResponseStreamEvent],
    # UpdateChatRequest is functionally equivalent to CreateChatRequest
    payload: UpdateChatRequest | None = None,
    return_sse: bool = False,
    process_completion_fn: Callable[
        [UpdateChatRequest | CreateChatRequest], Awaitable[ChatResponse | None]
    ]
    | None = None,
) -> AsyncGenerator[str]:
    if return_sse and payload is None:
        raise BadRequestException("Payload must be provided when return_sse is True.")

    payload_messages_copy = [*payload.messages] if payload is not None else []

    str_response = ""
    part_str_response = ""
    is_stream_done = False
    async for event in stream:
        # print(f"stream part_str_response: {part_str_response}\n")
        # print(f"stream event: {event}\n")

        if event.type == "response.output_text.delta":
            part_str_response = event.delta
            str_response += part_str_response

        if event.type == "response.output_text.done":
            is_stream_done = True
            part_str_response = event.text
            # ? this break will stop (break) the streaming once the text is done generating but there are still other events
            # ? between this and the response.completed event that we might want to process
            # break

        if event.type == "response.completed":
            is_stream_done = True
            # part_str_response = event.response.text

            if process_completion_fn is not None and payload is not None:
                # call function to create / update the chat using the provided payload
                chat: ChatResponse = await process_completion_fn(payload)
                chat_json = chat.model_dump_json()

                logger.info("Created / updated chat (chat response) in the database\n")

                if return_sse:
                    yield f"data: {chat_json}\n\n"

            logger.info(
                f"response streaming done, final str_response: {str_response}\n"
            )
            break

        # print(f"processing is_stream_done: {is_stream_done}\n")
        # print(f"processing str_response: {str_response}\n")
        # print(f"processing part_str_response: {part_str_response}\n")

        # # is_same = part_str_response and str_response == part_str_response
        # # is_stream_done = is_stream_done or is_same

        # nothing to yield
        if not part_str_response and not is_stream_done:
            continue

        if is_stream_done:
            continue  # continue the loop but skip the yielding code below

        # -----

        # send placeholder chat response objects as server-sent events
        if return_sse and str_response:
            now = datetime.datetime.now(tz=datetime.UTC)
            assistant_message = ChatMessage(
                role=ActorRole.ASSISTANT,
                content=str_response,
                timestamp=now,
            )
            payload.messages = [*payload_messages_copy, assistant_message]
            sse_data = ChatResponse.model_validate(
                {
                    **payload.model_dump(),
                    "id": "1000",
                    "created_at": now,
                    "is_active": False,
                    "is_deleted": False,
                }
            )
            sse_json = sse_data.model_dump_json()
            # Standard SSE requires prefixing with "data: " and ending with two newlines
            yield f"data: {sse_json}\n\n" if not is_stream_done else ""
            continue

        yield part_str_response if not is_stream_done else ""
