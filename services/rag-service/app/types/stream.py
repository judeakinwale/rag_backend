from collections.abc import Awaitable, Callable

from rag_packages.contracts.dto.chat import (
    ChatResponse,
    CreateChatRequest,
    UpdateChatRequest,
)

type ResponseCompletionFN = Callable[
    [UpdateChatRequest | CreateChatRequest, str | None], Awaitable[ChatResponse | None]
]
