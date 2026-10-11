from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager: runs startup and shutdown tasks."""
    logger.info(
        "Starting up %s (version: %s)...", settings.PROJECT_NAME, settings.VERSION
    )
    # Ensure storage directories exist
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    # Initialize database tables

    await init_db()
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Scalable, asynchronous backend API for bulk certificate generation with fault isolation and verification.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Enable CORS for local dashboards / clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API v1 router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENV,
        }

    @app.get(
        "/", response_class=FileResponse, tags=["Dashboard"], include_in_schema=False
    )
    async def dashboard():
        """Serve the interactive web dashboard."""
        html_file = Path(__file__).parent / "static" / "index.html"
        return FileResponse(html_file, media_type="text/html")

    return app


app = create_application()
