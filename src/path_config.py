"""
Path & DEA Configuration Management
=====================================
Centralizes ALL configuration for the DEA system:
  • Output paths (report, backup, podcast)
  • Pipeline feature flags (enabled formats, bitrate, WAV, etc.)
  • AGI narration settings (voices, segments, personalization)
  • Vector store tuning (duplicate threshold, persistence mode)
  • Reproducibility / tracing (config hash, run snapshots)

Config hierarchy (highest → lowest priority):
  1. Runtime overrides passed to get_config()
  2. Environment variables (DEA_* / existing names)
  3. In-code defaults in DEA_CONFIG

All hardcoded values previously scattered across podcast_generator,
multi_format_orchestrator, and qdrant_vector_store now resolve from here.
"""

import os
import logging
import copy
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# MASTER CONFIG DICT  — single source of truth for every tunable parameter
# ─────────────────────────────────────────────────────────────────────────────

DEA_CONFIG: Dict[str, Any] = {

    # ── Identity & Branding ──────────────────────────────────────────────────
    "brand": {
        "podcast_name":   "Vinay DEA Podcast",               # env: DEA_PODCAST_NAME
        "host_name":      "Vinay",                            # env: DEA_HOST_NAME
        "report_title":   "On-Device AI Intelligence Report", # env: DEA_REPORT_TITLE
        "organization":   "DEA Research",                     # env: DEA_ORGANIZATION
    },

    # ── Pipeline feature flags ───────────────────────────────────────────────
    "pipeline": {
        "enabled_formats":  ["email", "pdf", "pptx", "podcast", "transcript", "summary"],
        "generate_wav":     True,          # env: DEA_GENERATE_WAV
        "audio_bitrate":    "192k",        # env: DEA_AUDIO_BITRATE
        "max_paper_slides": 6,             # env: DEA_MAX_PAPER_SLIDES
        "top_k_papers":     6,             # env: DEA_TOP_K_PAPERS
        "backup_on_run":    True,          # env: DEA_BACKUP_ON_RUN
    },

    # ── Podcast / Audio ──────────────────────────────────────────────────────
    "podcast": {
        "language":       "en",                               # env: DEA_PODCAST_LANG
        "tts_engine":     "auto",          # "google" | "gtts" | "auto"
        "silence_ms":     500,             # pause between speakers
        "speaking_rate":  1.0,             # Google TTS speaking rate
        "narration_mode": "agi",           # "agi" | "classic"  env: DEA_NARRATION_MODE
    },

    # ── AGI Narration voices ─────────────────────────────────────────────────
    "voices": {
        "Anchor":     {"google_voice": "en-US-Neural2-D", "gender": "MALE",
                       "description": "Authoritative host, sets context and transitions"},
        "Analyst":    {"google_voice": "en-US-Neural2-C", "gender": "MALE",
                       "description": "Deep technical diver, explains mechanisms"},
        "Questioner": {"google_voice": "en-US-Neural2-E", "gender": "FEMALE",
                       "description": "Asks sharp follow-ups, represents audience"},
        "Skeptic":    {"google_voice": "en-US-Neural2-A", "gender": "MALE",
                       "description": "Challenges assumptions, surfaces counter-arguments"},
        "Futurist":   {"google_voice": "en-US-Neural2-F", "gender": "FEMALE",
                       "description": "Extrapolates trends, connects bigger picture"},
        # Legacy two-speaker aliases kept for backward compat
        "Explainer":  {"google_voice": "en-US-Neural2-C", "gender": "MALE",
                       "description": "Classic explainer (alias for Analyst)"},
    },

    # ── AGI Segment pipeline ─────────────────────────────────────────────────
    "segments": {
        "intro":      {"enabled": True,  "voices": ["Anchor"],                      "max_papers": 0},
        "hook":       {"enabled": True,  "voices": ["Anchor", "Questioner"],         "max_papers": 0},
        "trends":     {"enabled": True,  "voices": ["Anchor", "Analyst"],            "max_papers": 0},
        "deep_dive":  {"enabled": True,  "voices": ["Analyst", "Questioner"],        "max_papers": 6},
        "debate":     {"enabled": True,  "voices": ["Analyst", "Skeptic"],           "max_papers": 3},
        "memory":     {"enabled": True,  "voices": ["Analyst", "Questioner"],        "max_papers": 0},
        "future":     {"enabled": True,  "voices": ["Futurist", "Anchor"],           "max_papers": 0},
        "qa":         {"enabled": True,  "voices": ["Questioner", "Analyst", "Anchor"], "max_papers": 0},
        "summary":    {"enabled": True,  "voices": ["Anchor"],                       "max_papers": 0},
        "outro":      {"enabled": True,  "voices": ["Anchor", "Questioner"],         "max_papers": 0},
    },

    # ── Context-aware personalization ────────────────────────────────────────
    "personalization": {
        "audience":        "AI engineers and product managers",  # env: DEA_AUDIENCE
        "domain_focus":    "on-device AI, edge inference, DRAM optimization",
        "expertise_level": "intermediate",   # beginner | intermediate | expert
        "tone":            "professional-conversational",
    },

    # ── Vector Store ─────────────────────────────────────────────────────────
    "vector_store": {
        "mode":              "memory",      # "memory" | "persistent"  env: DEA_VS_MODE
        "persistence_path":  "results/vector_db",             # env: DEA_VS_PATH
        "duplicate_threshold": 0.95,        # env: DEA_DUP_THRESHOLD
        "similarity_threshold": 0.70,       # for find_similar queries
        "top_k_similar":     3,             # papers returned by find_similar
        # Proposed: semantic cluster tagging — group papers by topic cluster
        "enable_clustering": True,          # env: DEA_VS_CLUSTERING
        "cluster_count":     8,             # target topic clusters
    },

    # ── Tracing & reproducibility ────────────────────────────────────────────
    "tracing": {
        "embed_config_hash":    True,       # stamp config hash in all outputs
        "log_segment_timings":  True,       # log ms per podcast segment
        "config_snapshot_dir":  "results/config_snapshots",
    },
}

# env-var → dot-path mapping
_ENV_MAP: Dict[str, str] = {
    "DEA_PODCAST_NAME":      "brand.podcast_name",
    "DEA_HOST_NAME":         "brand.host_name",
    "DEA_REPORT_TITLE":      "brand.report_title",
    "DEA_ORGANIZATION":      "brand.organization",
    "DEA_GENERATE_WAV":      "pipeline.generate_wav",
    "DEA_AUDIO_BITRATE":     "pipeline.audio_bitrate",
    "DEA_MAX_PAPER_SLIDES":  "pipeline.max_paper_slides",
    "DEA_TOP_K_PAPERS":      "pipeline.top_k_papers",
    "DEA_BACKUP_ON_RUN":     "pipeline.backup_on_run",
    "DEA_PODCAST_LANG":      "podcast.language",
    "DEA_NARRATION_MODE":    "podcast.narration_mode",
    "DEA_AUDIENCE":          "personalization.audience",
    "DEA_VS_MODE":           "vector_store.mode",
    "DEA_VS_PATH":           "vector_store.persistence_path",
    "DEA_DUP_THRESHOLD":     "vector_store.duplicate_threshold",
    "DEA_VS_CLUSTERING":     "vector_store.enable_clustering",
    # legacy names still respected
    "REPORT_OUTPUT_DIR":     "_paths.output_dir",
    "BACKUP_DIR":            "_paths.backup_dir",
    "PODCAST_DIR":           "_paths.podcast_dir",
    "PODCAST_GREETING":      "_paths.podcast_greeting",
    "PODCAST_INTRO_MUSIC_PATH": "_paths.intro_music",
    "PODCAST_OUTRO_MUSIC_PATH": "_paths.outro_music",
}


def _set_nested(d: dict, dotpath: str, value: Any) -> None:
    keys = dotpath.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def _get_nested(d: dict, dotpath: str, default: Any = None) -> Any:
    keys = dotpath.split(".")
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def _coerce(value: str, original: Any) -> Any:
    if isinstance(original, bool):
        return value.lower() in ("1", "true", "yes")
    if isinstance(original, int):
        try:
            return int(value)
        except ValueError:
            return original
    if isinstance(original, float):
        try:
            return float(value)
        except ValueError:
            return original
    return value


def get_config(overrides: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Return a resolved copy of DEA_CONFIG with env-var and runtime overrides.
    Attaches _meta.config_hash for reproducibility tracing.

    Args:
        overrides: flat or nested dict; dot-path keys supported.
    """
    cfg = copy.deepcopy(DEA_CONFIG)

    for env_var, dotpath in _ENV_MAP.items():
        if dotpath.startswith("_paths."):
            continue  # handled by PathConfig singleton
        env_val = os.getenv(env_var)
        if env_val is not None:
            original = _get_nested(cfg, dotpath)
            _set_nested(cfg, dotpath, _coerce(env_val, original))

    if overrides:
        for key, val in overrides.items():
            if "." in key:
                _set_nested(cfg, key, val)
            else:
                cfg[key] = val

    cfg["_meta"] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "config_hash": hashlib.sha256(
            json.dumps(cfg, sort_keys=True, default=str).encode()
        ).hexdigest()[:12],
    }
    return cfg


def snapshot_config(cfg: Dict, run_id: Optional[str] = None) -> Optional[Path]:
    """Save a JSON snapshot of resolved config for full reproducibility."""
    snap_dir = Path(_get_nested(cfg, "tracing.config_snapshot_dir",
                                "results/config_snapshots"))
    snap_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_path = snap_dir / f"config_{run_id}.json"
    try:
        snap_path.write_text(json.dumps(cfg, indent=2, default=str), encoding="utf-8")
        logger.info(f"[Config] Snapshot → {snap_path}")
        return snap_path
    except Exception as e:
        logger.warning(f"[Config] Snapshot failed: {e}")
        return None


class PathConfig:
    """
    Singleton configuration class for managing output paths and DEA system config.

    Backward-compatible with all existing call sites.
    New code should prefer get_config() for full DEA_CONFIG access.
    """

    _instance: Optional["PathConfig"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if PathConfig._initialized:
            return

        # Load paths from environment variables with defaults
        self.report_dir = self._resolve_path(
            os.getenv("REPORT_OUTPUT_DIR", "results/reports")
        )
        self.backup_dir = self._resolve_path(
            os.getenv("BACKUP_DIR", "results/backup")
        )
        self.podcast_dir = self._resolve_path(
            os.getenv("PODCAST_DIR", "results/reports")
        )

        # Podcast configuration
        self.podcast_greeting = os.getenv(
            "PODCAST_GREETING",
            "Hello every one, Good Evening and Good Morning! Welcome to the Vinay DEA Podcast."
        )
        self.podcast_intro_music = os.getenv("PODCAST_INTRO_MUSIC_PATH")
        self.podcast_outro_music = os.getenv("PODCAST_OUTRO_MUSIC_PATH")

        # Resolved DEA config (paths block populated from env above)
        self._dea_cfg: Optional[Dict] = None

        # Ensure all directories exist
        self._ensure_directories_exist()

        # Log configuration
        self._log_configuration()

        PathConfig._initialized = True

    # ── DEA config access ─────────────────────────────────────────────────────

    def get_dea_config(self, overrides: Optional[Dict] = None) -> Dict:
        """
        Return resolved DEA_CONFIG for this run.
        Caches result; pass overrides to bypass cache.
        """
        if overrides or self._dea_cfg is None:
            cfg = get_config(overrides)
            # Inject path values resolved from env into config
            cfg.setdefault("_paths", {}).update({
                "output_dir":       str(self.report_dir),
                "backup_dir":       str(self.backup_dir),
                "podcast_dir":      str(self.podcast_dir),
                "podcast_greeting": self.podcast_greeting,
                "intro_music":      self.podcast_intro_music,
                "outro_music":      self.podcast_outro_music,
            })
            self._dea_cfg = cfg
        return self._dea_cfg

    def get_narration_mode(self) -> str:
        """Return podcast narration mode: 'agi' or 'classic'."""
        return os.getenv("DEA_NARRATION_MODE",
                         DEA_CONFIG["podcast"]["narration_mode"])

    def get_duplicate_threshold(self) -> float:
        """Return vector store duplicate threshold."""
        raw = os.getenv("DEA_DUP_THRESHOLD")
        if raw:
            try:
                return float(raw)
            except ValueError:
                pass
        return DEA_CONFIG["vector_store"]["duplicate_threshold"]

    def get_vector_store_mode(self) -> str:
        """Return vector store persistence mode: 'memory' or 'persistent'."""
        return os.getenv("DEA_VS_MODE",
                         DEA_CONFIG["vector_store"]["mode"])

    def get_vector_store_path(self) -> Path:
        """Return persistence path for vector DB (used in 'persistent' mode)."""
        raw = os.getenv("DEA_VS_PATH",
                        DEA_CONFIG["vector_store"]["persistence_path"])
        return self._resolve_path(raw)

    def get_clustering_enabled(self) -> bool:
        """Return whether semantic clustering is enabled in vector store."""
        raw = os.getenv("DEA_VS_CLUSTERING")
        if raw:
            return raw.lower() in ("1", "true", "yes")
        return DEA_CONFIG["vector_store"]["enable_clustering"]

    def _resolve_path(self, path_str: str) -> Path:
        """
        Resolve path string to absolute Path object.
        Handles both relative and absolute paths.
        """
        path = Path(path_str)
        if not path.is_absolute():
            # Make relative to project root (where main.py is)
            project_root = Path(__file__).parent.parent
            path = project_root / path
        return path.resolve()

    def _ensure_directories_exist(self) -> None:
        """Create all required directories if they don't exist."""
        for directory in [self.report_dir, self.backup_dir, self.podcast_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

    def _log_configuration(self) -> None:
        """Log the current configuration at startup."""
        logger.info("=" * 70)
        logger.info("PATH CONFIGURATION INITIALIZED")
        logger.info("=" * 70)
        logger.info(f"Report Output Directory:  {self.report_dir}")
        logger.info(f"Backup Directory:         {self.backup_dir}")
        logger.info(f"Podcast Output Directory: {self.podcast_dir}")
        logger.info(f"Podcast Greeting:         {self.podcast_greeting[:50]}...")
        if self.podcast_intro_music:
            logger.info(f"Podcast Intro Music:      {self.podcast_intro_music}")
        if self.podcast_outro_music:
            logger.info(f"Podcast Outro Music:      {self.podcast_outro_music}")
        logger.info("=" * 70)

    @classmethod
    def get_instance(cls) -> "PathConfig":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (mainly for testing)."""
        cls._instance = None
        cls._initialized = False

    def get_report_dir(self) -> Path:
        """Get report output directory."""
        return self.report_dir

    def get_backup_dir(self) -> Path:
        """Get backup directory."""
        return self.backup_dir

    def get_podcast_dir(self) -> Path:
        """Get podcast output directory."""
        return self.podcast_dir

    def get_podcast_greeting(self) -> str:
        """Get podcast greeting phrase."""
        return self.podcast_greeting

    def get_podcast_intro_music(self) -> Optional[Path]:
        """Get podcast intro music path if configured."""
        if self.podcast_intro_music:
            return Path(self.podcast_intro_music)
        return None

    def get_podcast_outro_music(self) -> Optional[Path]:
        """Get podcast outro music path if configured."""
        if self.podcast_outro_music:
            return Path(self.podcast_outro_music)
        return None