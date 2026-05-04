"""Request/response logging middleware.

Uses a plain async function registered via @app.middleware("http") rather than
BaseHTTPMiddleware to avoid the Starlette body double-read bug that corrupts
JSON request bodies when multiple BaseHTTPMiddleware instances are stacked.
"""

from fastapi import Request
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)


async def logging_middleware(request: Request, call_next):
    """Log all requests and responses without touching the request body."""

    # Add request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Log request
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Client: {request.client.host if request.client else 'unknown'} - "
        f"Request ID: {request_id}"
    )

    # Process request — body is never read here
    start_time = datetime.utcnow()
    response = await call_next(request)
    process_time = (datetime.utcnow() - start_time).total_seconds()

    # Log response
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {process_time:.3f}s - "
        f"Request ID: {request_id}"
    )

    # Add request ID to response header
    response.headers["X-Request-ID"] = request_id

    return response
