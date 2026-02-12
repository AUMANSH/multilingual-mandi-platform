"""
Health check endpoints for monitoring system status.

This module provides comprehensive health checks for all system components
including database, Redis, and Elasticsearch connectivity.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import structlog

from ..database import get_database_manager
from ..redis_client import get_redis_manager
from ..elasticsearch_client import get_elasticsearch_manager
from ..config import settings

logger = structlog.get_logger(__name__)

router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model."""
    status: str
    version: str
    timestamp: str
    components: Dict[str, Any]


class ComponentHealth(BaseModel):
    """Individual component health status."""
    status: str
    response_time_ms: float
    details: Dict[str, Any] = {}


@router.get("/", response_model=HealthStatus)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns overall system health status with component details.
    """
    import time
    from datetime import datetime
    
    start_time = time.time()
    components = {}
    overall_status = "healthy"
    
    # Check database connectivity
    try:
        db_start = time.time()
        db_manager = get_database_manager()
        async with db_manager.engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        components["database"] = ComponentHealth(
            status="healthy",
            response_time_ms=round((time.time() - db_start) * 1000, 2),
            details={"url": settings.database_url.split("@")[-1]},  # Hide credentials
        )
        
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        components["database"] = ComponentHealth(
            status="unhealthy",
            response_time_ms=round((time.time() - db_start) * 1000, 2),
            details={"error": str(e)},
        )
        overall_status = "unhealthy"
    
    # Check Redis connectivity
    try:
        redis_start = time.time()
        redis_manager = get_redis_manager()
        is_connected = await redis_manager.ping()
        
        if is_connected:
            components["redis"] = ComponentHealth(
                status="healthy",
                response_time_ms=round((time.time() - redis_start) * 1000, 2),
                details={"url": settings.redis_url.split("@")[-1]},  # Hide credentials
            )
        else:
            raise Exception("Redis ping failed")
            
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        components["redis"] = ComponentHealth(
            status="unhealthy",
            response_time_ms=round((time.time() - redis_start) * 1000, 2),
            details={"error": str(e)},
        )
        overall_status = "unhealthy"
    
    # Check Elasticsearch connectivity
    try:
        es_start = time.time()
        es_manager = get_elasticsearch_manager()
        is_connected = await es_manager.ping()
        
        if is_connected:
            components["elasticsearch"] = ComponentHealth(
                status="healthy",
                response_time_ms=round((time.time() - es_start) * 1000, 2),
                details={"url": settings.elasticsearch_url},
            )
        else:
            raise Exception("Elasticsearch ping failed")
            
    except Exception as e:
        logger.error("Elasticsearch health check failed", error=str(e))
        components["elasticsearch"] = ComponentHealth(
            status="unhealthy",
            response_time_ms=round((time.time() - es_start) * 1000, 2),
            details={"error": str(e)},
        )
        overall_status = "unhealthy"
    
    total_response_time = round((time.time() - start_time) * 1000, 2)
    
    health_status = HealthStatus(
        status=overall_status,
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        components={
            **{name: comp.dict() for name, comp in components.items()},
            "total_response_time_ms": total_response_time,
        },
    )
    
    # Return appropriate HTTP status
    if overall_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status.dict(),
        )
    
    return health_status


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/container orchestration.
    
    Returns 200 if the service is ready to accept traffic.
    """
    try:
        # Quick check of critical components
        db_manager = get_database_manager()
        redis_manager = get_redis_manager()
        es_manager = get_elasticsearch_manager()
        
        # Simple connectivity checks
        async with db_manager.engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        await redis_manager.ping()
        await es_manager.ping()
        
        return {"status": "ready"}
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "error": str(e)},
        )


@router.get("/live")
async def liveness_check():
    """
    Liveness check for Kubernetes/container orchestration.
    
    Returns 200 if the service is alive (basic functionality).
    """
    return {"status": "alive", "timestamp": "2024-01-01T00:00:00Z"}


@router.get("/metrics")
async def metrics():
    """
    Basic metrics endpoint for monitoring.
    
    Returns system metrics and statistics.
    """
    import psutil
    import time
    from datetime import datetime
    
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        # Application metrics
        uptime = time.time() - psutil.Process().create_time()
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": round(memory.used / 1024 / 1024, 2),
                "memory_total_mb": round(memory.total / 1024 / 1024, 2),
                "disk_percent": round((disk.used / disk.total) * 100, 2),
                "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            },
            "application": {
                "uptime_seconds": round(uptime, 2),
                "version": "0.1.0",
                "debug_mode": settings.debug,
                "supported_languages": settings.supported_languages,
            },
        }
        
    except Exception as e:
        logger.error("Metrics collection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to collect metrics"},
        )