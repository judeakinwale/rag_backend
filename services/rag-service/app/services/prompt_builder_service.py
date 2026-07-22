from datetime import UTC, datetime
import mimetypes
from typing import Any
from rag_packages.contracts.dto.chat import AddPromptRequest, ChatMessage
from rag_packages.shared.ai.openai import ActorRole


class PromptBuilder:
    def _get_mime_type(self, extension: str = "png", default: str = "image/png"):
        if "/" in extension:
            return extension  # already a mime type

        if not extension.startswith("."):
            extension = "." + extension

        mime_type = mimetypes.types_map.get(extension.lower(), default)

        print(mime_type)  # eg. image/jpeg, image/png, application/pdf, etc.

        return mime_type

    def copy_messages(self, messages: list[ChatMessage] | None) -> list[ChatMessage]:
        return (
            [message.model_copy(deep=True) for message in messages] if messages else []
        )

    def create_chat_message(
        self,
        *,
        role: ActorRole,
        content: str | list[dict[str, Any]],
    ) -> ChatMessage:
        return ChatMessage(role=role, content=content, timestamp=datetime.now(UTC))

    def build_prompt_content(
        self, payload: AddPromptRequest
    ) -> str | list[dict[str, Any]]:
        content: str | list[dict[str, Any]] = payload.prompt

        if payload.file_url or payload.b64_file:
            parts: list[dict[str, Any]] = [
                {"type": "input_text", "text": payload.prompt}
            ]
            image_url = payload.file_url

            if payload.b64_file is not None:
                mime_type = self._get_mime_type(payload.file_type)
                image_url = f"data:{mime_type};base64,{payload.b64_file}"

            if image_url is not None:
                parts.append(
                    {
                        "type": "input_image",
                        "image_url": image_url,
                        "detail": "auto",
                    }
                )

            content = parts

        return content
