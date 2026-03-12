"""Stats Router"""
from fastapi import APIRouter
from app.services.data_service import DataService
router = APIRouter()

@router.get("/")
async def stats():
    return DataService().get_statistics()