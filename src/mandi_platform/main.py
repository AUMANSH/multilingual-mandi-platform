"""
Main FastAPI application for the Multilingual Mandi Platform.

This module sets up the FastAPI application with all necessary middleware,
routers, and lifecycle event handlers.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog

from .config import settings
from .database import close_database, init_database, get_db_session
from .redis_client import close_redis
from .elasticsearch_client import close_elasticsearch
from .api.health import router as health_router
from .api.auth import router as auth_router
from .api.translation import router as translation_router
from .api.products import router as products_router
from .auth.middleware import AuthMiddleware, RateLimitMiddleware


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Multilingual Mandi Platform")
    
    try:
        # Initialize database tables (in development)
        if settings.debug:
            await init_database()
            logger.info("Database initialized")
        
        logger.info("Application startup complete")
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down Multilingual Mandi Platform")
        
        # Close database connections
        await close_database()
        logger.info("Database connections closed")
        
        # Close Redis connections
        await close_redis()
        logger.info("Redis connections closed")
        
        # Close Elasticsearch connections
        await close_elasticsearch()
        logger.info("Elasticsearch connections closed")
        
        logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Multilingual Mandi Platform",
        description=(
            "AI-driven price discovery and negotiation platform for local Indian vendors. "
            "Supports 10 Indian languages with real-time translation, cultural context "
            "awareness, and intelligent market analysis."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # Add security middleware
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Configure properly in production
        )
    
    # Add authentication middleware
    app.add_middleware(AuthMiddleware)
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests."""
        start_time = structlog.get_logger().info
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
            )
            
            return response
            
        except Exception as e:
            # Log error
            logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                exc_info=True,
            )
            
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
    
    # Include routers
    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    app.include_router(translation_router, tags=["Translation"])
    app.include_router(products_router, prefix="/api", tags=["Products"])
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions."""
        logger.error(
            "Unhandled exception",
            url=str(request.url),
            method=request.method,
            error=str(exc),
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc) if settings.debug else "An error occurred",
            },
        )
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "mandi_platform.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        workers=settings.workers if not settings.reload else 1,
    )