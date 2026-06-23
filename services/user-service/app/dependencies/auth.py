from dataclasses import dataclass

from fastapi import HTTPException, Request, status


@dataclass
class AuthContext:
    user_id: int
    email: str
    roles: list[str]


def get_auth_context(request: Request) -> AuthContext:
    claims = getattr(request.state, "auth_claims", None)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication context",
        )

    return AuthContext(
        user_id=int(claims["sub"]),
        email=claims["email"],
        roles=claims.get("roles", []),
    )
