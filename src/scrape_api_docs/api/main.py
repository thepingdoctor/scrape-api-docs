"""
FastAPI Application - Main Entry Point
======================================

FastAPI REST API for documentation scraping with full async support,
job management, WebSocket progress tracking, and enterprise features.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from .routers import scrape, jobs, exports, auth, system
from .middleware import LoggingMiddleware, RateLimitMiddleware
from .services.job_service import JobService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Starting Documentation Scraper API v2.0.0")

    # Initialize services
    job_service = JobService()
    await job_service.initialize()
    app.state.job_service = job_service

    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down API")
    await job_service.cleanup()
    logger.info("API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Documentation Scraper API",
    version="2.0.0",
    description=(
        "REST API for scraping and exporting documentation websites. "
        "Supports async operations, job management, WebSocket progress tracking, "
        "and multiple export formats (Markdown, PDF, JSON, EPUB)."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)


# Add middleware (order matters - last added is executed first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)


# Include routers
app.include_router(
    scrape.router,
    prefix="/api/v1/scrape",
    tags=["Scraping Operations"]
)
app.include_router(
    jobs.router,
    prefix="/api/v1/jobs",
    tags=["Job Management"]
)
app.include_router(
    exports.router,
    prefix="/api/v1/exports",
    tags=["Export Operations"]
)
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)
app.include_router(
    system.router,
    prefix="/api/v1/system",
    tags=["System Operations"]
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc) if app.debug else None
            }
        }
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint with service information."""
    return {
        "service": "Documentation Scraper API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/api/docs",
        "health": "/api/v1/system/health"
    }


# Health check (simple version at root level)
@app.get("/health", tags=["Root"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
