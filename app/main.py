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
from app.routers import workbench_routes
from app.routers import portfolio_routes, bid_comparison_routes, dark_obligation_routes
from app.routers import obligation_temporal_routes  # Feature 3: Obligation Matrix
try:
    from app.routers import negotiation_routes  # Feature 6
except ImportError:
    negotiation_routes = None  # not yet implemented
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
        from app.models import user, tender, clause, audit, jurisdiction, commodity, knowledge  # noqa: F401
        from app.models import obligation_temporal  # noqa: F401  # Feature 3
        # Feature 6 models (import after creation):
        try:
            from app.models import negotiation  # noqa: F401
        except ImportError:
            logger.warning("Negotiation models not yet available")
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

            # Seed knowledge DB (commodity taxonomy + articles)
            try:
                from app.services.knowledge_seed import seed_all_knowledge
                knowledge_results = seed_all_knowledge(db)
                if knowledge_results:
                    logger.info(f"✅ Knowledge DB seeded: {knowledge_results}")
            except ImportError:
                logger.warning("knowledge_seed module not yet available — skipping")

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
# Feature 2: SOW Workbench
# NOTE: /v1/workbench/commodities and /v1/workbench/jurisdictions are public endpoints.
#       Add them to app/middleware/auth.py UNPROTECTED_ROUTES:
#           "/v1/workbench/commodities",
#           "/v1/workbench/jurisdictions",
app.include_router(workbench_routes.router, prefix="/v1/workbench", tags=["SOW Workbench"])
# Feature 6: Negotiation Simulator (router registered when module is available)
if negotiation_routes is not None:
    app.include_router(negotiation_routes.router, prefix="/v1/negotiation", tags=["Negotiation Simulator"])
# Blast Radius engine: portfolio obligation index, N-bid stress matrix, dark-obligation detector
app.include_router(portfolio_routes.router)
app.include_router(bid_comparison_routes.router)
app.include_router(dark_obligation_routes.router)
# Feature 3: Obligation Matrix — temporal dependency graph
app.include_router(obligation_temporal_routes.router, prefix="/v1/procurement", tags=["Obligation Matrix"])

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
