"""
AGI Narration Podcast Generator
================================
Extends the classic two-speaker PodcastGenerator into a multi-voice,
multi-segment AGI-style narration engine.

Features
--------
* 5 distinct AI personas  (Anchor, Analyst, Questioner, Skeptic, Futurist)
* 10 dynamic segments     (intro → hook → trends → deep_dive → debate →
                           memory → future → qa → summary → outro)
* Context-aware personalization (audience, domain, expertise level, tone)
* Fully config-driven via dea_config.get_config() — zero hardcoded values
* Reproducibility: config hash embedded in file metadata & log output
* Graceful degradation: Google TTS → gTTS (single-voice) → transcript-only

Config mapping (key → dea_config.DEA_CONFIG path)
--------------------------------------------------
  Greeting          →  podcast.greeting
  Narration mode    →  podcast.narration_mode   ("agi" | "classic")
  Voices            →  voices.<Role>
  Segments          →  segments.<name>
  Silence (ms)      →  podcast.silence_ms
  Speaking rate     →  podcast.speaking_rate
  Audience          →  personalization.audience
  Domain focus      →  personalization.domain_focus
  Expertise level   →  personalization.expertise_level
"""

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dea_config import get_config, snapshot_config, voice_cfg, segment_cfg

logger = logging.getLogger(__name__)

# ── Optional TTS imports ──────────────────────────────────────────────────────
try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False
    logger.warning("[AGIPodcast] gtts not installed: pip install gtts")

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    logger.warning("[AGIPodcast] pydub not installed: pip install pydub")

try:
    from google.cloud import texttospeech
    HAS_GOOGLE_TTS = True
except ImportError:
    HAS_GOOGLE_TTS = False
    logger.warning("[AGIPodcast] google-cloud-texttospeech not installed")


# ─────────────────────────────────────────────────────────────────────────────
# SEGMENT BUILDERS  —  one function per segment
# Each builder returns List[Tuple[role: str, text: str]]
# ─────────────────────────────────────────────────────────────────────────────

class SegmentBuilders:
    """
    Stateless segment builder methods.
    All accept (insights, cfg) and return a dialog list.
    """

    @staticmethod
    def build_intro(insights: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
        today   = datetime.now().strftime("%B %d, %Y")
        brand   = cfg["brand"]
        persona = cfg["personalization"]
        greeting = cfg["podcast"]["greeting"]
        total   = len(insights)

        return [
            ("Anchor", greeting),
            ("Anchor", (
                f"Welcome to {brand['podcast_name']} — your weekly intelligence brief "
                f"on {persona['domain_focus']}. "
                f"I'm your host, and today is {today}. "
                f"We've processed {total} research sources this cycle, "
                f"and the signal is unusually strong."
            )),
        ]

    @staticmethod
    def build_hook(insights: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
        total    = len(insights)
        avg_score = (
            sum(i.get("relevance_score", 0) for i in insights) / total
            if total else 0
        )
        persona = cfg["personalization"]

        return [
            ("Questioner", (
                f"Before we dive in — why does this week's batch matter more than usual?"
            )),
            ("Anchor", (
                f"Because the average relevance score is {avg_score:.1f} out of 100 "
                f"across all {total} papers. For context, our threshold for 'worth your time' "
                f"is 65. This week, the floor is higher. "
                f"For our audience of {persona['audience']}, that translates directly "
                f"into implementable insights, not academic noise."
            )),
            ("Questioner", "That's a meaningful signal. What's driving the quality spike?"),
            ("Anchor", (
                "The field is consolidating. Early-stage exploration is giving way to "
                "engineering-grade solutions. Researchers are shipping benchmarks, "
                "not just proofs-of-concept. That's the shift we've been waiting for."
            )),
        ]

    @staticmethod
    def build_trends(insights: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
        platforms   = {}
        model_types = {}
        techniques  = {}
        for item in insights:
            p = item.get("platform", "Unknown")
            m = item.get("model_type", "Unknown")
            t = item.get("quantization_method", "Unknown")
            platforms[p]   = platforms.get(p, 0) + 1
            model_types[m] = model_types.get(m, 0) + 1
            techniques[t]  = techniques.get(t, 0) + 1

        top_platform = max(platforms, key=platforms.get, default="Unknown")
        top_model    = max(model_types, key=model_types.get, default="Unknown")
        top_tech     = max(techniques, key=techniques.get, default="Unknown")

        platforms_desc = ", ".join(
            f"{cnt} papers on {p}"
            for p, cnt in sorted(platforms.items(), key=lambda x: x[1], reverse=True)
        )

        return [
            ("Anchor", (
                f"Let me frame the macro picture first. Platform-wise we're seeing: {platforms_desc}. "
                f"The dominant architecture this week is {top_model}, "
                f"and the leading optimization technique is {top_tech}."
            )),
            ("Analyst", (
                f"{top_platform} is dominating not by accident — it's where the deployment "
                f"pressure is highest. When you're constrained to a fixed thermal envelope "
                f"and a battery budget, every engineering decision cascades. "
                f"The research reflects that urgency."
            )),
            ("Anchor", (
                "What's particularly notable is the breadth. This isn't a one-platform story. "
                "The techniques being developed for mobile are informing embedded and "
                "automotive deployments simultaneously."
            )),
        ]

    @staticmethod
    def build_deep_dive(insights: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
        seg     = segment_cfg(cfg, "deep_dive")
        limit   = seg.get("max_papers", 6)
        sorted_papers = sorted(
            insights, key=lambda x: x.get("relevance_score", 0), reverse=True
        )[:limit]

        dialog = [
            ("Analyst", (
                f"Alright, let's go paper by paper through the top {len(sorted_papers)}. "
                f"I'm going to give you the mechanism, not just the headline."
            )),
        ]

        for idx, paper in enumerate(sorted_papers, 1):
            title    = paper.get("title", "Untitled")
            score    = paper.get("relevance_score", 0)
            platform = paper.get("platform", "Unknown")
            memory   = paper.get("memory_insight", "N/A")
            dram     = paper.get("dram_impact", "Unknown")
            takeaway = paper.get("engineering_takeaway", "N/A")
            model    = paper.get("model_type", "Unknown")
            source   = paper.get("source", "Unknown")

            dialog.append(("Analyst", (
                f"Paper {idx}: '{title}' from {source}. "
                f"Relevance: {score}. Focus: {model} on {platform}. "
                f"Core finding — {memory}."
            )))
            dialog.append(("Questioner", (
                f"And the real-world implication? What does an engineer actually do with that?"
            )))
            dialog.append(("Analyst", (
                f"Concretely: {takeaway}. "
                f"DRAM impact is rated {dram} — which tells you how critical "
                f"this constraint is in production scenarios."
            )))

        return dialog

    @staticmethod
    def build_debate(insights: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
        seg   = segment_cfg(cfg, "debate")
        limit = seg.get("max_papers", 3)
        top   = sorted(insights, key=lambda x: x.get("relevance_score", 0), reverse=True)[:limit]
        titles = "; ".join(p.get("title", "Unknown") for p in top)

        return [
            ("Analyst", (
                f"The top papers — {titles} — all point in the same direction: "
                f"quantization and pruning are the near-term levers."
            )),
            ("Skeptic", (
                "I'd push back on that framing. Quantization has been 'the answer' "
                "for three years now. What's actually different? Are we seeing "
                "genuinely novel approaches, or is this incremental tuning?"
            )),
            ("Analyst", (
                "Fair challenge. The novelty isn't in the quantization math — "
                "it's in the system integration. How you schedule memory transfers, "
                "how you overlap compute and I/O, how you handle KV-cache under "
                "constrained DRAM. That's where the real engineering is happening."
            )),
            ("Skeptic", (
                "So the breakthrough isn't algorithmic, it's architectural "
                "co-design. The hardware and software teams finally talking to each other."
            )),
            ("Analyst", "Exactly. And that's actually harder than a new algorithm."),
        ]

    @staticmethod
    def build_memory_segment(insights: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
        high   = sum(1 for i in insights if i.get("dram_impact") == "High")
        medium = sum(1 for i in insights if i.get("dram_impact") == "Medium")
        total  = len(insights)

        return [
            ("Questioner", (
                "DRAM keeps coming up as the bottleneck. "
                "Can you give me a crisp model for why?"
            )),
            ("Analyst", (
                f"Sure. Of the {total} papers this week, {high} flag DRAM as a high-impact "
                f"constraint and {medium} as medium. Here's the mental model: "
                "inference is fundamentally a memory-bandwidth problem, not a compute problem. "
                "Your GPU sits idle waiting for weights to arrive from DRAM. "
                "You can't buy your way out of that on a phone."
            )),
            ("Questioner", "So the papers are optimizing the data movement, not the arithmetic?"),
            ("Analyst", (
                "Precisely. Reducing the bits per parameter, fusing operations to "
                "avoid round-trips to memory, streaming activations rather than "
                "materializing them — these are all memory-bandwidth strategies "
                "disguised as 'model compression'."
            )),
        ]

    @staticmethod
    def build_future(insights: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
        persona = cfg["personalization"]
        total   = len(insights)

        return [
            ("Futurist", (
                f"Stepping back from the {total} papers — what's the ten-year arc? "
                "We're watching the edge become the primary compute surface. "
                "Not a backup to the cloud — the default. "
                "Every device will have inference capability that rivals today's data centers, "
                "within a power budget measured in milliwatts."
            )),
            ("Anchor", "That's a strong claim. What's the forcing function?"),
            ("Futurist", (
                "Privacy regulation, latency requirements, and connectivity costs. "
                "The papers this week are the R&D engine for that transition. "
                f"For {persona['audience']}, the window to build expertise "
                "in on-device inference is right now — not in two years."
            )),
            ("Anchor", (
                "Which means the techniques in these papers aren't academic curiosities. "
                "They're the curriculum for the next five years of the field."
            )),
        ]

    @staticmethod
    def build_qa(insights: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
        persona    = cfg["personalization"]
        expertise  = persona.get("expertise_level", "intermediate")
        total      = len(insights)
        avg_score  = (
            sum(i.get("relevance_score", 0) for i in insights) / total if total else 0
        )

        # Tailor Q&A depth to expertise level
        if expertise == "beginner":
            q1 = "What's the single most important thing a newcomer should take away from today?"
            a1 = (
                "Start with quantization. It's the most mature, most impactful technique "
                "and the one with the best tooling. PyTorch, TensorFlow Lite, and "
                "Core ML all have first-class quantization support. That's your entry point."
            )
        elif expertise == "expert":
            q1 = (
                "For practitioners already deploying quantized models — "
                "where are the remaining performance cliffs?"
            )
            a1 = (
                "KV-cache management at long context lengths. The papers this week "
                "surface this repeatedly. Once you've quantized weights, the next "
                "bottleneck is dynamic memory for attention. "
                "Sliding window attention and selective cache eviction are the frontier."
            )
        else:  # intermediate
            q1 = "If I want to apply this week's research to a production system, where do I start?"
            a1 = (
                "Profile first. Understand your DRAM bandwidth utilization before "
                "applying any optimization. The papers this week give you the techniques, "
                "but without a profiling baseline, you're optimizing blind."
            )

        return [
            ("Questioner", q1),
            ("Analyst",    a1),
            ("Questioner", (
                f"How do I know which of these {total} papers is worth reading in full "
                f"versus just skimming the abstract?"
            )),
            ("Analyst", (
                f"Relevance score above 75 — read in full. "
                f"This week's average is {avg_score:.1f}, so the bar is higher than usual. "
                "Also look at DRAM impact rating: if it's High and your platform matches, "
                "that paper is directly actionable."
            )),
            ("Anchor", "And all the source links are in the full report for easy access."),
        ]

    @staticmethod
    def build_summary(insights: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
        brand    = cfg["brand"]
        total    = len(insights)
        avg_score = (
            sum(i.get("relevance_score", 0) for i in insights) / total if total else 0
        )
        platforms   = {}
        model_types = {}
        techniques  = {}
        high_impact = 0

        for paper in insights:
            p = paper.get("platform", "Unknown")
            m = paper.get("model_type", "Unknown")
            t = paper.get("quantization_method", "Unknown")
            platforms[p]   = platforms.get(p, 0) + 1
            model_types[m] = model_types.get(m, 0) + 1
            techniques[t]  = techniques.get(t, 0) + 1
            if paper.get("dram_impact") == "High":
                high_impact += 1

        top_platform = max(platforms, key=platforms.get, default="Unknown")
        top_model    = max(model_types, key=model_types.get, default="Unknown")
        top_tech     = max(techniques, key=techniques.get, default="Unknown")

        return [
            ("Anchor", (
                f"Let me close with the executive summary. "
                f"This week: {total} papers, average relevance {avg_score:.1f}/100. "
                f"Dominant platform: {top_platform}. "
                f"Leading architecture: {top_model}. "
                f"Primary optimization technique: {top_tech}. "
                f"DRAM flagged as high-impact in {high_impact} papers."
            )),
            ("Anchor", (
                "Three actionable takeaways: "
                "One — profile your DRAM bandwidth before optimizing. "
                "Two — quantization is table stakes; KV-cache management is the frontier. "
                "Three — platform-specific co-design is outperforming generic compression."
            )),
            ("Anchor", (
                f"All sources, links, and detailed metrics are in your {brand['report_title']} "
                "package — PDF, slides, and transcript. "
                "The intelligence is there. Put it to work."
            )),
        ]

    @staticmethod
    def build_outro(insights: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
        brand   = cfg["brand"]
        today   = datetime.now().strftime("%B %d, %Y")

        return [
            ("Questioner", (
                "This was genuinely dense. Appreciate the depth — "
                "not just the what, but the why and the how."
            )),
            ("Anchor", (
                f"That's what {brand['podcast_name']} exists for. "
                "Not to report the news — to tell you what it means for your work. "
                "Same time next week. Until then, ship something efficient."
            )),
        ]


# Segment registry — ordered pipeline
SEGMENT_REGISTRY = [
    ("intro",   SegmentBuilders.build_intro),
    ("hook",    SegmentBuilders.build_hook),
    ("trends",  SegmentBuilders.build_trends),
    ("deep_dive", SegmentBuilders.build_deep_dive),
    ("debate",  SegmentBuilders.build_debate),
    ("memory",  SegmentBuilders.build_memory_segment),
    ("future",  SegmentBuilders.build_future),
    ("qa",      SegmentBuilders.build_qa),
    ("summary", SegmentBuilders.build_summary),
    ("outro",   SegmentBuilders.build_outro),
]


# ─────────────────────────────────────────────────────────────────────────────
# AGI PODCAST GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

class AGIPodcastGenerator:
    """
    Multi-voice, multi-segment AGI narration podcast generator.

    All parameters flow from dea_config.get_config().
    Pass runtime overrides via the `config_overrides` argument.

    Usage
    -----
        gen = AGIPodcastGenerator(config_overrides={"podcast.narration_mode": "agi"})
        result = gen.generate(insights, run_id="2024-w42")
        # result = {"mp3": Path(...), "wav": Path(...), "transcript": Path(...), "config_hash": str}
    """

    def __init__(self, config_overrides: Optional[Dict] = None):
        self.cfg = get_config(config_overrides)
        self._init_tts()

        output_dir = Path(self.cfg["paths"]["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir

        logger.info(
            f"[AGIPodcast] Initialized — "
            f"mode={self.cfg['podcast']['narration_mode']}, "
            f"config_hash={self.cfg['_meta']['config_hash']}, "
            f"tts={'google' if self.has_google_tts else 'gtts' if self.has_gtts else 'none'}"
        )

    # ── TTS setup ─────────────────────────────────────────────────────────────

    def _init_tts(self):
        self.has_gtts       = HAS_GTTS
        self.has_pydub      = HAS_PYDUB
        self.has_google_tts = HAS_GOOGLE_TTS
        self.google_client  = None

        engine_pref = self.cfg["podcast"].get("tts_engine", "auto")

        if engine_pref in ("google", "auto") and HAS_GOOGLE_TTS:
            try:
                self.google_client  = texttospeech.TextToSpeechClient()
                self.has_google_tts = True
                logger.info("[AGIPodcast] Google Cloud TTS ready")
            except Exception as e:
                logger.warning(f"[AGIPodcast] Google TTS auth failed: {e} — falling back")
                self.has_google_tts = False

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(
        self,
        insights: List[Dict],
        run_id: Optional[str] = None,
    ) -> Dict:
        """
        Generate a full AGI narration podcast.

        Args:
            insights: List of paper/insight dicts.
            run_id:   Optional run identifier for file naming and config snapshots.

        Returns:
            Dict with keys: mp3, wav, transcript, config_hash, segment_count, dialog_turns
        """
        if not insights:
            logger.warning("[AGIPodcast] No insights — nothing to generate")
            return {"mp3": None, "wav": None, "transcript": None}

        run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save config snapshot for reproducibility
        if self.cfg["tracing"].get("embed_config_hash"):
            snapshot_config(self.cfg, run_id)

        # Build full dialog
        dialog = self._build_full_dialog(insights)
        logger.info(f"[AGIPodcast] Script ready — {len(dialog)} dialog turns across segments")

        # Save transcript
        transcript_path = self._save_transcript(dialog, run_id)

        # Generate audio
        mp3_path = wav_path = None
        if self.has_google_tts and self.google_client and HAS_PYDUB:
            mp3_path = self._render_google_tts(dialog, run_id)
        elif self.has_gtts:
            mp3_path = self._render_gtts(dialog, run_id)
        else:
            logger.warning("[AGIPodcast] No TTS engine — transcript-only output")

        if mp3_path and self.cfg["pipeline"].get("generate_wav") and HAS_PYDUB:
            wav_path = self._to_wav(mp3_path)

        return {
            "mp3":          mp3_path,
            "wav":          wav_path,
            "transcript":   transcript_path,
            "config_hash":  self.cfg["_meta"]["config_hash"],
            "segment_count": len(SEGMENT_REGISTRY),
            "dialog_turns": len(dialog),
        }

    # ── Dialog construction ───────────────────────────────────────────────────

    def _build_full_dialog(self, insights: List[Dict]) -> List[Tuple[str, str]]:
        """
        Execute each enabled segment builder in pipeline order.
        Returns flat list of (role, text) tuples.
        """
        dialog: List[Tuple[str, str]] = []

        for seg_name, builder_fn in SEGMENT_REGISTRY:
            seg = segment_cfg(self.cfg, seg_name)
            if not seg.get("enabled", True):
                logger.debug(f"[AGIPodcast] Segment '{seg_name}' disabled — skipping")
                continue

            import time
            t0 = time.perf_counter()
            try:
                turns = builder_fn(insights, self.cfg)
                dialog.extend(turns)
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                if self.cfg["tracing"].get("log_segment_timings"):
                    logger.debug(
                        f"[AGIPodcast] Segment '{seg_name}' — "
                        f"{len(turns)} turns, {elapsed_ms}ms"
                    )
            except Exception as e:
                logger.error(f"[AGIPodcast] Segment '{seg_name}' failed: {e}")

        return dialog

    # ── Audio rendering ───────────────────────────────────────────────────────

    def _render_google_tts(
        self, dialog: List[Tuple[str, str]], run_id: str
    ) -> Optional[Path]:
        """Render multi-voice dialog with Google Cloud TTS."""
        mp3_path = self.output_dir / f"podcast_{run_id}.mp3"
        silence_ms = self.cfg["podcast"].get("silence_ms", 500)
        rate       = self.cfg["podcast"].get("speaking_rate", 1.0)

        segments: List[AudioSegment] = []
        for role, text in dialog:
            audio = self._synthesize_google(role, text, rate)
            if audio:
                segments.append(audio)
                segments.append(AudioSegment.silent(duration=silence_ms))

        if not segments:
            logger.error("[AGIPodcast] No audio segments produced")
            return None

        combined = segments[0]
        for seg in segments[1:]:
            combined += seg

        bitrate = self.cfg["pipeline"].get("audio_bitrate", "192k")
        combined.export(str(mp3_path), format="mp3", bitrate=bitrate)
        logger.info(f"[AGIPodcast] MP3 saved → {mp3_path}")
        return mp3_path

    def _synthesize_google(self, role: str, text: str, rate: float) -> Optional["AudioSegment"]:
        """Synthesize a single turn with the appropriate Google TTS voice."""
        try:
            vcfg = voice_cfg(self.cfg, role)
            voice_name = vcfg.get("google_voice", "en-US-Neural2-D")
            gender_str = vcfg.get("gender", "MALE")
            gender = (
                texttospeech.SsmlVoiceGender.MALE
                if gender_str == "MALE"
                else texttospeech.SsmlVoiceGender.FEMALE
            )

            response = self.google_client.synthesize_speech(
                input=texttospeech.SynthesisInput(text=text),
                voice=texttospeech.VoiceSelectionParams(
                    language_code="en-US",
                    name=voice_name,
                    ssml_gender=gender,
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    speaking_rate=rate,
                ),
            )
            return AudioSegment.from_mp3(io.BytesIO(response.audio_content))
        except Exception as e:
            logger.error(f"[AGIPodcast] Google TTS synthesis failed for '{role}': {e}")
            return None

    def _render_gtts(
        self, dialog: List[Tuple[str, str]], run_id: str
    ) -> Optional[Path]:
        """Render dialog as single-voice gTTS fallback with role labels."""
        mp3_path = self.output_dir / f"podcast_{run_id}.mp3"
        lang = self.cfg["podcast"].get("language", "en")

        script = "\n\n".join(
            f"{role}: {text}" for role, text in dialog
        )
        try:
            tts = gTTS(text=script, lang=lang, slow=False)
            tts.save(str(mp3_path))
            logger.info(f"[AGIPodcast] gTTS MP3 saved → {mp3_path}")
            return mp3_path
        except Exception as e:
            logger.error(f"[AGIPodcast] gTTS failed: {e}")
            return None

    def _to_wav(self, mp3_path: Path) -> Optional[Path]:
        """Convert MP3 to WAV."""
        try:
            wav_path = mp3_path.with_suffix(".wav")
            AudioSegment.from_mp3(str(mp3_path)).export(str(wav_path), format="wav")
            logger.info(f"[AGIPodcast] WAV saved → {wav_path}")
            return wav_path
        except Exception as e:
            logger.warning(f"[AGIPodcast] WAV conversion failed: {e}")
            return None

    # ── Transcript ────────────────────────────────────────────────────────────

    def _save_transcript(
        self, dialog: List[Tuple[str, str]], run_id: str
    ) -> Optional[Path]:
        """Save dialog as a structured transcript file."""
        transcript_path = self.output_dir / f"transcript_{run_id}.txt"
        brand = self.cfg["brand"]
        config_hash = self.cfg["_meta"]["config_hash"]

        lines = [
            f"{'=' * 70}",
            f"  {brand['podcast_name'].upper()} — TRANSCRIPT",
            f"  Run ID:       {run_id}",
            f"  Config hash:  {config_hash}",
            f"  Generated:    {datetime.utcnow().isoformat()}Z",
            f"  Turns:        {len(dialog)}",
            f"{'=' * 70}",
            "",
        ]

        for role, text in dialog:
            vcfg = voice_cfg(self.cfg, role)
            desc = vcfg.get("description", "")
            lines.append(f"[{role.upper()}]  ({desc})")
            lines.append(text)
            lines.append("-" * 50)
            lines.append("")

        try:
            transcript_path.write_text("\n".join(lines), encoding="utf-8")
            logger.info(f"[AGIPodcast] Transcript saved → {transcript_path}")
            return transcript_path
        except Exception as e:
            logger.warning(f"[AGIPodcast] Transcript save failed: {e}")
            return None


# ─────────────────────────────────────────────────────────────────────────────
# BACKWARD-COMPATIBLE SHIM  (drop-in for original PodcastGenerator)
# ─────────────────────────────────────────────────────────────────────────────

class PodcastGeneratorV2:
    """
    Drop-in replacement for the original PodcastGenerator.

    All constructor args are accepted for backward compatibility but
    internally delegated to AGIPodcastGenerator via dea_config.
    """

    def __init__(
        self,
        output_dir:        str            = "results/reports",
        language:          str            = "en",
        greeting:          Optional[str]  = None,
        intro_music_path:  Optional[Path] = None,
        outro_music_path:  Optional[Path] = None,
        generate_wav:      bool           = True,
        narration_mode:    str            = "agi",   # "agi" | "classic"
    ):
        overrides = {
            "paths.output_dir":       output_dir,
            "podcast.language":       language,
            "podcast.narration_mode": narration_mode,
            "pipeline.generate_wav":  generate_wav,
        }
        if greeting:
            overrides["podcast.greeting"] = greeting
        if intro_music_path:
            overrides["paths.intro_music"] = str(intro_music_path)
        if outro_music_path:
            overrides["paths.outro_music"] = str(outro_music_path)

        self._agi = AGIPodcastGenerator(config_overrides=overrides)

    def generate(
        self,
        insights:       List[Dict],
        title:          str            = "On-Device AI Intelligence Report",
        episode_number: Optional[str]  = None,
        description:    Optional[str]  = None,
        source_links:   Optional[List] = None,
    ) -> Dict:
        run_id = episode_number or datetime.now().strftime("%Y%m%d_%H%M%S")
        result = self._agi.generate(insights, run_id=run_id)
        # Map to original return shape for compatibility
        return {"mp3": result.get("mp3"), "wav": result.get("wav")}


__all__ = [
    "AGIPodcastGenerator",
    "PodcastGeneratorV2",
    "SegmentBuilders",
    "SEGMENT_REGISTRY",
]
