"""
Companion Researcher - FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .api import router
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting Companion Researcher...")

    # Ensure directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.personalities_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_db_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Companion Researcher started successfully")
    yield

    logger.info("Shutting down Companion Researcher...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    # Companion Researcher API

    An AI-powered research companion with configurable personalities.

    ## Features

    - **Natural Conversation**: Chat naturally with your companion
    - **Research Engine**: Automatic web research and synthesis
    - **Personality Profiles**: Switch between coach, researcher, producer modes
    - **Voice Output**: Generate speech using CSM model
    - **Session Memory**: Track conversation history

    ## Quick Start

    1. Send a message to `/api/chat` to start a conversation
    2. The companion auto-detects if you're asking a research question
    3. Customize personalities via `/api/personalities`
    """,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router, prefix="/api")

# Mount static files for frontend (if built)
frontend_build = Path(__file__).parent.parent / "frontend" / "build"
if frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="frontend")


@app.get("/")
async def root():
    """Root endpoint - redirect to docs or serve frontend"""
    return {
        "message": "Welcome to Companion Researcher",
        "docs": "/docs",
        "api": "/api",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "companion_researcher.backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
