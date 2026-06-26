from collections.abc import Callable
from fastapi import Request
from app.core.config import settings
from rag_packages.shared.auth.token import JWTToken, JWTConfig


async def require_auth(request: Request, call_next: Callable) -> None:
    jwt_config = JWTConfig(
        secret=settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
        token_url=settings.JWT_TOKEN_URL,
        token_expires_in=settings.JWT_TOKEN_EXPIRES_IN,
    )
    token_helper = JWTToken(jwt_config)
    await token_helper.inject_auth_claims(request)

    return await call_next(request)
