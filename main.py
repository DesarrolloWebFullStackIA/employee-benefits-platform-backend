import logging
import time
from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config.config_variables import settings
from routes.routes import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pluxee_backend")

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Pluxee Enterprise HR Suite (Benefits & Expenses Management)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Global CORS Middleware
cors_origins: List[str] = (
    settings.CORS_ORIGINS
    if isinstance(settings.CORS_ORIGINS, list)
    else [str(settings.CORS_ORIGINS)]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Request Logging Middleware
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - Completed in {duration:.4f}s"
    )
    return response


# System Health and Root Endpoints
@app.get("/", tags=["System"])
def root():
    """Root welcome endpoint providing service information and API links."""
    return {
        "success": True,
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health",
        "api_v1": f"{settings.API_V1_STR}/status",
    }


@app.get("/health", tags=["System"])
def health():
    """Health check endpoint to verify server availability."""
    return {
        "success": True,
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }


# Mount API v1 router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
