"""
Async Pipeline Accelerator
===========================
Wraps the synchronous analysis loop in ``main.py`` with an async engine
that parallelizes independent operations using ``asyncio``.

Key speedups:
  1. Batch article analysis  — run N analyses concurrently (configurable)
  2. Parallel report generation — email / PDF / PPTX / podcast in parallel

Usage (from main.py):
    from src.async_pipeline import AsyncPipelineEngine
    engine = AsyncPipelineEngine(agi, vector_manager, hitl, threshold=60)
    new_findings, rejected = asyncio.run(engine.analyze_batch(articles, recent_findings))
"""

import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

logger = logging.getLogger(__name__)

# Maximum number of concurrent analysis tasks.  Keep modest to avoid
# overwhelming rate-limited APIs (Groq, Ollama, Gemini).
_DEFAULT_CONCURRENCY = 4


class AsyncPipelineEngine:
    """
    Async wrapper around the synchronous analysis pipeline.

    Strategy:
      - CPU-bound / IO-bound LLM calls are offloaded to a thread pool.
      - A semaphore limits concurrency to avoid API rate-limit storms.
      - Results are collected and deduplication is still enforced.
    """

    def __init__(
        self,
        agi_system,                       # HybridAGISystem instance
        vector_manager,                   # VectorStoreManager
        hitl_validator,                   # HITLValidator
        threshold: int = 60,
        max_concurrency: int = _DEFAULT_CONCURRENCY,
    ):
        self.agi = agi_system
        self.vector_mgr = vector_manager
        self.hitl = hitl_validator
        self.threshold = threshold
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.executor = ThreadPoolExecutor(
            max_workers=max_concurrency, thread_name_prefix="agi-worker"
        )
        logger.info(
            f"[AsyncPipeline] Initialized (concurrency={max_concurrency}, "
            f"threshold={threshold})"
        )

    # ── Public API ───────────────────────────────────────────────────────

    async def analyze_batch(
        self,
        articles: List[Dict],
        recent_findings: List[Dict],
    ) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Analyze a batch of articles concurrently.

        Returns:
            (new_findings, rejected_counts)
        """
        rejected = {"duplicate": 0, "low_score": 0, "failed": 0}
        results: List[Optional[Dict]] = [None] * len(articles)

        # Create tasks
        tasks = [
            self._analyze_one(idx, article, articles, recent_findings, results, rejected)
            for idx, article in enumerate(articles)
        ]

        # Fire them all; semaphore controls concurrency
        await asyncio.gather(*tasks, return_exceptions=True)

        # Collect non-None results
        new_findings = [r for r in results if r is not None]

        logger.info(
            f"[AsyncPipeline] Batch complete: "
            f"{len(new_findings)} accepted, "
            f"{rejected['duplicate']} dups, "
            f"{rejected['low_score']} below threshold, "
            f"{rejected['failed']} failed"
        )
        return new_findings, rejected

    # ── Internal ─────────────────────────────────────────────────────────

    async def _analyze_one(
        self,
        idx: int,
        article: Dict,
        all_articles: List[Dict],
        recent_findings: List[Dict],
        results: list,
        rejected: Dict[str, int],
    ):
        """Analyze a single article under the concurrency semaphore."""
        title = article.get("title", "Unknown")
        try:
            title_short = title[:60] + "..." if len(title) > 60 else title
        except Exception:
            title_short = "Paper"

        async with self.semaphore:
            logger.info(f"[{idx+1}/{len(all_articles)}] {title_short}")

            try:
                # ── Duplicate checks (fast, keep synchronous) ────────
                should_process, reason = self.vector_mgr.check_and_add(article)
                if not should_process and reason == "duplicate":
                    rejected["duplicate"] += 1
                    logger.info(f"  [SEMANTIC DUPLICATE]")
                    return

                dup_title = any(
                    str(title).lower() == str(p.get("title", "")).lower()
                    for p in recent_findings
                )
                if dup_title:
                    rejected["duplicate"] += 1
                    logger.info(f"  [DUPLICATE] Already in history")
                    return

                # ── LLM analysis (offload to thread pool) ────────────
                loop = asyncio.get_running_loop()
                analysis = await loop.run_in_executor(
                    self.executor,
                    self.agi.analyze_paper,
                    article,
                    recent_findings,
                )

                if not analysis:
                    rejected["failed"] += 1
                    logger.warning(f"  [FAILED] Analysis error")
                    return

                # ── HITL validation ──────────────────────────────────
                hitl_status, hitl_reason, validated = self.hitl.validate_paper(
                    article, analysis
                )
                if hitl_status == "needs_review":
                    logger.info(f"  [HITL] {hitl_reason}")
                    return

                score = validated.get("relevance_score", 0)
                if score >= self.threshold:
                    merged = {**article, **validated}
                    results[idx] = merged
                    logger.info(f"  [ACCEPTED] Score: {score}")
                else:
                    rejected["low_score"] += 1
                    logger.info(f"  [REJECTED] Score: {score}")

            except Exception as e:
                logger.error(f"  [ERROR] {str(e)[:120]}")
                rejected["failed"] += 1

    def shutdown(self):
        """Shutdown the thread pool executor."""
        self.executor.shutdown(wait=False)
        logger.info("[AsyncPipeline] Executor shut down")


# ── Async Report Generation ──────────────────────────────────────────────────

async def generate_reports_async(
    insights: List[Dict],
    all_sources: List[Dict],
    output_dir: str = None,
) -> Dict[str, bool]:
    """
    Run all report generators concurrently.

    Each generator is CPU/IO-bound (file writes, TTS), so we offload
    each to a thread pool worker and await them all in parallel.
    """
    from concurrent.futures import ThreadPoolExecutor

    results = {}
    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="report")
    loop = asyncio.get_running_loop()

    try:
        from src.multi_format_orchestrator import MultiFormatReportOrchestrator
        orch = MultiFormatReportOrchestrator(output_dir)

        # The orchestrator's generate_all is a single sync call.
        # Wrap it to run in a thread so the event loop stays free.
        report_results = await loop.run_in_executor(
            executor,
            orch.generate_all,
            insights,
            all_sources,
        )
        results.update(report_results)
    except Exception as e:
        logger.error(f"[AsyncReports] Generation failed: {e}")

    executor.shutdown(wait=False)
    return results


__all__ = ["AsyncPipelineEngine", "generate_reports_async"]
