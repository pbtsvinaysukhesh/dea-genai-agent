"""
Podcast/Audio Generator
========================
Creates audio files with two modes:

  classic (default legacy):
    Natural two-speaker conversation (Explainer & Questioner).
    Preserved exactly as originally implemented.

  agi (new):
    Multi-voice, multi-segment AGI narration with 5 personas
    (Anchor, Analyst, Questioner, Skeptic, Futurist) and 10 dynamic
    segments driven by DEA_CONFIG.  Activated by setting
    narration_mode="agi" in constructor or via DEA_NARRATION_MODE env var.

Both modes share the same TTS backend (Google Cloud TTS / gTTS fallback),
WAV export, and metadata embedding.  All tunable values (voice names, silence
duration, speaking rate, greeting) resolve from PathConfig / DEA_CONFIG so
nothing is hardcoded here.
"""

import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime
import io
import os

logger = logging.getLogger(__name__)

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False
    logger.warning("[Audio] gtts not installed. Install with: pip install gtts")

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    logger.warning("[Audio] pydub not installed. Install with: pip install pydub")

try:
    from google.cloud import texttospeech
    HAS_GOOGLE_TTS = True
except ImportError:
    HAS_GOOGLE_TTS = False
    logger.warning("[Audio] google-cloud-texttospeech not installed. Install with: pip install google-cloud-texttospeech")


class PodcastGenerator:
    """
    Generate audio podcasts with professional two-speaker conversation:
    - Exact greeting phrase at start: "Hello Every One Good Evening & Good morning Welcome to Vinay DEA podcast"
    - Explainer: Discusses research findings (Male voice)
    - Questioner: Asks relevant follow-up questions (Female voice)
    - Natural dialog format with Q&A
    - Dedicated 2-minute summary at end
    - MP3 and WAV output formats
    - Optional intro/outro music support
    - Metadata embedding (title, date, episode number, description, source links)
    - Uses Google Cloud TTS for natural voices (with gTTS fallback)
    """

    def __init__(
        self,
        output_dir: str = "results/reports",
        language: str = "en",
        greeting: Optional[str] = None,
        intro_music_path: Optional[Path] = None,
        outro_music_path: Optional[Path] = None,
        generate_wav: bool = True,
        narration_mode: str = "classic",  # "classic" | "agi"
    ):
        """Initialize podcast generator

        Args:
            output_dir: Directory for output files
            language: Language code for TTS
            greeting: Custom greeting phrase (uses DEA_CONFIG default if None)
            intro_music_path: Path to intro music file
            outro_music_path: Path to outro music file
            generate_wav: Whether to also generate WAV format
            narration_mode: "classic" (two-speaker) or "agi" (multi-voice, multi-segment)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.language = language
        self.generate_wav = generate_wav
        self.intro_music_path = intro_music_path
        self.outro_music_path = outro_music_path
        self.narration_mode = narration_mode

        # Resolve greeting from config hierarchy: arg → env → DEA_CONFIG default
        _default_greeting = (
            "Hello every one, Good Evening and Good Morning! "
            "Welcome to the Vinay DEA Podcast."
        )
        try:
            from src.path_config import PathConfig
            pc = PathConfig.get_instance()
            _default_greeting = pc.podcast_greeting
        except Exception:
            pass
        self.greeting = greeting or _default_greeting

        self.has_gtts = HAS_GTTS
        self.has_pydub = HAS_PYDUB
        self.has_google_tts = HAS_GOOGLE_TTS

        if self.has_google_tts:
            try:
                self.google_client = texttospeech.TextToSpeechClient()
                logger.info("[Audio] Google Cloud TTS initialized")
            except Exception as e:
                logger.warning(f"[Audio] Google Cloud TTS auth failed: {e}. Will use gTTS fallback.")
                self.has_google_tts = False
                self.google_client = None
        else:
            self.google_client = None

        if not self.has_gtts:
            logger.warning("[Audio] gTTS required as fallback. Install: pip install gtts")

    def generate(
        self,
        insights: List[Dict],
        title: str = "On-Device AI Intelligence Report",
        episode_number: Optional[str] = None,
        description: Optional[str] = None,
        source_links: Optional[List[str]] = None,
    ) -> Dict[str, Optional[Path]]:
        """
        Generate professional podcast.

        Routes to AGI multi-voice narration when narration_mode="agi",
        otherwise uses the original classic two-speaker format.

        Args:
            insights: List of paper/insight dictionaries
            title: Podcast episode title
            episode_number: Episode ID or number
            description: Episode description
            source_links: List of source URLs to embed in metadata

        Returns:
            Dict with 'mp3' and 'wav' paths (or None if not generated)
        """
        if not insights:
            logger.warning("[Audio] No insights to generate podcast")
            return {"mp3": None, "wav": None}

        # ── AGI mode: delegate to AGI engine ─────────────────────────────────
        if self.narration_mode == "agi":
            return self._generate_agi(
                insights, episode_number or datetime.now().strftime("%Y%m%d_%H%M%S")
            )

        # ── Classic mode: original implementation below ───────────────────────
        results = {"mp3": None, "wav": None}

        try:
            mp3_path = None
            if self.has_google_tts and self.google_client:
                mp3_path = self._generate_with_google_tts(insights)
            elif self.has_gtts:
                mp3_path = self._generate_with_gtts_fallback(insights)
            else:
                logger.error("[Audio] No TTS engine available")
                return results

            if not mp3_path:
                logger.error("[Audio] MP3 generation failed")
                return results

            results["mp3"] = mp3_path

            if self.generate_wav:
                wav_path = self._convert_mp3_to_wav(mp3_path)
                results["wav"] = wav_path

            self._embed_metadata(
                mp3_path,
                title=title,
                episode_number=episode_number,
                description=description,
                source_links=source_links,
            )
            if results["wav"]:
                from src.audio_metadata import AudioMetadataEmbedder
                AudioMetadataEmbedder.embed_audio_metadata(
                    results["wav"],
                    title=title,
                    episode_number=episode_number,
                    date=datetime.utcnow().isoformat(),
                    description=description,
                    source_links=source_links or [],
                )

            return results

        except Exception as e:
            logger.error(f"[Audio] Generation failed: {e}")
            return {"mp3": None, "wav": None}

    def _generate_agi(self, insights: List[Dict], run_id: str) -> Dict[str, Optional[Path]]:
        """Delegate to AGIPodcastEngine for multi-voice narration."""
        engine = AGIPodcastEngine(
            output_dir=self.output_dir,
            generate_wav=self.generate_wav,
            google_client=self.google_client if self.has_google_tts else None,
            has_gtts=self.has_gtts,
            has_pydub=self.has_pydub,
            language=self.language,
        )
        result = engine.generate(insights, run_id=run_id)
        return {"mp3": result.get("mp3"), "wav": result.get("wav")}

    def _generate_with_google_tts(self, insights: List[Dict]) -> Optional[Path]:
        """Generate podcast using Google Cloud Text-to-Speech with multiple voices"""
        try:
            # Generate timestamp-based filename
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            mp3_path = self.output_dir / f"podcast_{timestamp}.mp3"

            # Build dialog script
            dialog = self._build_dialog_script(insights)

            logger.info(f"[Audio] Synthesizing {len(dialog)} speech segments with Google Cloud TTS...")

            # Synthesize all segments
            audio_segments = []
            for speaker, text in dialog:
                audio_data = self._synthesize_text(text, speaker)
                if audio_data:
                    audio_segments.append(audio_data)
                    # Add pause between speakers
                    silence = AudioSegment.silent(duration=500)
                    audio_segments.append(silence)

            if not audio_segments:
                logger.error("[Audio] No audio segments generated")
                return None

            # Concatenate all segments
            combined = audio_segments[0]
            for segment in audio_segments[1:]:
                combined += segment

            # Export to file
            combined.export(str(mp3_path), format="mp3", bitrate="192k")
            logger.info(f"[Audio] Podcast generated: {mp3_path}")
            return mp3_path

        except Exception as e:
            logger.error(f"[Audio] Google TTS generation failed: {e}")
            return None

    def _synthesize_text(self, text: str, speaker: str):
        """Synthesize text to speech with speaker-specific voice from DEA_CONFIG."""
        try:
            # Resolve voice from config, fall back to legacy mapping
            voice_name = None
            gender_enum = texttospeech.SsmlVoiceGender.MALE
            try:
                from src.path_config import DEA_CONFIG
                vcfg = DEA_CONFIG.get("voices", {}).get(speaker, {})
                voice_name = vcfg.get("google_voice")
                gender_str = vcfg.get("gender", "MALE")
                gender_enum = (
                    texttospeech.SsmlVoiceGender.MALE
                    if gender_str == "MALE"
                    else texttospeech.SsmlVoiceGender.FEMALE
                )
            except Exception:
                pass

            # Legacy fallback
            if not voice_name:
                if speaker == "Explainer":
                    voice_name = "en-US-Neural2-C"
                    gender_enum = texttospeech.SsmlVoiceGender.MALE
                else:
                    voice_name = "en-US-Neural2-E"
                    gender_enum = texttospeech.SsmlVoiceGender.FEMALE

            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name,
                ssml_gender=gender_enum,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
            )

            response = self.google_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
            audio = AudioSegment.from_mp3(io.BytesIO(response.audio_content))
            return audio

        except Exception as e:
            logger.error(f"[Audio] Synthesis failed for {speaker}: {e}")
            return None

    def _generate_with_gtts_fallback(self, insights: List[Dict]) -> Optional[Path]:
        """Fallback to gTTS with speaker labels in text"""
        try:
            # Generate timestamp-based filename
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            mp3_path = self.output_dir / f"podcast_{timestamp}.mp3"

            dialog = self._build_dialog_script(insights)

            # Combine all text with speaker labels
            script = ""
            for speaker, text in dialog:
                script += f"{speaker}: {text}\n\n"

            logger.info(f"[Audio] Generating podcast with gTTS (single voice with speaker labels)...")
            tts = gTTS(text=script, lang=self.language, slow=False)
            tts.save(str(mp3_path))

            logger.info(f"[Audio] Podcast generated: {mp3_path}")
            return mp3_path

        except Exception as e:
            logger.error(f"[Audio] gTTS generation failed: {e}")
            return None

    def _build_dialog_script(self, insights: List[Dict]) -> List[Tuple[str, str]]:
        """
        Build natural, story-driven podcast script like professional news/tech speakers.
        NOT keyword reading - actual engaging narrative discussion.
        """
        today = datetime.now().strftime("%B %d, %Y")
        dialog = []

        # GREETING
        dialog.append(("Explainer", "Hello everyone, welcome to Vinay's DEA podcast."))

        dialog.append(("Explainer", f"""
This is your On-Device AI Intelligence Report for {today}. I'm your AI research analyst,
and joining me today is a research specialist who helps us break down what's really happening
in the world of efficient AI on mobile and edge devices.
        """.strip()))

        # HOOK - Why this matters
        total_papers = len(insights)
        dialog.append(("Questioner", "So we've been tracking AI research for on-device deployment. What kind of momentum are we seeing?"))

        avg_score = sum(i.get('relevance_score', 0) for i in insights) / total_papers if total_papers > 0 else 0
        dialog.append(("Explainer", f"""
This week is actually fascinating. We've gone through {total_papers} distinct research papers and projects,
and the quality is remarkable. On average, these are scoring {avg_score:.1f} out of 100 for relevance to practical on-device AI.
What that tells me is that we're not looking at academic papers that live in journals. We're seeing real work
that engineers can actually use to deploy AI in the real world. That's the sweet spot where research meets practice.
        """.strip()))

        # KEY TRENDS
        platforms = {}
        model_types = {}
        for item in insights:
            platform = item.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1
            model_type = item.get ('model_type', 'Unknown')
            model_types[model_type] = model_types.get(model_type, 0) + 1

        dialog.append(("Questioner", "What platforms are all these papers focused on?"))

        platforms_desc = ", ".join([f"{count} focused on {platform}" for platform, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True)])
        dialog.append(("Explainer", f"""
We're seeing really broad platform coverage this week. {platforms_desc}.
The diversity is actually important because it tells us the industry is serious about making AI work everywhere.
You can't just optimize for one platform anymore. Mobile, laptop, embedded systems - they all have different constraints.
        """.strip()))

        # DEEP DIVE INTO TOP PAPERS
        sorted_insights = sorted(insights, key=lambda x: x.get('relevance_score', 0), reverse=True)

        dialog.append(("Questioner", f"Alright, let's dig into the actual findings. What are the top {min(5, total_papers)} most impactful papers?"))

        dialog.append(("Explainer", f"Great, let's tell the story of what these researchers are actually discovering."))

        for idx, paper in enumerate(sorted_insights[:min(6, len(sorted_insights))], 1):
            title = paper.get('title', 'Unknown')
            score = paper.get('relevance_score', 0)
            platform = paper.get('platform', 'Unknown')
            memory_insight = paper.get('memory_insight', 'N/A')
            dram_impact = paper.get('dram_impact', 'Unknown')
            takeaway = paper.get('engineering_takeaway', 'N/A')
            model_type = paper.get('model_type', 'Unknown')
            source = paper.get('source', 'Unknown')

            # Tell the story of this paper
            dialog.append(("Explainer", f"""
Let me tell you about research number {idx}: "{title}" from {source}.
This scored a {score}, which means this is serious, implementable work. The paper focuses on {model_type} models
and how to deploy them on {platform} devices. Here's what makes it valuable: {memory_insight}.
            """.strip()))

            # Have questioner ask a natural follow-up
            dialog.append(("Questioner", f"That's really interesting. Why does that matter? What's the real-world impact?"))

            # Answer with practical implications
            dialog.append(("Explainer", f"""
This matters because {takeaway}. The DRAM impact is rated as {dram_impact}, which tells you how serious
this constraint is. On {platform}, memory is often the limiting factor that determines whether you can even run the model.
This research shows a genuine path forward that practitioners are using right now.
            """.strip()))

        # MEMORY ENGINEERING ANGLE
        high_impact = len([i for i in insights if i.get('dram_impact') == 'High'])
        medium_impact = len([i for i in insights if i.get('dram_impact') == 'Medium'])

        dialog.append(("Questioner", "You keep mentioning DRAM as a constraint. Are papers really that focused on memory?"))

        dialog.append(("Explainer", f"""
Absolutely. This week we saw {high_impact} papers directly addressing high DRAM constraints,
and {medium_impact} more dealing with medium-tier memory challenges. Think about it: if you're trying to run
an AI model on a phone or edge device, you can't just add more RAM like you would with a server.
You have to work with what's there. That forces fascinating engineering solutions.
Different quantization strategies, clever activation swapping, architectural changes.
It's making the entire field think about efficiency, not just raw power.
        """.strip()))

        # TRENDS AND WRAP-UP
        dialog.append(("Questioner", "What's the big picture? Where is this all heading?"))

        dialog.append(("Explainer", f"""
We're at an inflection point. For years, AI was about making bigger models with more compute.
Now we're asking: how do we make this work everywhere? In pockets, in cars, in edge devices,
in situations where you can't phone home to a data center. The papers this week show
that the industry has answers. Not perfect answers yet, but real, working solutions.
That shift from "can we?" to "how do we do it efficiently?" - that's the story of the research right now.
        """.strip()))

        # CALL TO ACTION
        dialog.append(("Explainer", """
All these findings, all these papers with their source links and technical details,
they're in your full intelligence report. Check out the PDFs, the slide deck,
the comprehensive resource list. Everything is there for you to go deeper.
        """.strip()))

        # CLOSING
        dialog.append(("Questioner", "Thanks for that perspective. Really valuable for everyone building AI systems."))

        dialog.append(("Explainer", """
Thanks for being here. This is the kind of analysis that matters - taking all the noise
from the research community and distilling it into what you actually need to know to build better AI systems.
That's what we do here. Same time next week with fresh insights.
        """.strip()))

        return dialog

    def _build_summary_section(self, insights: List[Dict]) -> str:
        """Build comprehensive summary incorporating all sources and deep-dive findings"""
        total = len(insights)
        avg_score = sum(i.get('relevance_score', 0) for i in insights) / total if total > 0 else 0

        # Analyze trends
        platforms = {}
        model_types = {}
        techniques = {}
        high_impact = 0
        sources_list = []

        for idx, paper in enumerate(insights, 1):
            platform = paper.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1
            model_type = paper.get('model_type', 'Unknown')
            model_types[model_type] = model_types.get(model_type, 0) + 1
            technique = paper.get('quantization_method', 'Unknown')
            techniques[technique] = techniques.get(technique, 0) + 1
            if paper.get('dram_impact') == 'High':
                high_impact += 1

            # Collect all sources
            title = paper.get('title', 'Unknown')
            link = paper.get('link', 'N/A')
            sources_list.append(f"  {idx}. {title} - {link}")

        top_platform = max(platforms.items(), key=lambda x: x[1])[0] if platforms else 'Unknown'
        top_model_type = max(model_types.items(), key=lambda x: x[1])[0] if model_types else 'Unknown'
        top_technique = max(techniques.items(), key=lambda x: x[1])[0] if techniques else 'Unknown'

        sources_summary = "\n".join(sources_list[:5])  # First 5 for audio
        sources_full = "\n".join(sources_list)  # All for reference

        summary = f"""
COMPREHENSIVE SUMMARY AND SOURCE DEEP-DIVE

We've just completed a thorough analysis of {total} research papers on on-device AI optimization.
The average relevance score across all sources is {avg_score:.1f} out of 100, indicating high-quality,
practical research focused on real deployment challenges.

COMPLETE SOURCE LIST:
This deep-dive discussion covered the following sources:
{sources_summary}
And {len(sources_list) - 5 if len(sources_list) > 5 else 0} additional sources available in the full report.

PLATFORM DISTRIBUTION:
The research landscape shows strong focus on {top_platform} platforms, with papers addressing
{', '.join([f"{count} {platform}" for platform, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True)])}.
Each platform has unique constraints, and the research demonstrates platform-specific optimization strategies.

MODEL ARCHITECTURE TRENDS:
The top researched model type is {top_model_type}, followed by emerging work across diverse architectures.
This reflects the industry's current focus on making these popular models efficient for edge deployment.

KEY OPTIMIZATION TECHNIQUES:
The most prevalent optimization approach is {top_technique}, with {', '.join([f"{technique}: {count}"
for technique, count in sorted(techniques.items(), key=lambda x: x[1], reverse=True)[:3]])}.

CRITICAL BOTTLENECK ANALYSIS:
DRAM remains the primary bottleneck in on-device AI. With {high_impact} papers addressing high DRAM impact challenges,
the research community is clearly focused on solving the memory constraint problem.

PRACTICAL TAKEAWAYS FOR IMPLEMENTATION:
First, the research validates that efficient on-device AI is not a future problem – it's a present opportunity.
Second, platform-specific strategies are essential. Third, memory optimization techniques like quantization and pruning
provide immediate, measurable improvements. Fourth, architectural approaches like knowledge distillation are becoming
standard practice.

DEEP-DIVE INSIGHTS:
All {total} sources covered today represent the cutting edge of practical on-device AI implementation. The papers
discuss concrete, implementable approaches that practitioners can apply immediately. Whether you're developing mobile
applications, working on edge computing, or optimizing for constrained devices, these sources provide actionable intelligence.

MEMORY ENGINEERING IMPLICATIONS:
For the memory industry, this research validates the importance of DRAM bandwidth optimization. The solutions being
researched aren't about creating more memory – they're about using memory more intelligently. Efficient attention
mechanisms, selective activation storage, and streaming inference patterns are practical approaches that reduce DRAM
pressure without requiring hardware changes.

FUTURE OUTLOOK:
The trend is unmistakable and accelerating. Efficient on-device AI is moving from academic research to production systems.
The next generation of AI applications will prioritize both capability and efficiency. Organizations that master these
optimization techniques will have competitive advantages in deploying AI solutions on mobile and edge devices.

Thank you for this deep dive through all {total} sources. The complete analysis, including all source links,
detailed metrics, and actionable takeaways, is available in our comprehensive report documents.
        """

        return summary.strip()

    def _convert_mp3_to_wav(self, mp3_path: Path) -> Optional[Path]:
        """Convert MP3 file to WAV format"""
        if not self.has_pydub:
            logger.warning("[Audio] pydub not available, skipping WAV conversion")
            return None

        try:
            wav_path = mp3_path.with_suffix(".wav")
            # Replace timestamp-based mp3_ with podcast_
            wav_name = mp3_path.name.replace(".mp3", ".wav")
            wav_path = mp3_path.parent / wav_name

            # Load MP3 and export as WAV
            audio = AudioSegment.from_mp3(str(mp3_path))
            audio.export(str(wav_path), format="wav")

            logger.info(f"[Audio] Converted to WAV: {wav_path}")
            return wav_path

        except Exception as e:
            logger.warning(f"[Audio] WAV conversion failed: {e}")
            return None

    def _embed_metadata(
        self,
        mp3_path: Path,
        title: str,
        episode_number: Optional[str] = None,
        description: Optional[str] = None,
        source_links: Optional[List[str]] = None,
    ) -> bool:
        """Embed metadata into MP3 file"""
        try:
            from src.audio_metadata import AudioMetadataEmbedder

            return AudioMetadataEmbedder.embed_audio_metadata(
                file_path=mp3_path,
                title=title,
                episode_number=episode_number,
                date=datetime.utcnow().isoformat(),
                description=description,
                source_links=source_links or [],
            )
        except ImportError:
            logger.debug("AudioMetadataEmbedder not available")
            return False
        except Exception as e:
            logger.warning(f"[Audio] Metadata embedding failed: {e}")
            return False


class TranscriptGenerator:
    """
    Generate transcripts of podcast or analysis
    """

    def __init__(self):
        """Initialize transcript generator"""
        pass

    def generate_transcript(self, insights: List[Dict], output_path: str = "results/transcript.txt") -> bool:
        """Generate text transcript from insights"""
        try:
            podcast_gen = PodcastGenerator()
            dialog = podcast_gen._build_dialog_script(insights)

            # Build transcript
            transcript = "PODCAST TRANSCRIPT\n"
            transcript += "=" * 80 + "\n\n"

            for speaker, text in dialog:
                transcript += f"{speaker}:\n{text}\n\n"
                transcript += "-" * 40 + "\n\n"

            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transcript)

            logger.info(f"[Transcript] Generated: {output_path}")
            return True

        except Exception as e:
            logger.error(f"[Transcript] Generation failed: {e}")
            return False


# ─────────────────────────────────────────────────────────────────────────────
# AGI PODCAST ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class AGIPodcastEngine:
    """
    Multi-voice, multi-segment AGI narration engine.

    Used internally by PodcastGenerator when narration_mode="agi".
    Can also be instantiated directly for maximum control.

    Segments (all toggleable via DEA_CONFIG segments.*):
      intro → hook → trends → deep_dive → debate →
      memory → future → qa → summary → outro

    Personas: Anchor, Analyst, Questioner, Skeptic, Futurist
    (voice assignments resolved from DEA_CONFIG voices.*)
    """

    def __init__(
        self,
        output_dir: Path,
        generate_wav: bool = True,
        google_client=None,
        has_gtts: bool = False,
        has_pydub: bool = False,
        language: str = "en",
    ):
        self.output_dir   = output_dir
        self.generate_wav = generate_wav
        self.google_client = google_client
        self.has_gtts     = has_gtts
        self.has_pydub    = has_pydub
        self.language     = language

        # Load DEA_CONFIG
        try:
            from src.path_config import get_config
            self.cfg = get_config()
        except Exception:
            from path_config import get_config
            self.cfg = get_config()

    def generate(self, insights: List[Dict], run_id: str) -> Dict:
        dialog = self._build_dialog(insights)
        transcript_path = self._save_transcript(dialog, run_id)
        mp3_path = wav_path = None

        if self.google_client and self.has_pydub:
            mp3_path = self._render_google(dialog, run_id)
        elif self.has_gtts:
            mp3_path = self._render_gtts(dialog, run_id)

        if mp3_path and self.generate_wav and self.has_pydub:
            wav_path = self._to_wav(mp3_path)

        return {"mp3": mp3_path, "wav": wav_path, "transcript": transcript_path}

    # ── Segment builders ──────────────────────────────────────────────────────

    def _build_dialog(self, insights: List[Dict]) -> List[Tuple[str, str]]:
        today  = datetime.now().strftime("%B %d, %Y")
        total  = len(insights)
        avg    = sum(i.get("relevance_score", 0) for i in insights) / total if total else 0
        brand  = self.cfg.get("brand", {})
        persona = self.cfg.get("personalization", {})
        segs   = self.cfg.get("segments", {})
        greeting = self.cfg.get("_paths", {}).get(
            "podcast_greeting",
            self.cfg.get("podcast", {}).get("greeting",
                "Hello everyone! Welcome to the Vinay DEA Podcast.")
        )

        dialog: List[Tuple[str, str]] = []

        def seg_on(name): return segs.get(name, {}).get("enabled", True)

        # INTRO
        if seg_on("intro"):
            dialog += [
                ("Anchor", greeting),
                ("Anchor", (
                    f"Welcome to {brand.get('podcast_name','DEA Podcast')} — "
                    f"your weekly brief on {persona.get('domain_focus','on-device AI')}. "
                    f"Today is {today}. We've processed {total} research sources."
                )),
            ]

        # HOOK
        if seg_on("hook"):
            dialog += [
                ("Questioner", "Why does this week's batch stand out?"),
                ("Anchor", (
                    f"Average relevance score: {avg:.1f}/100 across {total} papers. "
                    f"Our threshold is 65 — this week's floor is higher. "
                    f"For {persona.get('audience','engineers')}, that means "
                    "directly implementable insights, not academic noise."
                )),
            ]

        # TRENDS
        if seg_on("trends"):
            platforms, model_types, techniques = {}, {}, {}
            for item in insights:
                for d, k in [(platforms, "platform"), (model_types, "model_type"),
                             (techniques, "quantization_method")]:
                    v = item.get(k, "Unknown")
                    d[v] = d.get(v, 0) + 1
            top_p = max(platforms, key=platforms.get, default="Unknown")
            top_m = max(model_types, key=model_types.get, default="Unknown")
            top_t = max(techniques, key=techniques.get, default="Unknown")
            p_desc = ", ".join(
                f"{cnt} on {p}"
                for p, cnt in sorted(platforms.items(), key=lambda x: x[1], reverse=True)
            )
            dialog += [
                ("Anchor", f"Platform coverage: {p_desc}."),
                ("Analyst", (
                    f"Dominant architecture: {top_m}. "
                    f"Leading technique: {top_t}. "
                    f"{top_p} is dominating — highest deployment pressure, "
                    "tightest thermal and memory constraints."
                )),
            ]

        # DEEP DIVE
        if seg_on("deep_dive"):
            limit = segs.get("deep_dive", {}).get("max_papers", 6)
            sorted_p = sorted(insights, key=lambda x: x.get("relevance_score", 0), reverse=True)[:limit]
            dialog.append(("Analyst", f"Let's go through the top {len(sorted_p)} papers mechanistically."))
            for idx, paper in enumerate(sorted_p, 1):
                dialog += [
                    ("Analyst", (
                        f"Paper {idx}: '{paper.get('title','Untitled')}' from {paper.get('source','Unknown')}. "
                        f"Score {paper.get('relevance_score',0)}. "
                        f"Focus: {paper.get('model_type','?')} on {paper.get('platform','?')}. "
                        f"Finding: {paper.get('memory_insight','N/A')}."
                    )),
                    ("Questioner", "What's the practical engineering implication?"),
                    ("Analyst", (
                        f"{paper.get('engineering_takeaway','N/A')} "
                        f"DRAM impact rated {paper.get('dram_impact','Unknown')}."
                    )),
                ]

        # DEBATE
        if seg_on("debate"):
            limit = segs.get("debate", {}).get("max_papers", 3)
            top3 = sorted(insights, key=lambda x: x.get("relevance_score", 0), reverse=True)[:limit]
            titles = "; ".join(p.get("title", "?") for p in top3)
            dialog += [
                ("Analyst", f"Top papers — {titles} — all point to quantization and pruning."),
                ("Skeptic", (
                    "I'd push back. Quantization has been 'the answer' for three years. "
                    "What's genuinely novel here?"
                )),
                ("Analyst", (
                    "The novelty is system-level co-design: scheduling memory transfers, "
                    "overlapping compute and I/O, KV-cache management under constrained DRAM. "
                    "That's harder than a new algorithm."
                )),
                ("Skeptic", "So the breakthrough is hardware-software teams finally talking."),
                ("Analyst", "Exactly. And that's what makes it durable."),
            ]

        # MEMORY
        if seg_on("memory"):
            high = sum(1 for i in insights if i.get("dram_impact") == "High")
            med  = sum(1 for i in insights if i.get("dram_impact") == "Medium")
            dialog += [
                ("Questioner", "DRAM keeps appearing. Give me the concise model."),
                ("Analyst", (
                    f"{high} papers flag DRAM as high-impact, {med} as medium. "
                    "Inference is a memory-bandwidth problem, not compute. "
                    "Your GPU waits for weights. You can't buy out of that on a phone."
                )),
                ("Questioner", "So the papers are optimizing data movement, not arithmetic?"),
                ("Analyst", (
                    "Exactly: fewer bits per parameter, fused ops to reduce DRAM round-trips, "
                    "streaming activations. Memory-bandwidth strategies dressed as 'compression'."
                )),
            ]

        # FUTURE
        if seg_on("future"):
            dialog += [
                ("Futurist", (
                    "Ten-year arc: the edge becomes the primary compute surface. "
                    "Not backup to cloud — the default. "
                    "Every device will run inference that rivals today's data centers "
                    "within milliwatts."
                )),
                ("Anchor", "What's the forcing function?"),
                ("Futurist", (
                    f"Privacy regulation, latency requirements, connectivity costs. "
                    f"For {persona.get('audience','engineers')}, "
                    "the window to build on-device expertise is now."
                )),
            ]

        # Q&A
        if seg_on("qa"):
            expertise = persona.get("expertise_level", "intermediate")
            if expertise == "beginner":
                q = "What's the single most important takeaway for a newcomer?"
                a = ("Start with quantization. Most mature, most impactful, best tooling. "
                     "PyTorch, TF Lite, Core ML all have first-class support.")
            elif expertise == "expert":
                q = "For practitioners already deploying quantized models — where are the remaining cliffs?"
                a = ("KV-cache management at long context. Once weights are quantized, "
                     "dynamic memory for attention is the next bottleneck. "
                     "Sliding window attention and selective cache eviction are the frontier.")
            else:
                q = "Where do I start applying this to a production system?"
                a = ("Profile DRAM bandwidth first. Optimize second. "
                     "Without a baseline, you're blind.")
            dialog += [
                ("Questioner", q),
                ("Analyst",    a),
                ("Questioner", f"Which of these {total} papers is worth reading in full?"),
                ("Analyst", (
                    f"Score above 75 — read in full. Average this week: {avg:.1f}. "
                    "Also filter by DRAM impact = High if your platform matches."
                )),
                ("Anchor", "All source links are in the full report."),
            ]

        # SUMMARY
        if seg_on("summary"):
            platforms2, model_types2, techniques2 = {}, {}, {}
            high2 = 0
            for p in insights:
                pf = p.get("platform", "Unknown")
                mt = p.get("model_type", "Unknown")
                tc = p.get("quantization_method", "Unknown")
                platforms2[pf]   = platforms2.get(pf, 0) + 1
                model_types2[mt] = model_types2.get(mt, 0) + 1
                techniques2[tc]  = techniques2.get(tc, 0) + 1
                if p.get("dram_impact") == "High":
                    high2 += 1
            tp2 = max(platforms2, key=platforms2.get, default="?")
            tm2 = max(model_types2, key=model_types2.get, default="?")
            tt2 = max(techniques2, key=techniques2.get, default="?")
            dialog.append(("Anchor", (
                f"Executive summary: {total} papers, avg relevance {avg:.1f}/100. "
                f"Top platform: {tp2}. Top architecture: {tm2}. "
                f"Top technique: {tt2}. DRAM high-impact: {high2} papers. "
                "Three takeaways: profile DRAM before optimizing; "
                "KV-cache is the new frontier; platform co-design beats generic compression."
            )))

        # OUTRO
        if seg_on("outro"):
            dialog += [
                ("Questioner", "Genuinely valuable depth. Thanks."),
                ("Anchor", (
                    f"That's what {brand.get('podcast_name','DEA Podcast')} exists for. "
                    "Same time next week. Until then — ship something efficient."
                )),
            ]

        return dialog

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render_google(self, dialog: List[Tuple[str, str]], run_id: str) -> Optional[Path]:
        mp3_path = self.output_dir / f"podcast_{run_id}.mp3"
        silence_ms = self.cfg.get("podcast", {}).get("silence_ms", 500)
        rate       = self.cfg.get("podcast", {}).get("speaking_rate", 1.0)
        bitrate    = self.cfg.get("pipeline", {}).get("audio_bitrate", "192k")

        segs = []
        for role, text in dialog:
            audio = self._synth_google(role, text, rate)
            if audio:
                segs.append(audio)
                segs.append(AudioSegment.silent(duration=silence_ms))

        if not segs:
            return None

        combined = segs[0]
        for s in segs[1:]:
            combined += s
        combined.export(str(mp3_path), format="mp3", bitrate=bitrate)
        logger.info(f"[AGI Audio] MP3 → {mp3_path}")
        return mp3_path

    def _synth_google(self, role: str, text: str, rate: float):
        try:
            voices = self.cfg.get("voices", {})
            vcfg   = voices.get(role, {})
            vname  = vcfg.get("google_voice", "en-US-Neural2-D")
            gender = (
                texttospeech.SsmlVoiceGender.MALE
                if vcfg.get("gender", "MALE") == "MALE"
                else texttospeech.SsmlVoiceGender.FEMALE
            )
            resp = self.google_client.synthesize_speech(
                input=texttospeech.SynthesisInput(text=text),
                voice=texttospeech.VoiceSelectionParams(
                    language_code="en-US", name=vname, ssml_gender=gender
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    speaking_rate=rate,
                ),
            )
            return AudioSegment.from_mp3(io.BytesIO(resp.audio_content))
        except Exception as e:
            logger.error(f"[AGI Audio] Google TTS failed for '{role}': {e}")
            return None

    def _render_gtts(self, dialog: List[Tuple[str, str]], run_id: str) -> Optional[Path]:
        mp3_path = self.output_dir / f"podcast_{run_id}.mp3"
        script = "\n\n".join(f"{role}: {text}" for role, text in dialog)
        try:
            tts = gTTS(text=script, lang=self.language, slow=False)
            tts.save(str(mp3_path))
            logger.info(f"[AGI Audio] gTTS MP3 → {mp3_path}")
            return mp3_path
        except Exception as e:
            logger.error(f"[AGI Audio] gTTS failed: {e}")
            return None

    def _to_wav(self, mp3_path: Path) -> Optional[Path]:
        try:
            wav_path = mp3_path.with_suffix(".wav")
            AudioSegment.from_mp3(str(mp3_path)).export(str(wav_path), format="wav")
            logger.info(f"[AGI Audio] WAV → {wav_path}")
            return wav_path
        except Exception as e:
            logger.warning(f"[AGI Audio] WAV conversion failed: {e}")
            return None

    def _save_transcript(self, dialog: List[Tuple[str, str]], run_id: str) -> Optional[Path]:
        path = self.output_dir / f"transcript_{run_id}.txt"
        voices = self.cfg.get("voices", {})
        config_hash = self.cfg.get("_meta", {}).get("config_hash", "")
        lines = [
            "=" * 70,
            f"  DEA PODCAST TRANSCRIPT  |  Run: {run_id}  |  Config: {config_hash}",
            "=" * 70, "",
        ]
        for role, text in dialog:
            desc = voices.get(role, {}).get("description", "")
            lines.append(f"[{role.upper()}]  ({desc})")
            lines.append(text)
            lines.append("-" * 50)
            lines.append("")
        try:
            path.write_text("\n".join(lines), encoding="utf-8")
            logger.info(f"[AGI Audio] Transcript → {path}")
            return path
        except Exception as e:
            logger.warning(f"[AGI Audio] Transcript save failed: {e}")
            return None


# Export for use
__all__ = ['PodcastGenerator', 'TranscriptGenerator', 'AGIPodcastEngine']