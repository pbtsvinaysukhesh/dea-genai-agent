"""HITL Router"""
import os, json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
BASE = "data/hitl_review"

def _list(folder):
    path = f"{BASE}/{folder}"
    if not os.path.exists(path): return []
    items = []
    for f in os.listdir(path):
        if f.endswith(".json"):
            try:
                with open(f"{path}/{f}", encoding="utf-8") as fp:
                    items.append(json.load(fp))
            except: pass
    return sorted(items, key=lambda x: x.get("created_at",""), reverse=True)

@router.get("/pending")
async def pending(): return {"reviews": _list("pending"), "count": len(_list("pending"))}

@router.get("/approved")
async def approved(): return {"reviews": _list("approved"), "count": len(_list("approved"))}

class ReviewAction(BaseModel):
    review_id: str
    notes: Optional[str] = ""

@router.post("/approve")
async def approve(body: ReviewAction):
    src = f"{BASE}/pending/{body.review_id}.json"
    dst = f"{BASE}/approved/{body.review_id}.json"
    if not os.path.exists(src): raise HTTPException(404, "Review not found")
    with open(src, encoding="utf-8") as f: data = json.load(f)
    data["human_review"] = {"status":"approved","notes":body.notes}
    with open(dst,"w",encoding="utf-8") as f: json.dump(data, f, indent=2)
    os.remove(src)
    return {"status":"approved"}

@router.post("/reject")
async def reject(body: ReviewAction):
    src = f"{BASE}/pending/{body.review_id}.json"
    dst = f"{BASE}/rejected/{body.review_id}.json"
    if not os.path.exists(src): raise HTTPException(404, "Review not found")
    with open(src, encoding="utf-8") as f: data = json.load(f)
    data["human_review"] = {"status":"rejected","reason":body.notes}
    with open(dst,"w",encoding="utf-8") as f: json.dump(data, f, indent=2)
    os.remove(src)
    return {"status":"rejected"}