"""Health check endpoints for the ATS Agent.

This module provides health check functionality to monitor
the service status and readiness.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ats_agent.src.schema import HealthResponse
from ats_agent.src.core.manager import get_global_manager
from ats_agent.src.settings import settings
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check service health and readiness.
    
    Returns:
        Health status information
        
    Raises:
        HTTPException: If service is unhealthy
    """
    try:
        # Basic health check
        health_status = {
            "status": "healthy",
            "service": "ATS Resume Reviewer Agent",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
        
        # Check agent availability (optional deeper check)
        try:
            manager = await get_global_manager()
            if manager.agent is None:
                logger.warning("ATS agent not initialized")
                health_status["status"] = "degraded"
                health_status["warning"] = "Agent not fully initialized"
        except Exception as e:
            logger.error(f"Agent health check failed: {e}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            
            # Return 503 for unhealthy status
            return JSONResponse(
                status_code=503,
                content=health_status
            )
        
        logger.debug("Health check completed successfully")
        return HealthResponse(**health_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "service": "ATS Resume Reviewer Agent",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/health/ready")
async def readiness_check() -> dict:
    """Check service readiness for traffic.
    
    Returns:
        Readiness status
        
    Raises:
        HTTPException: If service is not ready
    """
    try:
        # Check dependencies and initialization
        manager = await get_global_manager()
        
        if manager.agent is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "ready": False,
                    "message": "ATS agent not initialized",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        return {
            "ready": True,
            "service": "ATS Resume Reviewer Agent",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/health/live")
async def liveness_check() -> dict:
    """Check service liveness (basic responsiveness).
    
    Returns:
        Liveness status
    """
    return {
        "alive": True,
        "service": "ATS Resume Reviewer Agent",
        "timestamp": datetime.now().isoformat(),
        "environment": settings.AGENT_ENV
    }