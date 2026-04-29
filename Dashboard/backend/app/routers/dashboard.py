"""
Dashboard Router — serves pipeline summary, source distribution,
health metrics, and trend data to the frontend.
"""

from fastapi import APIRouter, Query
from app.services.dashboard_data import DashboardDataService

router = APIRouter()
_svc = DashboardDataService()


@router.get("/summary")
async def get_summary():
    """Return the latest pipeline summary.json."""
    data = _svc.get_summary()
    if data is None:
        return {"error": "No summary available yet. Run the pipeline first."}
    return data


@router.get("/sources")
async def get_source_distribution():
    """
    Return source distribution for charting.
    Example: { "arXiv": 12, "Apple ML": 3, "Meta AI": 2, ... }
    """
    return _svc.get_source_distribution()


@router.get("/health")
async def get_pipeline_health():
    """Return pipeline health metrics (last run, reports, HITL pending)."""
    return _svc.get_pipeline_health()


@router.get("/trends")
async def get_trend_data(days: int = Query(30, ge=1, le=365)):
    """Return daily paper counts for trend charting."""
    return _svc.get_trend_data(days)
