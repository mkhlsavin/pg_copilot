"""
CodeGraph Leads Microservice.

FastAPI application for handling CTA form submissions.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.config import get_settings
from src.database.connection import close_db, init_db
from src.routers import health_router, leads_router
from src.routers.leads import limiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    logger.info(f"Starting CodeGraph Leads Service ({settings.environment})")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Log notification status
    logger.info(f"Notifications: email={settings.email_enabled}, telegram={settings.telegram_enabled}")

    yield

    # Cleanup
    await close_db()
    logger.info("CodeGraph Leads Service stopped")


# Create FastAPI application
app = FastAPI(
    title="CodeGraph Leads API",
    description="API for handling CTA form submissions from CodeGraph landing page",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# Custom exception handler for rate limiting
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded with Russian message."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Слишком много запросов. Пожалуйста, подождите немного.",
            "error": "rate_limit_exceeded",
        },
    )


# Include routers
app.include_router(
    leads_router,
    prefix="/api/v1/leads",
    tags=["leads"],
)
app.include_router(
    health_router,
    prefix="/api/v1/health",
    tags=["health"],
)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs."""
    return {
        "service": "codegraph-leads",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
