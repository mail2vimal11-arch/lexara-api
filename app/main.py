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
from app.middleware.logging import LoggingMiddleware

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"🚀 {settings.app_name} v{settings.version} starting...")
    try:
        init_db()
        # Create procurement AI tables
        from app.database.session import Base, engine
        from app.models import user, tender, clause, audit, billing  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized")

        # Seed Ontario standard clauses + bootstrap FAISS index
        db = SessionLocal()
        try:
            from app.services.clause_seed import seed_clauses
            seeded = seed_clauses(db)
            if seeded:
                logger.info(f"✅ Seeded {seeded} standard clauses")

            # Seed reference tenders (fallback when APIs are unavailable)
            from app.services.tender_seed import seed_tenders
            tender_seeded = seed_tenders(db)
            if tender_seeded:
                logger.info(f"✅ Seeded {tender_seeded} reference tenders")

            from app.nlp.search import bootstrap_index_from_db
            bootstrap_index_from_db(db)
            logger.info("✅ FAISS index ready")

            # Skip live ingestion at startup — it blocks the app for 60-180s
            # when TED/OCP APIs are down. Reference tenders are already seeded.
            # Live ingestion runs on-demand via POST /v1/procurement/ingestion/run
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)

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
app.add_middleware(LoggingMiddleware)
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
