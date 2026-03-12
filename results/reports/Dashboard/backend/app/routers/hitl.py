"""
hitl.py router — reads/approves/rejects from the REAL
data/hitl_review/ folder that src/hitl_validator.py writes to.

HITLValidator.__init__ creates:
  data/hitl_review/pending/
  data/hitl_review/approved/
  data/hitl_review/rejected/

This router reads those same folders.
"""

import os, sys, json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# ── Resolve project root (same logic as data_service and pipeline_service) ──
_HERE         = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Exact folder HITLValidator uses (hitl_validator.py line 24: review_dir="data/hitl_review")
HITL_BASE = os.path.join(_PROJECT_ROOT, "data", "hitl_review")

router = APIRouter()


def _list_folder(folder: str) -> list:
    path = os.path.join(HITL_BASE, folder)
    if not os.path.exists(path):
        return []
    items = []
    for fname in os.listdir(path):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(path, fname), encoding="utf-8") as f:
                    items.append(json.load(f))
            except Exception:
                pass
    return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)


@router.get("/pending")
async def get_pending():
    reviews = _list_folder("pending")
    return {"reviews": reviews, "count": len(reviews)}


@router.get("/approved")
async def get_approved():
    reviews = _list_folder("approved")
    return {"reviews": reviews, "count": len(reviews)}


@router.get("/rejected")
async def get_rejected():
    reviews = _list_folder("rejected")
    return {"reviews": reviews, "count": len(reviews)}


class ReviewAction(BaseModel):
    review_id: str
    notes: Optional[str] = ""


@router.post("/approve")
async def approve(body: ReviewAction):
    """
    Mirrors HITLValidator.approve_review(review_id, notes)
    from hitl_validator.py
    """
    src = os.path.join(HITL_BASE, "pending",  f"{body.review_id}.json")
    dst = os.path.join(HITL_BASE, "approved", f"{body.review_id}.json")

    if not os.path.exists(src):
        raise HTTPException(404, f"Review {body.review_id} not found in pending/")

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    data["human_review"] = {"status": "approved", "notes": body.notes}

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    os.remove(src)
    return {"status": "approved", "review_id": body.review_id}


@router.post("/reject")
async def reject(body: ReviewAction):
    """
    Mirrors HITLValidator.reject_review(review_id, reason)
    from hitl_validator.py
    """
    src = os.path.join(HITL_BASE, "pending",  f"{body.review_id}.json")
    dst = os.path.join(HITL_BASE, "rejected", f"{body.review_id}.json")

    if not os.path.exists(src):
        raise HTTPException(404, f"Review {body.review_id} not found in pending/")

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    data["human_review"] = {"status": "rejected", "reason": body.notes}

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    os.remove(src)
    return {"status": "rejected", "review_id": body.review_id}