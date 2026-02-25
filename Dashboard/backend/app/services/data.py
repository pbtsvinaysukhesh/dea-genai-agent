"""
data_service.py — reads from the REAL data/history.json
that src/history.py (HistoryManager) writes to.

HOW THE PATH IS RESOLVED:
  This file lives at:
    your-project/dashboard/backend/app/services/data_service.py
  Walking up 5 levels gives:
    your-project/                 ← _PROJECT_ROOT
  So history.json is at:
    your-project/data/history.json  ← same file HistoryManager writes
"""

import os, sys, json, hashlib, logging
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Find project root (5 levels up from this file) ───────────────────────────
#
#   your-project/                           level 5 = _PROJECT_ROOT
#   └── dashboard/                          level 4
#       └── backend/                        level 3
#           └── app/                        level 2
#               └── services/               level 1 = _HERE
#                   └── data_service.py     (this file)
#
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", ".."))

# Add project root to path so  `from src.history import HistoryManager`  works
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ── Exact same paths that src/history.py and src/email_and_archive.py use ───
HISTORY_FILE = os.path.join(_PROJECT_ROOT, "data", "history.json")
RESULTS_DIR  = os.path.join(_PROJECT_ROOT, "results", "daily")

logger.info(f"[DataService] project root = {_PROJECT_ROOT}")
logger.info(f"[DataService] history file = {HISTORY_FILE}")


class DataService:

    def _load(self) -> List[Dict]:
        papers = []

        # ── Primary source: data/history.json ──────────────────────────
        # Written by: src/history.py → HistoryManager.save_insights()
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, encoding="utf-8") as f:
                    papers = json.load(f)
                logger.debug(f"[DataService] loaded {len(papers)} from history.json")
            except Exception as e:
                logger.error(f"[DataService] failed to read history.json: {e}")
                papers = []

        # ── Secondary source: results/daily/*.json ─────────────────────
        # Written by: src/email_and_archive.py → ResultsArchiver.archive_session_results()
        # We merge any papers not already in history
        if os.path.exists(RESULTS_DIR):
            for fname in sorted(os.listdir(RESULTS_DIR), reverse=True)[:10]:
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(RESULTS_DIR, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        data = json.load(f)
                    for p in data.get("papers", []):
                        if not any(x.get("title") == p.get("title") for x in papers):
                            papers.append(p)
                except Exception as e:
                    logger.warning(f"[DataService] could not read {fname}: {e}")

        # Assign stable _id to every paper (MD5 of title)
        for p in papers:
            if "_id" not in p:
                p["_id"] = hashlib.md5(
                    p.get("title", "").encode()
                ).hexdigest()[:12]

        return papers

    def _save(self, papers: List[Dict]):
        """Write back to data/history.json — same file HistoryManager uses."""
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def get_papers(self, limit=50, offset=0,
                   platform=None, min_score=0, search=None) -> List[Dict]:
        p = self._load()
        if platform:
            p = [x for x in p if x.get("platform", "").lower() == platform.lower()]
        if min_score:
            p = [x for x in p if x.get("relevance_score", 0) >= min_score]
        if search:
            q = search.lower()
            p = [x for x in p
                 if q in x.get("title", "").lower()
                 or q in x.get("memory_insight", "").lower()
                 or q in x.get("engineering_takeaway", "").lower()]
        p.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return p[offset: offset + limit]

    def get_paper_by_id(self, pid: str) -> Optional[Dict]:
        return next((p for p in self._load() if p.get("_id") == pid), None)

    def update_paper(self, pid: str, updates: dict) -> Optional[Dict]:
        """
        Called when the chat AI edits a paper field.
        Writes back to data/history.json.
        """
        papers = self._load()
        for i, p in enumerate(papers):
            if p.get("_id") == pid:
                papers[i].update(updates)
                papers[i]["updated_at"] = datetime.now().isoformat()
                self._save(papers)
                return papers[i]
        return None

    def delete_paper(self, pid: str) -> bool:
        papers = self._load()
        new = [p for p in papers if p.get("_id") != pid]
        if len(new) < len(papers):
            self._save(new)
            return True
        return False

    def get_statistics(self) -> Dict:
        papers = self._load()
        if not papers:
            return {"total": 0, "avg_score": 0, "platforms": {},
                    "impacts": {}, "top_score": 0}
        platforms, impacts = {}, {}
        for p in papers:
            pl = p.get("platform", "Unknown")
            im = p.get("dram_impact", "Unknown")
            platforms[pl] = platforms.get(pl, 0) + 1
            impacts[im]   = impacts.get(im, 0) + 1
        return {
            "total":     len(papers),
            "avg_score": round(
                sum(p.get("relevance_score", 0) for p in papers) / len(papers), 1),
            "platforms": platforms,
            "impacts":   impacts,
            "top_score": max(p.get("relevance_score", 0) for p in papers),
        }