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


# NOTE:
# # user service -> auth service
# {
#   "id": 123,
#   "email": "user@example.com",
#   "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$...",
#   "is_active": true
# }

# # in auth service
# user = await user_client.get_user_credentials_by_email(email)
# if user is None:
#     deny()

# if not verify_password(password, user["password_hash"]):
#     deny()

# # auth service -> user service
# token = issue_access_token(
#     sub=str(user["id"]),
#     email=user["email"],
#     roles=["user"],
# )
