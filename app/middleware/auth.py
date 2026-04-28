"""API key authentication middleware."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate API keys for protected routes."""
    
    # Routes that don't require authentication
    UNPROTECTED_ROUTES = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/",
        "/v1/auth/register",
        "/v1/auth/login",
        "/v1/plans",     # public — visitors must see plans before signing up
        "/v1/checkout",  # public — Stripe checkout doesn't require a Lexara account
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
        
        # Require auth for API routes — actual JWT validation is handled
        # by Depends(get_current_user) at the route level.
        # Middleware only rejects requests that are missing the Bearer prefix entirely.
        if request.url.path.startswith("/v1"):
            auth_header = request.headers.get("Authorization", "")

            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authorization header missing or malformed"},
                    headers={"WWW-Authenticate": "Bearer"},  # RFC 6750 §3.1
                )
        
        response = await call_next(request)
        return response
