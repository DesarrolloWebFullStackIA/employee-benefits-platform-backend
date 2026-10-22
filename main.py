from contextlib import asynccontextmanager
import logging
import time
from typing import List

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.config_variables import settings
from database.database import init_db
from routes.routes import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pluxee_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler: create database tables on startup."""
    logger.info("Initializing database tables...")
    init_db()
    logger.info("Database tables initialized successfully.")
    yield


# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Pluxee Enterprise HR Suite (Benefits & Expenses Management)",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
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
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
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


# Centralized Exception Handlers (CA-BE-01.4)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Standardize HTTP exceptions to JSON format { 'success': false, 'detail': ... }"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Standardize validation errors to JSON format { 'success': false, 'detail': ... }"""
    first_error = exc.errors()[0]["msg"] if exc.errors() else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "detail": f"Validation error: {first_error}",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all unexpected internal server errors."""
    logger.error(
        f"Unhandled internal error on {request.url.path}: {str(exc)}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "detail": "Internal server error"},
    )


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
