"""
Main FastAPI application
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.services.database import init_db, close_db
from app.services.redis import redis_service
from app.services.seed import seed_demo_data
from app.api.endpoints import (
    auth,
    projects,
    schedules,
    suppliers,
    procurement,
    risks,
    recommendations,
    analytics,
    reports,
    agents,
    conversation,
    upload,
    notifications,
    intelligence
)

settings = get_settings()
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting AI Project Monitoring & Risk Engine")
    await init_db()
    await redis_service.connect()
    if settings.seed_demo_data:
        await seed_demo_data()
        from app.services.intelligence_hub import hub
        hub.initialize()
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    await close_db()
    await redis_service.disconnect()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Autonomous AI platform for monitoring Data Centre EPC Projects",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods.split(",") if settings.cors_allow_methods != "*" else ["*"],
    allow_headers=settings.cors_allow_headers.split(",") if settings.cors_allow_headers != "*" else ["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env
    }


# Include API routers
app.include_router(
    auth.router,
    prefix=f"{settings.api_prefix}/auth",
    tags=["Authentication"]
)

app.include_router(
    projects.router,
    prefix=f"{settings.api_prefix}/projects",
    tags=["Projects"]
)

app.include_router(
    schedules.router,
    prefix=f"{settings.api_prefix}/schedules",
    tags=["Schedules"]
)

app.include_router(
    suppliers.router,
    prefix=f"{settings.api_prefix}/suppliers",
    tags=["Suppliers"]
)

app.include_router(
    procurement.router,
    prefix=f"{settings.api_prefix}/procurement",
    tags=["Procurement"]
)

app.include_router(
    risks.router,
    prefix=f"{settings.api_prefix}/risks",
    tags=["Risks"]
)

app.include_router(
    recommendations.router,
    prefix=f"{settings.api_prefix}/recommendations",
    tags=["Recommendations"]
)

app.include_router(
    analytics.router,
    prefix=f"{settings.api_prefix}/analytics",
    tags=["Analytics"]
)

app.include_router(
    reports.router,
    prefix=f"{settings.api_prefix}/reports",
    tags=["Reports"]
)

app.include_router(
    agents.router,
    prefix=f"{settings.api_prefix}/agents",
    tags=["Agents"]
)

app.include_router(
    conversation.router,
    prefix=f"{settings.api_prefix}/conversation",
    tags=["Conversation"]
)

app.include_router(
    upload.router,
    prefix=f"{settings.api_prefix}/upload",
    tags=["Upload"]
)

app.include_router(
    notifications.router,
    prefix=f"{settings.api_prefix}/notifications",
    tags=["Notifications"]
)

app.include_router(
    intelligence.router,
    prefix=f"{settings.api_prefix}/intelligence",
    tags=["Unified Project Intelligence"]
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


# Serve the built frontend (single-host mode: same process/port serves the API and the SPA)
_frontend_dist = settings.frontend_dist_path
if _frontend_dist.exists():
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(request: Request, full_path: str):
        """SPA catch-all: serve index.html for any non-API route so client-side routing works."""
        if full_path.startswith("api/") or full_path in ("health",):
            raise HTTPException(status_code=404, detail="Not found")

        candidate = _frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(_frontend_dist / "index.html")
else:
    logger.warning(
        f"Frontend build not found at {_frontend_dist} — run `npm run build` in frontend/ to serve it from this app."
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers
    )
