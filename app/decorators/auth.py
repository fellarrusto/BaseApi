import inspect
from functools import wraps
from typing import Callable, List, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.decorators._signature import (
    expose_signature,
    hidden_request_parameter,
    request_parameter,
    take_request,
)
from app.schemas.auth import AuthUser
from app.services.auth_service import auth_service

# Endpoint parameter that receives the authenticated user, if declared
CURRENT_USER_PARAM = "current_user"

# Hidden parameter injected by FastAPI, never seen by the endpoint
_CREDENTIALS_PARAM = "_auth_credentials"

# auto_error=False: a missing token raises UnauthorizedError, handled by @handle_errors.
# Declaring HTTPBearer also adds the "Authorize" button to Swagger.
_bearer_scheme = HTTPBearer(auto_error=False)


def require_auth(roles: Optional[List[str]] = None) -> Callable:
    """
    Require a valid bearer token and, if `roles` is given, at least one of them.

    The token is resolved by auth_service.authenticate(). The user is stored
    in request.state.user (read by @audit_log) and passed to the endpoint if
    it declares a `current_user: AuthUser` parameter.

    Raises:
        UnauthorizedError: Missing or invalid token (401)
        ForbiddenError: The user has none of the required roles (403)
    """
    required_roles = set(roles or [])

    def decorator(func: Callable) -> Callable:
        wants_user = CURRENT_USER_PARAM in inspect.signature(func).parameters
        request_name, forward_request = request_parameter(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = take_request(kwargs, request_name, forward_request)
            credentials: Optional[HTTPAuthorizationCredentials] = kwargs.pop(_CREDENTIALS_PARAM)
            if credentials is None:
                raise UnauthorizedError("Missing bearer token")

            user: AuthUser = await auth_service.authenticate(credentials.credentials)
            request.state.user = user
            if required_roles and not required_roles.intersection(user.roles):
                raise ForbiddenError("Insufficient role")

            if wants_user:
                kwargs[CURRENT_USER_PARAM] = user
            return await func(*args, **kwargs)

        credentials_param = inspect.Parameter(
            _CREDENTIALS_PARAM,
            inspect.Parameter.KEYWORD_ONLY,
            annotation=Optional[HTTPAuthorizationCredentials],
            default=Depends(_bearer_scheme)
        )
        expose_signature(
            wrapper,
            func,
            add=[credentials_param] if forward_request else [hidden_request_parameter(), credentials_param],
            remove=[CURRENT_USER_PARAM]
        )
        return wrapper
    return decorator
