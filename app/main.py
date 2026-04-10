"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database.session import init_db
from app.routers import contracts, usage, health, upload, billing, procurement
from app.middleware.auth import APIKeyMiddleware
from app.middleware.logging import LoggingMiddleware

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info(f"🚀 {settings.app_name} v{settings.version} starting...")
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 {settings.app_name} shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="AI-powered contract analysis engine for Canadian legal professionals",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
origins = [origin.strip() for origin in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(APIKeyMiddleware)

# Include Routers
app.include_router(health.router, tags=["Health"])
app.include_router(contracts.router, prefix="/v1", tags=["Contracts"])
app.include_router(upload.router, prefix="/v1", tags=["Upload"])
app.include_router(billing.router, prefix="/v1", tags=["Billing"])
app.include_router(usage.router, prefix="/v1", tags=["Usage"])
app.include_router(procurement.router, prefix="/v1/procurement", tags=["Procurement Tools"])

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request.headers.get("x-request-id", "unknown")
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
