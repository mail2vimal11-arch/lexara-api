"""API key authentication middleware.

Security note: any change to this file must be reviewed.
Auth bypass was fixed in 25fdee4; JWT validation added at middleware layer — CA-008.
"""

from fastapi import Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate JWT for protected /v1 routes.

    Defense in depth: middleware validates the JWT signature so clearly invalid
    tokens are rejected before reaching the route layer.  Full user lookup
    (is_active check, DB query) still happens in get_current_user at route level.
    """

    UNPROTECTED_ROUTES = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/",
        "/v1/auth/register",
        "/v1/auth/login",
    }

    async def dispatch(self, request: Request, call_next):
        """Process request."""

        # Always pass through OPTIONS (CORS preflight) and Stripe webhook
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in ("/v1/webhook", "/v1/webhooks/stripe"):
            return await call_next(request)

        # Skip auth for public routes
        if request.url.path in self.UNPROTECTED_ROUTES:
            return await call_next(request)

        if request.url.path.startswith("/v1"):
            auth_header = request.headers.get("Authorization", "")

            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "message": "Invalid or missing Authorization header"},
                )

            # CA-008: validate JWT signature at middleware layer (defense in depth)
            token = auth_header.split(" ", 1)[1]
            try:
                jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            except JWTError:
                return JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "message": "Invalid or expired token"},
                )

        response = await call_next(request)
        return response
