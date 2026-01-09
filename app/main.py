"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.lifespan import lifespan
from app.core.logging import setup_logging
from dotenv import load_dotenv

load_dotenv(override=True)
setup_logging(level="INFO", json_output=False)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="RAS - Research Assistant System",
        description="Multi-agent system for analyzing research writing",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    application.include_router(router, prefix="/api/v1")

    @application.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "RAS - Research Assistant System",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return application


app = create_app()
