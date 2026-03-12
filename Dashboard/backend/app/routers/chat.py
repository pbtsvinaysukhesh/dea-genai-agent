"""Chat Router — REST fallback (WebSocket preferred)"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.services.chat_service import ChatService

router = APIRouter()

class Msg(BaseModel):
    content: str
    paper_id: Optional[str] = None
    context: List[dict] = []

@router.post("/message")
async def message(msg: Msg):
    svc = ChatService()
    out = ""
    async for tok in svc.stream(msg.content, msg.paper_id, msg.context):
        out += tok
    return {"response": out}