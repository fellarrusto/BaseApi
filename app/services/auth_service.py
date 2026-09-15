import logging

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.schemas.auth import AuthUser

logger = logging.getLogger(__name__)

MOCK_TOKEN_PREFIX = "mock:"


class AuthService:
    """
    Turns a bearer token into an AuthUser.

    To add real authentication implement `_verify_token` only: the
    @require_auth decorator, the roles check and the audit already work.
    """

    async def authenticate(self, token: str) -> AuthUser:
        """
        Resolve the user behind a bearer token.

        Raises:
            UnauthorizedError: If the token is invalid
        """
        if settings.AUTH_MOCK_ENABLED and token.startswith(MOCK_TOKEN_PREFIX):
            return self._parse_mock_token(token)
        return await self._verify_token(token)

    async def _verify_token(self, token: str) -> AuthUser:
        """
        Verify a real token and return its user and roles.

        Not implemented yet: every token is rejected. Typical implementations:
        - Firebase: verify the ID token through an integration client,
          roles from the token custom claims
        - JWT/OIDC provider: check the signature against the provider JWKS,
          roles from a claim
        - Roles stored in the database: read them through a repository
        """
        logger.warning("AuthService._verify_token is not implemented: token rejected")
        raise UnauthorizedError("Authentication is not configured")

    def _parse_mock_token(self, token: str) -> AuthUser:
        """Local testing only: "mock:<user_id>" or "mock:<user_id>:<role1>,<role2>"."""
        user_id, _, roles = token[len(MOCK_TOKEN_PREFIX):].partition(":")
        if not user_id:
            raise UnauthorizedError("Invalid mock token, expected mock:<user_id>:<role1>,<role2>")
        return AuthUser(id=user_id, roles=[role.strip() for role in roles.split(",") if role.strip()])


auth_service = AuthService()
