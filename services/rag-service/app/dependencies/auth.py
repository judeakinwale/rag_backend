from enum import StrEnum
from typing import Annotated

from app.utils.token_validation import EntraTokenValidator, EntraUser
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from jose import jwt


class AuthProvider(StrEnum):
    AZURE_ENTRA = "azure"
    GOOGLE = "google"
    FACEBOOK = "facebook"
    GITHUB = "github"


security = HTTPBearer(auto_error=False)


def decode_jwt_token(token: str) -> dict:
    payload = jwt.decode(token, options={"verify_signature": False})
    return payload


# TODO: confirm this works with the EntraTokenValidator and the EntraUser model
def validate_jwt_token(
    request: Request, token: str, provider: AuthProvider = AuthProvider.AZURE_ENTRA
) -> dict | False:
    if not token or provider is None:
        return False

    match provider:
        case AuthProvider.AZURE_ENTRA:
            # # add EntraTokenValidator to lifespan.py and initialize
            validator: EntraTokenValidator = request.app.state.entra_validator
            validatedInfo: EntraUser = validator.validate_token(token)
            return validatedInfo

    return False


def get_current_user(
    request: Request, credentials: Annotated[HTTPBearer, Depends(security)]
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing credentials")

    token = credentials.credentials

    # Here you would typically decode the JWT token and extract user information
    # For demonstration purposes, we'll just return a dummy user
    user = validate_jwt_token(request, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user
