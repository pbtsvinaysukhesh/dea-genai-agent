"""
pipeline_service.py — calls the REAL src/ pipeline, step by step.

HOW IT LINKS TO THE EXISTING CODEBASE:
  It does exactly what main.py's run_ultimate_agi() does,
  but broken into async steps so the browser sees live progress.

  Every function called here is the SAME function main.py calls:
    main.py line 125: fetch_articles_deep(config, use_playwright=True)
    main.py line 131: Collector().fetch_all(config)
    main.py line 152: VectorStoreManager(enabled=...)
    main.py line 168: HybridAGISystem(...)
    main.py line 220: agi.analyze_paper(article, recent_findings)
    main.py line 228: hitl.validate_paper(article, analysis)
    main.py line 289: archiver.archive_session_results(...)
    main.py line 301: email_tracker.filter_unsent_papers(new_findings)
    main.py line 307: formatter.build_html(unsent_papers)
    main.py line 313: mailer.send(html_report)
    main.py line 317: email_tracker.mark_as_sent(unsent_papers)
"""

import os, sys, json, asyncio, logging
from typing import AsyncGenerator
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── Resolve project root so `from src.xxx import` works ──────────────────────
#
#   your-project/                           ← _PROJECT_ROOT
#   └── dashboard/
#       └── backend/
#           └── app/
#               └── services/
#                   └── pipeline_service.py  (this file)
#
_HERE         = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", ".."))

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

logger.info(f"[PipelineService] project root = {_PROJECT_ROOT}")

# In-memory status — also read by GET /api/pipeline/status
_status = {
    "running":    False,
    "progress":   0,
    "message":    "Idle",
    "started_at": None,
    "session_id": None,
    "stats":      {},
}


class PipelineService:
    """
    Mirrors run_ultimate_agi() from main.py but streams progress to the browser.
    Each _stage_*() method calls the exact same src/ function main.py calls.
    """

    async def run_stream(self) -> AsyncGenerator[dict, None]:
        global _status

        if _status["running"]:
            yield {"type": "error", "message": "Pipeline already running"}
            return

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        _status.update({
            "running":    True,
            "progress":   0,
            "message":    "Starting…",
            "started_at": datetime.now().isoformat(),
            "session_id": session_id,
            "stats":      {},
        })

        try:
            # ── Stage 1: config ───────────────────────────────────────────
            # main.py line 83: config = load_config()
            yield self._prog(5, "📂 Loading config/config.yaml…")
            config    = await asyncio.to_thread(self._load_config)
            threshold = config["system"]["relevance_threshold"]
            use_pw    = config["system"].get("use_playwright", True)
            use_crew  = config.get("features", {}).get("use_crewai", True)
            use_vecs  = config["system"].get("use_vectors", True)
            yield self._prog(8, f"✅ Config loaded (threshold={threshold}, playwright={use_pw})")

            # ── Stage 2: collect ──────────────────────────────────────────
            # main.py lines 125–139: fetch_articles_deep OR Collector().fetch_all()
            yield self._prog(10, "📡 Collecting articles (arXiv + RSS)…")
            articles = await asyncio.to_thread(self._collect, config, use_pw)
            yield self._prog(22, f"✅ Collected {len(articles)} articles")

            if not articles:
                yield self._prog(100, "⚠️ No articles collected — check config sources")
                _status["running"] = False
                return

            # ── Stage 3: vector store ─────────────────────────────────────
            # main.py line 152: VectorStoreManager(enabled=...)
            yield self._prog(25, "🧠 Initialising Qdrant Vector Store…")
            vm = await asyncio.to_thread(self._init_vectors, use_vecs)
            yield self._prog(30, "✅ Vector Store ready")

            # ── Stage 4: load history ─────────────────────────────────────
            # main.py lines 45–59: load_recent_findings(days=7)
            yield self._prog(33, "📚 Loading recent findings (last 7 days)…")
            recent = await asyncio.to_thread(self._load_recent)
            yield self._prog(37, f"✅ {len(recent)} historical papers loaded")

            # ── Stage 5: AGI analysis + HITL ─────────────────────────────
            # main.py lines 168–256: HybridAGISystem + agi.analyze_paper + hitl.validate_paper
            yield self._prog(40, f"⚖️  AGI analysis + HITL (threshold ≥ {threshold})…")
            findings, rejected = await asyncio.to_thread(
                self._run_analysis, articles, recent, vm, config, use_crew, threshold
            )
            yield self._prog(72,
                f"✅ Analysis done — {len(findings)} new · "
                f"{rejected['duplicate']} duplicates · "
                f"{rejected['hitl_pending']} pending HITL"
            )

            if not findings:
                yield {"type": "complete", "progress": 100,
                       "message": "No new findings above threshold",
                       "stats": {"total": len(articles), **rejected}}
                _status.update({"running": False, "progress": 100,
                                "message": "Done (no new findings)", "stats": rejected})
                return

            # ── Stage 6: save to history ──────────────────────────────────
            # main.py line 270: history.save_insights(new_findings)
            yield self._prog(76, "💾 Saving to data/history.json…")
            await asyncio.to_thread(self._save_history, findings)
            yield self._prog(80, f"✅ Saved {len(findings)} papers to history")

            # ── Stage 7: archive ──────────────────────────────────────────
            # main.py lines 289–296: archiver.archive_session_results(...)
            yield self._prog(83, "💾 Archiving full session results…")
            archive_path = await asyncio.to_thread(
                self._archive, findings, session_id,
                {"rejected": rejected,
                 "vector_stats": vm.get_stats() if hasattr(vm, "get_stats") else {}}
            )
            yield self._prog(88, f"✅ Archived → {archive_path}")

            # ── Stage 8: email ─────────────────────────────────────────────
            # main.py lines 301–329: email_tracker.filter + formatter.build_html + mailer.send
            yield self._prog(90, "📧 Smart email (new papers only, no re-sends)…")
            email_msg = await asyncio.to_thread(
                self._send_email, findings, config, session_id
            )
            yield self._prog(97, f"✅ {email_msg}")

            # ── Done ───────────────────────────────────────────────────────
            stats = {
                "total_collected": len(articles),
                "new_findings":    len(findings),
                **rejected,
            }
            _status.update({"running": False, "progress": 100,
                            "message": "Complete!", "stats": stats})
            yield {"type": "complete", "progress": 100,
                   "message": f"Done — {len(findings)} new papers found",
                   "stats":   stats}

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            _status.update({"running": False,
                            "message": f"Error: {e}", "progress": 0})
            yield {"type": "error", "message": str(e)}

    # ── Stage helpers — each mirrors the exact main.py call ──────────────────

    def _prog(self, pct: int, msg: str) -> dict:
        _status["progress"] = pct
        _status["message"]  = msg
        return {"type": "progress", "progress": pct, "message": msg}

    def _load_config(self) -> dict:
        """main.py line 83: config = load_config()"""
        import yaml
        path = os.path.join(_PROJECT_ROOT, "config", "config.yaml")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _collect(self, config: dict, use_playwright: bool) -> list:
        """main.py lines 125–139"""
        if use_playwright:
            try:
                from src.deep_scraper import fetch_articles_deep
                return fetch_articles_deep(config, use_playwright=True)
            except Exception as e:
                logger.warning(f"Playwright failed ({e}), falling back")

        from src.collector import Collector, deduplicate_articles
        articles = Collector().fetch_all(config)
        return deduplicate_articles(articles)

    def _init_vectors(self, use_vectors: bool):
        """main.py line 152"""
        from src.qdrant_vector_store import VectorStoreManager
        return VectorStoreManager(enabled=use_vectors)

    def _load_recent(self) -> list:
        """main.py lines 45–59: load_recent_findings(days=7)"""
        from src.history import HistoryManager
        hm = HistoryManager()
        try:
            with open(hm.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cutoff = datetime.now() - timedelta(days=7)
            return [
                d for d in data
                if "date" in d
                and datetime.fromisoformat(d["date"]) > cutoff
            ]
        except Exception:
            return []

    def _run_analysis(self, articles, recent, vm, config,
                      use_crew, threshold) -> tuple:
        """
        main.py lines 168–256:
          HybridAGISystem → agi.analyze_paper → hitl.validate_paper
        """
        from src.crewai_agents import HybridAGISystem
        from src.hitl_validator import HITLValidator

        # Same args as main.py line 168
        agi = HybridAGISystem(
            use_crewai=use_crew,
            use_playwright=False,   # scraping already done
            use_council=True
        )
        # Same args as main.py line 102
        hitl = HITLValidator(
            auto_approve_threshold=0.85,
            require_review_score=90
        )

        findings = []
        rejected = {"duplicate": 0, "low_score": 0, "failed": 0, "hitl_pending": 0}

        for article in articles:
            title = str(article.get("title", ""))

            # main.py line 196: vector duplicate check
            ok, reason = vm.check_and_add(article)
            if not ok:
                rejected["duplicate"] += 1
                continue

            # main.py lines 210–215: title history duplicate
            try:
                if any(title.lower() == str(p.get("title","")).lower()
                       for p in recent):
                    rejected["duplicate"] += 1
                    continue
            except Exception:
                pass

            # main.py line 220: analyze_paper
            analysis = agi.analyze_paper(article, recent)
            if not analysis:
                rejected["failed"] += 1
                continue

            # main.py line 228: hitl.validate_paper
            hitl_status, hitl_reason, validated = hitl.validate_paper(article, analysis)
            if hitl_status == "needs_review":
                rejected["hitl_pending"] += 1
                continue

            score = validated.get("relevance_score", 0)
            if score >= threshold:
                findings.append({**article, **validated})
            else:
                rejected["low_score"] += 1

        return findings, rejected

    def _save_history(self, findings: list):
        """main.py line 270: history.save_insights(new_findings)"""
        from src.history import HistoryManager
        HistoryManager().save_insights(findings)

    def _archive(self, findings: list, session_id: str, extra: dict) -> str:
        """main.py lines 289–296: archiver.archive_session_results(...)"""
        from src.email_and_archive import ResultsArchiver
        return ResultsArchiver().archive_session_results(
            findings,
            {"total_analyzed": len(findings), **extra},
            session_id
        )

    def _send_email(self, findings: list, config: dict, session_id: str) -> str:
        """main.py lines 301–329"""
        from src.email_and_archive import EmailTracker
        from src.formatter import ReportFormatter
        from src.mailer import Mailer

        tracker = EmailTracker()
        unsent  = tracker.filter_unsent_papers(findings)  # line 301

        if not unsent:
            return "No new papers to email (all already sent)"

        html = ReportFormatter().build_html(unsent)        # line 307

        try:
            mailer = Mailer(config.get("email", {}))       # line 114
            if mailer.send(html):                          # line 313
                tracker.mark_as_sent(unsent)              # line 317
                return f"Sent {len(unsent)} papers"
            return "Email failed — check SMTP credentials"
        except Exception as e:
            logger.warning(f"Email error: {e}")

        # Fallback: save report locally (main.py lines 324–328)
        reports_dir = os.path.join(_PROJECT_ROOT, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        path = os.path.join(reports_dir, f"report_{session_id}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        tracker.mark_as_sent(unsent)
        return f"Email unavailable — saved locally → reports/report_{session_id}.html"

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def get_status() -> dict:
        return _status

    @staticmethod
    def stop():
        _status.update({
            "running":  False,
            "message":  "Stopped by user",
            "progress": 0,
        })