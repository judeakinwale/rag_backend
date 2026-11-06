import datetime
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Annotated, Any, TypeAlias

from app.dependencies.chat import get_prompt_builder
from app.services.chat_service import ChatService
from app.types.stream import ResponseCompletionFN
from openai import AsyncOpenAI, AsyncStream
from openai.types.responses import Response, ResponseInputParam, ResponseStreamEvent
from rag_packages.contracts.dto.chat import (
    ChatMessage,
    ChatResponse,
    CreateChatRequest,
    UpdateChatRequest,
)
from rag_packages.shared.ai.openai import ActorRole
from rag_packages.shared.exception.exception import BadRequestException

logger = logging.getLogger(__name__)

prompt_builder = get_prompt_builder()


async def process_openai_response_stream(
    stream: AsyncStream[ResponseStreamEvent],
    # UpdateChatRequest is functionally equivalent to CreateChatRequest
    payload: UpdateChatRequest | CreateChatRequest | None = None,
    return_sse: bool = False,
    process_completion_fn: ResponseCompletionFN | None = None,
) -> AsyncGenerator[str]:
    if return_sse and payload is None:
        raise BadRequestException("Payload must be provided when return_sse is True.")

    if stream is None:
        # call function to create / update the chat using the provided payload
        chat: ChatResponse = await process_completion_fn(payload, stream)
        cleaned_chat = ChatService.cleanChatResponse(chat)
        chat_json = cleaned_chat.model_dump_json()

        logger.info("Created / updated chat (chat response) in the database\n")

        if return_sse:
            yield f"data: {chat_json}\n\n"
            logger.info(f"response SSE streaming done, final str_response: {stream}\n")
            return

        yield f"{stream}"
        logger.info(f"response streaming done, final str_response: {stream}\n")
        return

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
                assistant_message = prompt_builder.create_chat_message(
                    role=ActorRole.ASSISTANT,
                    content=str_response,
                )
                payload.messages = [*payload_messages_copy, assistant_message]

                # call function to create / update the chat using the provided payload
                chat: ChatResponse = await process_completion_fn(payload, str_response)
                chat_json = chat.model_dump_json()

                logger.info("Created / updated chat (chat response) in the database\n")

                if return_sse:
                    yield f"data: {chat_json}\n\n"

            logger.info(
                f"response streaming done, final str_response: {str_response}\n"
            )
            break

        if event.type == "response.failed":
            default_err_msg = "OpenAI service returned a failed response."
            raise RuntimeError(event.response.error or default_err_msg)

        # print(f"processing str_response: {str_response}\n")

        if not part_str_response and not is_stream_done:
            continue  # nothing to yield

        if is_stream_done:
            continue  # continue the loop but skip the yielding code below

        print(f"processing part_str_response: {part_str_response}\n")
        # print(
        #     f"processing part_str_response: {part_str_response if not is_stream_done else 'test'}\n"
        # )

        # -----

        # send placeholder chat response objects as server-sent events
        if return_sse and str_response:
            now = datetime.datetime.now(tz=datetime.UTC)
            assistant_message = prompt_builder.create_chat_message(
                role=ActorRole.ASSISTANT,
                content=str_response,
            )
            payload.messages = [*payload_messages_copy, assistant_message]

            valid_payload = {
                **payload.model_dump(),
                "id": "0",
                "created_at": now,
                "is_active": False,
                "is_deleted": False,
            }
            sse_data = ChatResponse.model_validate(valid_payload)
            cleaned_sse_data = ChatService.cleanChatResponse(sse_data)
            sse_json = cleaned_sse_data.model_dump_json()

            # Standard SSE requires prefixing with "data: " and ending with two newlines
            yield f"data: {sse_json}\n\n" if not is_stream_done else ""
            continue

        # yield part_str_response
        yield part_str_response if not is_stream_done else ""
