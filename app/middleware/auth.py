"""API key authentication middleware.

Security note: any change to this file must be reviewed.
Auth bypass was fixed in 25fdee4; JWT validation added at middleware layer — CA-008.
"""

from fastapi import Request
from jose import ExpiredSignatureError, JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate JWT for protected /v1 routes.

    Defense in depth: middleware validates the JWT signature so clearly invalid
    tokens are rejected before reaching the route layer. Full user lookup
    (is_active check, DB query) still happens in get_current_user at route level.
    """

    # Routes that don't require authentication (exact match)
    UNPROTECTED_ROUTES = {
        "/health",
        "/status",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/",
        "/v1/auth/register",
        "/v1/auth/login",
        "/v1/plans",
        "/v1/checkout",
        "/v1/workbench/commodities",
        "/v1/workbench/jurisdictions",
    }

    # Route prefixes that don't require authentication (startswith match)
    UNPROTECTED_PREFIXES = (
        "/v1/negotiation/join/",
    )

    async def dispatch(self, request: Request, call_next):
        """Process request."""

        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in ("/v1/webhook", "/v1/webhooks/stripe"):
            return await call_next(request)

        if request.url.path in self.UNPROTECTED_ROUTES:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in self.UNPROTECTED_PREFIXES):
            return await call_next(request)

        if request.url.path.startswith("/v1"):
            auth_header = request.headers.get("Authorization", "")

            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid authentication token"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # CA-008: validate JWT signature at middleware layer (defense in depth)
            # ExpiredSignatureError must be caught BEFORE the generic JWTError,
            # since ExpiredSignatureError is a subclass of JWTError.
            token = auth_header.split(" ", 1)[1]
            try:
                jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            except ExpiredSignatureError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token has expired. Please log in again."},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except JWTError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid authentication token"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        response = await call_next(request)
        return response
