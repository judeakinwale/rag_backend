from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from jose import jwt
from jose.exceptions import JWTError


@dataclass
class EntraUser:
    tenant_id: str
    object_id: str
    display_name: str | None
    username: str | None
    scopes: list[str]
    roles: list[str]


class EntraTokenValidator:
    """
    Validates Microsoft Entra ID access tokens using python-jose.
    """

    def __init__(
        self,
        tenant_id: str,
        audience: str | None = None,
    ):
        self.tenant_id = tenant_id
        self.audience = audience
        self.signingKey: Any
        self.signingExp: datetime

        self.issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"

        self.jwks_url = (
            f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        )

        # Cache Microsoft's signing keys.
        self.jwks = self._load_jwks()

    def _load_jwks(self) -> dict:
        response = requests.get(
            self.jwks_url,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()

    def _get_signing_key(self, token: str) -> dict:
        """
        Find the Microsoft public JWK corresponding to
        the token's 'kid'.
        """

        if (
            (self.signingKey is not None)
            and (self.signingExp is not None)
            and (datetime.now(UTC) < self.signingExp)
        ):
            return self.signingKey

        header = jwt.get_unverified_header(token)

        kid = header.get("kid")

        if not kid:
            raise JWTError("Token does not contain a kid")

        for key in self.jwks.get("keys", []):
            if key.get("kid") == kid:
                return key

        # Microsoft's signing keys can rotate. Refresh the JWKS
        # once if the key isn't currently cached.
        self.jwks = self._load_jwks()

        for key in self.jwks.get("keys", []):
            if key.get("kid") == kid:
                self.signingKey = key
                self.signingExp = datetime.now(UTC) + timedelta(hours=24)
                return key

        raise JWTError(f"Unable to find signing key for kid={kid}")

    def validate_token(self, token: str) -> EntraUser:
        """
        Cryptographically validate an Entra access token and
        return the authenticated user's information.
        """

        signing_key = self._get_signing_key(token)

        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={
                "verify_signature": True,
                "verify_aud": bool(self.audience),  # True,
                "verify_iss": True,
                "verify_exp": True,
                "verify_nbf": True,
                # Require these claims to be present.
                "require_exp": True,
                "require_iat": True,
                "require_nbf": True,
                "require_iss": True,
                "require_aud": bool(self.audience),  # True,
            },
        )

        # Make absolutely sure the tenant is the tenant
        # this validator was configured to trust.
        if claims.get("tid") != self.tenant_id:
            raise JWTError("Token was issued for an unexpected tenant")

        object_id = claims.get("oid")

        if not object_id:
            raise JWTError("Token does not contain an oid claim")

        scopes = claims.get("scp", "")
        scopes = scopes.split() if scopes else []

        roles = claims.get("roles", [])

        return EntraUser(
            tenant_id=claims["tid"],
            object_id=object_id,
            display_name=claims.get("name"),
            username=claims.get("preferred_username"),
            scopes=scopes,
            roles=roles,
        )
