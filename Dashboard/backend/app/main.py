"""
AGI Research Intelligence Dashboard — FastAPI Backend
Modular architecture: routers / services / models
"""

import os, json, asyncio, logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.routers import papers, chat, pipeline, stats, hitl
from app.services.connection_manager import ConnectionManager
from app.services.chat_service import ChatService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

manager = ConnectionManager()
chat_service = ChatService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    for d in ["data/hitl_review/pending", "data/hitl_review/approved",
              "data/hitl_review/rejected", "results/daily", "results/archive", "logs"]:
        os.makedirs(d, exist_ok=True)
    logger.info("✅ AGI Dashboard started")
    yield
    logger.info("AGI Dashboard shutting down")


app = FastAPI(
    title="AGI Research Intelligence",
    description="On-Device AI Research Intelligence Dashboard",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(papers.router,   prefix="/api/papers",   tags=["Papers"])
app.include_router(chat.router,     prefix="/api/chat",     tags=["Chat"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["Pipeline"])
app.include_router(stats.router,    prefix="/api/stats",    tags=["Stats"])
app.include_router(hitl.router,     prefix="/api/hitl",     tags=["HITL"])


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "version": "2.0.0"}


# ── WebSocket real-time chat ──────────────────────────────────────────────────
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            # stream tokens back
            async for token in chat_service.stream(
                content   = data.get("content", ""),
                paper_id  = data.get("paper_id"),
                context   = data.get("context", []),
            ):
                await manager.send(websocket, {"type": "token", "content": token})
            await manager.send(websocket, {"type": "done"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── Pipeline progress stream ──────────────────────────────────────────────────
@app.websocket("/ws/pipeline")
async def websocket_pipeline(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()       # wait for "start" signal
            from app.services.pipeline_service import PipelineService
            async for update in PipelineService().run_stream():
                await manager.send(websocket, update)
    except WebSocketDisconnect:
        manager.disconnect(websocket)