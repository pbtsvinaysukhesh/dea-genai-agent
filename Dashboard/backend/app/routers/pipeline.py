"""
Pipeline Router — Control and monitor the AI research pipeline
REST endpoints for status polling + WebSocket for streaming progress
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.services.pipeline import PipelineService

router = APIRouter()
pipeline_service = PipelineService()


class PipelineStatusResponse(BaseModel):
    """Pipeline status response model"""
    status: str  # idle, running, completed, failed
    progress: int  # 0-100
    stage: str  # current stage
    message: str  # status message
    stats: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status():
    """
    Get current pipeline status
    Used for polling fallback when WebSocket unavailable
    """
    status_dict = pipeline_service.get_status()
    return PipelineStatusResponse(
        status=status_dict.get("status", "unknown"),
        progress=status_dict.get("progress", 0),
        stage=status_dict.get("stage", "idle"),
        message=status_dict.get("message", ""),
        stats=status_dict.get("stats"),
        started_at=status_dict.get("started_at"),
        completed_at=status_dict.get("completed_at"),
        error=status_dict.get("error"),
    )


@router.post("/start")
async def start_pipeline():
    """
    Start the AI pipeline (non-blocking)
    Returns immediately; use WebSocket or polling for progress
    """
    if pipeline_service.is_running():
        return {
            "status": "already_running",
            "message": "Pipeline already running",
            "progress": pipeline_service.get_status().get("progress", 0),
        }

    try:
        pipeline_service.start()
        return {
            "status": "started",
            "message": "Pipeline started successfully",
            "progress": 0,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to start pipeline: {str(e)}",
            "error": str(e),
        }


@router.post("/stop")
async def stop_pipeline():
    """
    Stop the running pipeline
    Gracefully terminates current operation
    """
    if not pipeline_service.is_running():
        return {
            "status": "not_running",
            "message": "Pipeline is not running",
        }

    try:
        pipeline_service.stop()
        return {
            "status": "stopped",
            "message": "Pipeline stopped successfully",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to stop pipeline: {str(e)}",
            "error": str(e),
        }


@router.get("/health")
async def pipeline_health():
    """
    Health check for pipeline service
    Returns service status and availability
    """
    try:
        is_healthy = pipeline_service.health_check()
        return {
            "status": "healthy" if is_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "service": "pipeline",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "service": "pipeline",
            "error": str(e),
        }
