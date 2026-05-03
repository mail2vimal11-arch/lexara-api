"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database.session import init_db, SessionLocal
from app.routers import contracts, usage, health, upload, billing, procurement
from app.routers import auth_routes, procurement_clause_routes, ingestion_routes, compare_routes
from app.middleware.auth import APIKeyMiddleware
from app.middleware.logging import logging_middleware

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"🚀 {settings.app_name} v{settings.version} starting...")

    # CA-024 / CA-029: DB init is critical — re-raise on failure so the container
    # exits with a non-zero code rather than starting in a degraded state.
    try:
        init_db()
        from app.database.session import Base, engine
        from app.models import user, tender, clause, audit, billing  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.critical(f"❌ Database initialization failed — refusing to start: {e}", exc_info=True)
        raise

    # Non-critical startup tasks: seeding and FAISS bootstrap.
    # Failures here are logged but do NOT prevent the app from starting.
    db = SessionLocal()
    try:
        from app.services.clause_seed import seed_clauses
        seeded = seed_clauses(db)
        if seeded:
            logger.info(f"✅ Seeded {seeded} standard clauses")

        from app.services.tender_seed import seed_tenders
        tender_seeded = seed_tenders(db)
        if tender_seeded:
            logger.info(f"✅ Seeded {tender_seeded} reference tenders")

        from app.nlp.search import bootstrap_index_from_db
        bootstrap_index_from_db(db)
        logger.info("✅ FAISS index ready")
    except Exception as e:
        logger.error(f"❌ Non-critical startup task failed (app will still serve requests): {e}", exc_info=True)
    finally:
        db.close()

    yield

    logger.info("🛑 Shutting down...")


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
# LoggingMiddleware registered as plain async function (not BaseHTTPMiddleware)
# to avoid the Starlette body double-read bug that corrupts JSON request bodies.
app.middleware("http")(logging_middleware)
app.add_middleware(APIKeyMiddleware)

# Include Routers
app.include_router(health.router, tags=["Health"])
app.include_router(contracts.router, prefix="/v1", tags=["Contracts"])
app.include_router(upload.router, prefix="/v1", tags=["Upload"])
app.include_router(billing.router, prefix="/v1", tags=["Billing"])
app.include_router(usage.router, prefix="/v1", tags=["Usage"])
app.include_router(procurement.router, prefix="/v1/procurement", tags=["Procurement Tools"])
# Procurement AI — new modules
app.include_router(auth_routes.router, prefix="/v1")
app.include_router(procurement_clause_routes.router, prefix="/v1/procurement")
app.include_router(ingestion_routes.router, prefix="/v1/procurement")
app.include_router(compare_routes.router, prefix="/v1/procurement")

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
