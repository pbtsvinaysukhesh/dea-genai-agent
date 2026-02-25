"""Papers Router"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.data_service import DataService

router = APIRouter()
ds = DataService()

@router.get("/")
async def list_papers(limit:int=50, offset:int=0,
                      platform:Optional[str]=None, min_score:int=0,
                      search:Optional[str]=None):
    papers = ds.get_papers(limit, offset, platform, min_score, search)
    return {"papers": papers, "total": len(papers)}

@router.get("/top")
async def top_papers(n:int=6):
    p = ds.get_papers(limit=n, min_score=60)
    p.sort(key=lambda x:x.get("relevance_score",0), reverse=True)
    return {"papers": p[:n]}

@router.get("/{pid}")
async def get_paper(pid:str):
    p = ds.get_paper_by_id(pid)
    if not p: raise HTTPException(404, "Not found")
    return p

@router.put("/{pid}")
async def update_paper(pid:str, updates:dict):
    p = ds.update_paper(pid, updates)
    if not p: raise HTTPException(404, "Not found")
    return {"status":"updated","paper":p}

@router.delete("/{pid}")
async def delete_paper(pid:str):
    if not ds.delete_paper(pid): raise HTTPException(404, "Not found")
    return {"status":"deleted"}