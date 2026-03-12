"""
DEA Agent Configuration System
================================
Single source of truth for all DEA module parameters.
Eliminates hardcoded values across pptx_generator, pdf_generator,
podcast_generator, and multi_format_orchestrator.

Config hierarchy (highest to lowest priority):
  1. Runtime overrides passed directly to modules
  2. Environment variables (DEA_*)
  3. This file's DEA_CONFIG dict defaults

All config keys are documented with type, default, and env-var mapping.
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# MASTER CONFIG DICT
# Every hardcoded value in the codebase should trace back to an entry here.
# ─────────────────────────────────────────────────────────────────────────────

DEA_CONFIG: Dict[str, Any] = {

    # ── Identity & Branding ──────────────────────────────────────────────────
    "brand": {
        "podcast_name":     "Vinay DEA Podcast",          # env: DEA_PODCAST_NAME
        "host_name":        "Vinay",                       # env: DEA_HOST_NAME
        "report_title":     "On-Device AI Intelligence Report",  # env: DEA_REPORT_TITLE
        "organization":     "DEA Research",                # env: DEA_ORGANIZATION
    },

    # ── Paths ────────────────────────────────────────────────────────────────
    "paths": {
        "output_dir":       "results/reports",             # env: REPORT_OUTPUT_DIR
        "backup_dir":       "results/backup",              # env: BACKUP_DIR
        "podcast_dir":      "results/reports",             # env: PODCAST_DIR
        "intro_music":      None,                          # env: PODCAST_INTRO_MUSIC_PATH
        "outro_music":      None,                          # env: PODCAST_OUTRO_MUSIC_PATH
    },

    # ── Pipeline feature flags ───────────────────────────────────────────────
    "pipeline": {
        "enabled_formats":  ["email", "pdf", "pptx", "podcast", "transcript", "summary"],
        "generate_wav":     True,                          # env: DEA_GENERATE_WAV
        "audio_bitrate":    "192k",                        # env: DEA_AUDIO_BITRATE
        "max_paper_slides": 6,                             # env: DEA_MAX_PAPER_SLIDES
        "top_k_papers":     6,                             # env: DEA_TOP_K_PAPERS
        "backup_on_run":    True,                          # env: DEA_BACKUP_ON_RUN
    },

    # ── Podcast / Audio ──────────────────────────────────────────────────────
    "podcast": {
        "language":         "en",                          # env: DEA_PODCAST_LANG
        "greeting":         (                              # env: DEA_PODCAST_GREETING
            "Hello everyone, Good Evening and Good Morning! "
            "Welcome to the Vinay DEA Podcast."
        ),
        "tts_engine":       "auto",   # "google" | "gtts" | "auto"
        "silence_ms":       500,                           # pause between speakers
        "speaking_rate":    1.0,                           # Google TTS rate
        "narration_mode":   "agi",    # "classic" | "agi"  (env: DEA_NARRATION_MODE)
    },

    # ── AGI Narration voices ─────────────────────────────────────────────────
    # Each voice maps to a Google TTS Neural2 voice name + gender label.
    # Roles: Anchor, Analyst, Skeptic, Futurist, Questioner
    "voices": {
        "Anchor": {
            "google_voice":  "en-US-Neural2-D",
            "gender":        "MALE",
            "description":   "Authoritative host, sets context & transitions",
            "gtts_accent":   "en",
        },
        "Analyst": {
            "google_voice":  "en-US-Neural2-C",
            "gender":        "MALE",
            "description":   "Deep technical diver, explains mechanisms",
            "gtts_accent":   "en",
        },
        "Questioner": {
            "google_voice":  "en-US-Neural2-E",
            "gender":        "FEMALE",
            "description":   "Asks sharp follow-up questions, represents audience",
            "gtts_accent":   "en",
        },
        "Skeptic": {
            "google_voice":  "en-US-Neural2-A",
            "gender":        "MALE",
            "description":   "Challenges assumptions, surfaces counter-arguments",
            "gtts_accent":   "en-us",
        },
        "Futurist": {
            "google_voice":  "en-US-Neural2-F",
            "gender":        "FEMALE",
            "description":   "Extrapolates trends, connects to bigger picture",
            "gtts_accent":   "en-au",
        },
    },

    # ── AGI Segment configuration ────────────────────────────────────────────
    # Controls which segments appear and their speaking assignments.
    # Set enabled=False to skip a segment without removing it from the schema.
    "segments": {
        "intro":       {"enabled": True,  "voices": ["Anchor"],                      "max_papers": 0},
        "hook":        {"enabled": True,  "voices": ["Anchor", "Questioner"],         "max_papers": 0},
        "trends":      {"enabled": True,  "voices": ["Anchor", "Analyst"],            "max_papers": 0},
        "deep_dive":   {"enabled": True,  "voices": ["Analyst", "Questioner"],        "max_papers": 6},
        "debate":      {"enabled": True,  "voices": ["Analyst", "Skeptic"],           "max_papers": 3},
        "memory":      {"enabled": True,  "voices": ["Analyst", "Questioner"],        "max_papers": 0},
        "future":      {"enabled": True,  "voices": ["Futurist", "Anchor"],           "max_papers": 0},
        "qa":          {"enabled": True,  "voices": ["Questioner", "Analyst", "Anchor"], "max_papers": 0},
        "summary":     {"enabled": True,  "voices": ["Anchor"],                       "max_papers": 0},
        "outro":       {"enabled": True,  "voices": ["Anchor", "Questioner"],         "max_papers": 0},
    },

    # ── Presentation (PPT) ───────────────────────────────────────────────────
    "pptx": {
        "slide_width_in":   10,
        "slide_height_in":  7.5,
        "colors": {
            "primary":   (102, 126, 234),
            "secondary": (118, 75, 162),
            "heading":   (26,  32,  44),
            "text":      (45,  55,  72),
            "accent":    (237, 137, 54),
            "white":     (255, 255, 255),
        },
        "fonts": {
            "title":    "Calibri",
            "body":     "Calibri",
            "mono":     "Courier New",
        },
    },

    # ── PDF ──────────────────────────────────────────────────────────────────
    "pdf": {
        "page_size":         "A4",
        "margin_inches":     1.0,
        "font_body":         "Helvetica",
        "font_heading":      "Helvetica-Bold",
        "font_size_body":    11,
        "font_size_heading": 16,
    },

    # ── Personalization context ──────────────────────────────────────────────
    # Injected into AGI narration for context-aware commentary.
    "personalization": {
        "audience":         "AI engineers and product managers",
        "domain_focus":     "on-device AI, edge inference, DRAM optimization",
        "expertise_level":  "intermediate",   # beginner | intermediate | expert
        "tone":             "professional-conversational",
    },

    # ── Reproducibility & tracing ────────────────────────────────────────────
    "tracing": {
        "embed_config_hash":  True,   # Embed SHA256 of config in outputs
        "log_segment_timings": True,  # Log ms per segment
        "config_snapshot_dir": "results/config_snapshots",  # Save config per run
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG ACCESSOR  —  applies env-var overrides at access time
# ─────────────────────────────────────────────────────────────────────────────

# Mapping: env-var name → dot-path into DEA_CONFIG
_ENV_OVERRIDES = {
    "DEA_PODCAST_NAME":        "brand.podcast_name",
    "DEA_HOST_NAME":           "brand.host_name",
    "DEA_REPORT_TITLE":        "brand.report_title",
    "DEA_ORGANIZATION":        "brand.organization",
    "REPORT_OUTPUT_DIR":       "paths.output_dir",
    "BACKUP_DIR":              "paths.backup_dir",
    "PODCAST_DIR":             "paths.podcast_dir",
    "PODCAST_INTRO_MUSIC_PATH":"paths.intro_music",
    "PODCAST_OUTRO_MUSIC_PATH":"paths.outro_music",
    "DEA_GENERATE_WAV":        "pipeline.generate_wav",
    "DEA_AUDIO_BITRATE":       "pipeline.audio_bitrate",
    "DEA_MAX_PAPER_SLIDES":    "pipeline.max_paper_slides",
    "DEA_TOP_K_PAPERS":        "pipeline.top_k_papers",
    "DEA_BACKUP_ON_RUN":       "pipeline.backup_on_run",
    "DEA_PODCAST_LANG":        "podcast.language",
    "DEA_PODCAST_GREETING":    "podcast.greeting",
    "DEA_NARRATION_MODE":      "podcast.narration_mode",
}


def _set_nested(d: dict, dotpath: str, value: Any) -> None:
    """Set a value in a nested dict using dot notation."""
    keys = dotpath.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def _get_nested(d: dict, dotpath: str, default: Any = None) -> Any:
    """Get a value from a nested dict using dot notation."""
    keys = dotpath.split(".")
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def _coerce(value: str, original: Any) -> Any:
    """Coerce string env-var to match type of the config default."""
    if isinstance(original, bool):
        return value.lower() in ("1", "true", "yes")
    if isinstance(original, int):
        return int(value)
    if isinstance(original, float):
        return float(value)
    return value


def get_config(overrides: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Return a resolved copy of DEA_CONFIG with env-var and runtime overrides applied.

    Args:
        overrides: Optional flat or nested dict of runtime overrides.
                   Dot-paths are supported: {"podcast.greeting": "Hi!"}.

    Returns:
        Deep-merged config dict with full tracing metadata attached.

    Example:
        cfg = get_config({"podcast.narration_mode": "agi"})
        greeting = cfg["podcast"]["greeting"]
    """
    import copy
    import json
    import hashlib

    cfg = copy.deepcopy(DEA_CONFIG)

    # 1. Apply env-var overrides
    for env_var, dotpath in _ENV_OVERRIDES.items():
        env_val = os.getenv(env_var)
        if env_val is not None:
            original = _get_nested(cfg, dotpath)
            coerced  = _coerce(env_val, original)
            _set_nested(cfg, dotpath, coerced)
            logger.debug(f"[Config] ENV override: {env_var} → {dotpath} = {coerced!r}")

    # 2. Apply runtime overrides (dot-path keys supported)
    if overrides:
        for key, val in overrides.items():
            if "." in key:
                _set_nested(cfg, key, val)
            else:
                cfg[key] = val

    # 3. Attach tracing metadata
    cfg["_meta"] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "config_hash":  hashlib.sha256(
            json.dumps(cfg, sort_keys=True, default=str).encode()
        ).hexdigest()[:12],
    }

    return cfg


def snapshot_config(cfg: Dict, run_id: Optional[str] = None) -> Optional[Path]:
    """
    Save a JSON snapshot of the resolved config for reproducibility.

    Args:
        cfg: Resolved config dict (from get_config()).
        run_id: Optional identifier for this run (defaults to timestamp).

    Returns:
        Path to saved snapshot, or None if saving failed.
    """
    import json

    snapshot_dir = Path(_get_nested(cfg, "tracing.config_snapshot_dir", "results/config_snapshots"))
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_path = snapshot_dir / f"config_{run_id}.json"

    try:
        snap_path.write_text(json.dumps(cfg, indent=2, default=str), encoding="utf-8")
        logger.info(f"[Config] Snapshot saved → {snap_path}")
        return snap_path
    except Exception as e:
        logger.warning(f"[Config] Could not save snapshot: {e}")
        return None


# Convenience alias
def voice_cfg(cfg: Dict, role: str) -> Dict:
    """Return voice config for a given role (e.g. 'Anchor')."""
    return cfg.get("voices", {}).get(role, {})


def segment_cfg(cfg: Dict, name: str) -> Dict:
    """Return segment config for a given segment name (e.g. 'deep_dive')."""
    return cfg.get("segments", {}).get(name, {"enabled": True, "voices": ["Anchor"]})


if __name__ == "__main__":
    import json
    cfg = get_config()
    print(json.dumps(cfg, indent=2, default=str))
