"""
FastAPI Application Factory.

Main entry point for the RAG-CPGQL REST API.
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.api import __version__
from src.api.config import get_settings, CORSConfig
from src.api.database.connection import init_db, close_db
from src.api.utils.responses import (
    error_response,
    validation_error_response,
    generate_request_id,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Server start time for uptime calculation
_start_time: float = 0


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    global _start_time

    # Startup
    logger.info("Starting RAG-CPGQL API...")
    _start_time = time.time()

    db_initialized = False
    try:
        # Initialize database (optional - gracefully handle missing database)
        try:
            await init_db()
            db_initialized = True
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(f"Database initialization skipped: {e}")
            logger.info("Running in limited mode (no database)")

        # TODO: Initialize other services (LLM, Joern, etc.)

        logger.info(f"RAG-CPGQL API v{__version__} started successfully")
        yield

    finally:
        # Shutdown
        logger.info("Shutting down RAG-CPGQL API...")
        if db_initialized:
            await close_db()
            logger.info("Database connections closed")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    cors_config = CORSConfig()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.allowed_origins,
        allow_credentials=cors_config.allow_credentials,
        allow_methods=cors_config.allowed_methods,
        allow_headers=cors_config.allowed_headers,
        max_age=cors_config.max_age,
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add request ID to all requests."""
        request_id = request.headers.get("X-Request-ID", generate_request_id())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response

    # Request timing middleware
    @app.middleware("http")
    async def add_process_time(request: Request, call_next):
        """Add processing time header to responses."""
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000  # Convert to ms
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        return response

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle validation errors."""
        errors = []
        for error in exc.errors():
            errors.append({
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", ""),
                "type": error.get("type", "unknown"),
            })

        request_id = getattr(request.state, "request_id", None)
        return validation_error_response(errors, request_id)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.exception(f"Unhandled exception: {exc}")
        request_id = getattr(request.state, "request_id", None)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    # Include routers
    _include_routers(app)

    return app


def _include_routers(app: FastAPI) -> None:
    """Include all API routers."""
    from src.api.routers import auth, chat, scenarios, review, sessions, history, health, query, stats, demo
    from src.api.routers import import_project

    # API v1 prefix
    api_v1 = "/api/v1"

    app.include_router(auth.router, prefix=f"{api_v1}/auth", tags=["Authentication"])
    app.include_router(chat.router, prefix=f"{api_v1}/chat", tags=["Chat"])
    app.include_router(scenarios.router, prefix=f"{api_v1}/scenarios", tags=["Scenarios"])
    app.include_router(review.router, prefix=f"{api_v1}/review", tags=["Code Review"])
    app.include_router(sessions.router, prefix=f"{api_v1}/sessions", tags=["Sessions"])
    app.include_router(history.router, prefix=f"{api_v1}/history", tags=["History"])
    app.include_router(health.router, prefix=f"{api_v1}/health", tags=["Health"])
    app.include_router(query.router, prefix=f"{api_v1}/query", tags=["Query"])
    app.include_router(stats.router, prefix=f"{api_v1}/stats", tags=["Statistics"])
    app.include_router(demo.router, prefix=f"{api_v1}/demo", tags=["Demo"])
    app.include_router(import_project.router, prefix=f"{api_v1}/import", tags=["Project Import"])

    # WebSocket routes
    from src.api.websocket import routes as ws_routes
    app.include_router(ws_routes.router, prefix=f"{api_v1}/ws", tags=["WebSocket"])


def get_uptime() -> float:
    """Get server uptime in seconds."""
    global _start_time
    if _start_time == 0:
        return 0
    return time.time() - _start_time


# Create the application instance
app = create_app()


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs."""
    return {
        "name": "RAG-CPGQL API",
        "version": __version__,
        "docs": "/api/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
    )
