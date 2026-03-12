"""
DEA Flexible Pipeline Orchestrator
====================================
Config-driven pipeline for PPT, PDF, and Podcast generation.
Replaces hardcoded orchestration in multi_format_orchestrator.py.

Design principles
-----------------
* Every behavioral parameter flows from dea_config.get_config().
* Each format is an independently togglable pipeline stage.
* Reproducibility: config hash + run_id stamped on every output.
* Tracing: per-stage timing, success/failure, and output paths logged.
* Graceful degradation: missing optional deps skip stages, not crash.

Config mapping
--------------
  Enabled formats      →  pipeline.enabled_formats
  Output directory     →  paths.output_dir
  Backup on run        →  pipeline.backup_on_run
  Max paper slides     →  pipeline.max_paper_slides
  Narration mode       →  podcast.narration_mode
  Config snapshots     →  tracing.config_snapshot_dir
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dea_config import get_config, snapshot_config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE RESULT
# ─────────────────────────────────────────────────────────────────────────────

class StageResult:
    def __init__(
        self,
        stage:    str,
        success:  bool,
        outputs:  Dict[str, Optional[Path]] = None,
        duration_ms: int = 0,
        error:    str = "",
    ):
        self.stage       = stage
        self.success     = success
        self.outputs     = outputs or {}
        self.duration_ms = duration_ms
        self.error       = error

    def to_dict(self) -> Dict:
        return {
            "stage":       self.stage,
            "success":     self.success,
            "outputs":     {k: str(v) if v else None for k, v in self.outputs.items()},
            "duration_ms": self.duration_ms,
            "error":       self.error,
        }


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE STAGES  —  one function per format
# ─────────────────────────────────────────────────────────────────────────────

def _stage_email(insights: List[Dict], cfg: Dict, out: Path) -> StageResult:
    t0 = time.perf_counter()
    try:
        from enhanced_formatter import EnhancedReportFormatter
        formatter = EnhancedReportFormatter()
        html = formatter.build_html(insights)
        path = out / "email_report.html"
        path.write_text(html, encoding="utf-8")
        return StageResult("email", True, {"html": path}, _ms(t0))
    except ImportError:
        return StageResult("email", False, {}, _ms(t0), "enhanced_formatter not available")
    except Exception as e:
        return StageResult("email", False, {}, _ms(t0), str(e))


def _stage_pdf(insights: List[Dict], cfg: Dict, out: Path) -> StageResult:
    t0 = time.perf_counter()
    pdf_path = out / "report.pdf"
    try:
        from pdf_generator import PDFReportGenerator
        gen = PDFReportGenerator(output_path=str(pdf_path))
        ok  = gen.generate(insights)
        return StageResult("pdf", ok, {"pdf": pdf_path if ok else None}, _ms(t0))
    except ImportError:
        return StageResult("pdf", False, {}, _ms(t0), "pdf_generator not available")
    except Exception as e:
        return StageResult("pdf", False, {}, _ms(t0), str(e))


def _stage_pptx(insights: List[Dict], cfg: Dict, out: Path) -> StageResult:
    t0 = time.perf_counter()
    pptx_path = out / "report.pptx"
    try:
        from pptx_generator import PowerPointGenerator
        gen = PowerPointGenerator(output_path=str(pptx_path))
        ok  = gen.generate(insights)
        return StageResult("pptx", ok, {"pptx": pptx_path if ok else None}, _ms(t0))
    except ImportError:
        return StageResult("pptx", False, {}, _ms(t0), "pptx_generator not available")
    except Exception as e:
        return StageResult("pptx", False, {}, _ms(t0), str(e))


def _stage_podcast(insights: List[Dict], cfg: Dict, run_id: str) -> StageResult:
    t0 = time.perf_counter()
    try:
        from agi_podcast_generator import AGIPodcastGenerator
        gen    = AGIPodcastGenerator()  # uses resolved cfg internally
        result = gen.generate(insights, run_id=run_id)
        success = bool(result.get("mp3") or result.get("transcript"))
        return StageResult(
            "podcast", success,
            {
                "mp3":        result.get("mp3"),
                "wav":        result.get("wav"),
                "transcript": result.get("transcript"),
            },
            _ms(t0),
        )
    except ImportError:
        return StageResult("podcast", False, {}, _ms(t0), "agi_podcast_generator not available")
    except Exception as e:
        return StageResult("podcast", False, {}, _ms(t0), str(e))


def _stage_transcript(insights: List[Dict], cfg: Dict, out: Path, run_id: str) -> StageResult:
    """Standalone transcript stage (if podcast skipped but transcript still wanted)."""
    t0 = time.perf_counter()
    try:
        from agi_podcast_generator import AGIPodcastGenerator
        gen  = AGIPodcastGenerator()
        path = gen._agi._save_transcript(  # type: ignore[attr-defined]
            gen._agi._build_full_dialog(insights),
            run_id=run_id,
        ) if hasattr(gen, "_agi") else None
        return StageResult("transcript", path is not None, {"txt": path}, _ms(t0))
    except Exception as e:
        return StageResult("transcript", False, {}, _ms(t0), str(e))


def _stage_summary(insights: List[Dict], cfg: Dict, out: Path) -> StageResult:
    t0 = time.perf_counter()
    try:
        import json
        total     = len(insights)
        avg_score = sum(i.get("relevance_score", 0) for i in insights) / total if total else 0

        summary = {
            "generated_at":   datetime.utcnow().isoformat() + "Z",
            "config_hash":    cfg.get("_meta", {}).get("config_hash", ""),
            "total_papers":   total,
            "avg_relevance":  round(avg_score, 2),
            "top_papers": [
                {
                    "title":   p.get("title"),
                    "score":   p.get("relevance_score"),
                    "platform": p.get("platform"),
                    "link":    p.get("link"),
                }
                for p in sorted(insights, key=lambda x: x.get("relevance_score", 0), reverse=True)[:10]
            ],
        }

        json_path = out / "summary.json"
        txt_path  = out / "summary.txt"
        json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        txt_path.write_text(
            f"DEA Summary — {summary['generated_at']}\n"
            f"Papers: {total}  |  Avg relevance: {avg_score:.1f}\n"
            f"Config: {summary['config_hash']}\n",
            encoding="utf-8",
        )
        return StageResult("summary", True, {"json": json_path, "txt": txt_path}, _ms(t0))
    except Exception as e:
        return StageResult("summary", False, {}, _ms(t0), str(e))


def _stage_backup(out: Path, cfg: Dict) -> StageResult:
    t0 = time.perf_counter()
    try:
        from backup_manager import BackupManager
        backup_dir = Path(cfg["paths"]["backup_dir"])
        mgr = BackupManager(backup_dir)
        files = {
            "pdf":  out / "report.pdf",
            "pptx": out / "report.pptx",
        }
        results = mgr.backup_and_version(files)
        backed  = sum(1 for v in results.values() if v)
        return StageResult("backup", True, {}, _ms(t0),
                           f"Backed up {backed} files")
    except ImportError:
        return StageResult("backup", False, {}, _ms(t0), "backup_manager not available")
    except Exception as e:
        return StageResult("backup", False, {}, _ms(t0), str(e))


# Stage registry — format name → callable(insights, cfg, ...) → StageResult
# Stages that require extra args (run_id, out) are handled in run_pipeline.
_STAGE_MAP = {
    "email":      _stage_email,
    "pdf":        _stage_pdf,
    "pptx":       _stage_pptx,
    "podcast":    _stage_podcast,
    "transcript": _stage_transcript,
    "summary":    _stage_summary,
}


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(
    insights:         List[Dict],
    config_overrides: Optional[Dict] = None,
    run_id:           Optional[str]  = None,
    formats:          Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Execute the DEA generation pipeline for the requested formats.

    Args:
        insights:         List of paper/insight dicts from RAG/collection pipeline.
        config_overrides: Runtime overrides applied on top of dea_config defaults.
                          Supports dot-path keys: {"podcast.narration_mode": "agi"}.
        run_id:           Unique run identifier (used for filenames + config snapshot).
                          Defaults to current timestamp.
        formats:          List of format names to generate.
                          Defaults to pipeline.enabled_formats from config.
                          Valid values: email, pdf, pptx, podcast, transcript, summary

    Returns:
        {
          "run_id":       str,
          "config_hash":  str,
          "stages":       {format: StageResult.to_dict()},
          "overall":      bool,          # True if all requested stages succeeded
          "duration_ms":  int,
          "output_dir":   str,
        }

    Example:
        results = run_pipeline(
            insights,
            config_overrides={"podcast.narration_mode": "agi"},
            formats=["pdf", "podcast"],
        )
    """
    t_total = time.perf_counter()

    cfg    = get_config(config_overrides)
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    out    = Path(cfg["paths"]["output_dir"])
    out.mkdir(parents=True, exist_ok=True)

    config_hash = cfg["_meta"]["config_hash"]
    logger.info(
        f"[Pipeline] ▶ run={run_id}, hash={config_hash}, "
        f"papers={len(insights)}"
    )

    # Save config snapshot for reproducibility
    if cfg["tracing"].get("embed_config_hash"):
        snapshot_config(cfg, run_id)

    # Resolve which formats to run
    requested = formats or cfg["pipeline"].get("enabled_formats", list(_STAGE_MAP.keys()))

    # Backup before overwriting
    if cfg["pipeline"].get("backup_on_run") and "backup" not in requested:
        _stage_backup(out, cfg)

    # Execute stages
    stage_results: Dict[str, Dict] = {}
    for fmt in requested:
        if fmt not in _STAGE_MAP:
            logger.warning(f"[Pipeline] Unknown format '{fmt}' — skipping")
            continue

        logger.info(f"[Pipeline] ── {fmt.upper()} ─────────────────")
        fn = _STAGE_MAP[fmt]

        # Dispatch with appropriate signatures
        if fmt in ("podcast", "transcript"):
            result = fn(insights, cfg, run_id)
        else:
            result = fn(insights, cfg, out)

        stage_results[fmt] = result.to_dict()
        status = "✅" if result.success else "❌"
        logger.info(
            f"[Pipeline] {status} {fmt.upper()} — "
            f"{result.duration_ms}ms"
            + (f"  err={result.error}" if result.error and not result.success else "")
        )

    overall = all(r["success"] for r in stage_results.values())
    total_ms = _ms(t_total)

    logger.info(
        f"[Pipeline] ◼ Complete — "
        f"{sum(r['success'] for r in stage_results.values())}/{len(stage_results)} stages OK, "
        f"{total_ms}ms"
    )

    return {
        "run_id":      run_id,
        "config_hash": config_hash,
        "stages":      stage_results,
        "overall":     overall,
        "duration_ms": total_ms,
        "output_dir":  str(out),
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# CLI  —  python dea_pipeline.py --formats pdf pptx podcast
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")

    parser = argparse.ArgumentParser(description="DEA Flexible Pipeline")
    parser.add_argument(
        "--formats", nargs="+",
        default=["email", "pdf", "pptx", "podcast", "summary"],
        help="Formats to generate",
    )
    parser.add_argument(
        "--narration", default="agi",
        choices=["agi", "classic"],
        help="Podcast narration mode",
    )
    parser.add_argument(
        "--insights-json", default=None,
        help="Path to JSON file containing insights list (for testing)",
    )
    args = parser.parse_args()

    # Load test insights or use a stub
    if args.insights_json:
        with open(args.insights_json) as f:
            test_insights = json.load(f)
    else:
        test_insights = [
            {
                "title": "Efficient LLM Inference on Mobile",
                "relevance_score": 87,
                "platform": "Mobile",
                "model_type": "Transformer",
                "quantization_method": "INT4",
                "dram_impact": "High",
                "memory_insight": "4-bit quantization cuts peak DRAM by 60%",
                "engineering_takeaway": "Use INT4 with outlier-aware calibration",
                "source": "arXiv",
                "link": "https://arxiv.org/example",
            }
        ]

    result = run_pipeline(
        test_insights,
        config_overrides={"podcast.narration_mode": args.narration},
        formats=args.formats,
    )
    print(json.dumps(result, indent=2, default=str))
