"""
Podcast/Audio Generator
Creates audio files with natural two-speaker conversation (Explainer & Questioner format)
Uses Google Cloud Text-to-Speech for multiple voices with fallback to gTTS
Includes greeting phrase, WAV export, metadata embedding, and optional music support.
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
        output_dir: str = "results/podcasts",
        language: str = "en",
        greeting: Optional[str] = None,
        intro_music_path: Optional[Path] = None,
        outro_music_path: Optional[Path] = None,
        generate_wav: bool = True,
    ):
        """Initialize podcast generator

        Args:
            output_dir: Directory for output files
            language: Language code for TTS
            greeting: Custom greeting phrase (uses default if None)
            intro_music_path: Path to intro music file
            outro_music_path: Path to outro music file
            generate_wav: Whether to also generate WAV format
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.language = language
        self.generate_wav = generate_wav
        self.intro_music_path = intro_music_path
        self.outro_music_path = outro_music_path

        # Use provided greeting or default
        self.greeting = greeting or (
            "Hello Every One Good Evening & Good morning Welcome to Vinay DEA podcast"
        )

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
        Generate professional two-speaker podcast with conversation format.

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

        results = {"mp3": None, "wav": None}

        try:
            # Generate MP3 using TTS
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

            # Generate WAV if enabled
            if self.generate_wav:
                wav_path = self._convert_mp3_to_wav(mp3_path)
                results["wav"] = wav_path

            # Embed metadata in both MP3 and WAV
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
        """Synthesize text to speech with specific voice for speaker"""
        try:
            # Select voice based on speaker
            if speaker == "Explainer":
                voice_name = "en-US-Neural2-C"  # Male voice
            else:  # Questioner
                voice_name = "en-US-Neural2-E"  # Female voice

            # Build synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Select voice parameters
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name,
                ssml_gender=texttospeech.SsmlVoiceGender.MALE if speaker == "Explainer" else texttospeech.SsmlVoiceGender.FEMALE
            )

            # Audio config
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0
            )

            # Synthesize
            response = self.google_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Convert to AudioSegment
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
        """Build deep-dive discussion script incorporating all sources and findings"""
        today = datetime.now().strftime("%B %d, %Y")
        dialog = []

        # 0. GREETING PHRASE - Updated to Vinay's DEA Podcast
        greeting = "Hello everyone, welcome to Vinay's DEA podcast."
        dialog.append(("Explainer", greeting))

        # 1. Introduction
        dialog.append(("Explainer", f"""
Welcome to the On-Device AI Intelligence Report podcast for {today}.
I'm your AI research analyst, and I'm here with our research specialist to break down
the latest findings in on-device AI and mobile optimization.
        """.strip()))

        # 2. Executive Summary
        total_papers = len(insights)
        avg_score = sum(i.get('relevance_score', 0) for i in insights) / total_papers if total_papers > 0 else 0

        dialog.append(("Questioner", "So what are we looking at today? How many papers did we analyze this week?"))

        dialog.append(("Explainer", f"""
Great question! We've analyzed {total_papers} papers this week across multiple sources.
The average relevance score is {avg_score:.1f} out of 100. That means we're seeing some really
solid research focused on practical on-device AI deployment.
        """.strip()))

        # Get platform distribution
        platforms = {}
        model_types = {}
        for item in insights:
            platform = item.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1
            model_type = item.get('model_type', 'Unknown')
            model_types[model_type] = model_types.get(model_type, 0) + 1

        platforms_text = ", ".join([f"{count} {platform}" for platform, count in platforms.items()])
        dialog.append(("Questioner", "What platforms are they focusing on?"))
        dialog.append(("Explainer", f"We're seeing research across {platforms_text}. The diversity is actually quite important because different platforms have different constraints."))

        # 3. DEEP-DIVE DISCUSSION - Comprehensive Analysis of All Sources
        sorted_insights = sorted(
            insights,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )

        dialog.append(("Explainer", f"""
Now, let's dive deep into our comprehensive analysis of all {len(sorted_insights)} sources we've gathered this week.
This is where we really dissect what the research is telling us about on-device AI optimization and deployment strategies.
        """.strip()))

        dialog.append(("Questioner", "Perfect. Let's start with the highest-relevance papers and work our way through the complete picture."))

        # SECTION A: Deep analysis of each source with full context
        for idx, paper in enumerate(sorted_insights, 1):
            title = paper.get('title', 'Unknown')
            score = paper.get('relevance_score', 0)
            platform = paper.get('platform', 'Unknown')
            memory_insight = paper.get('memory_insight', 'N/A')
            dram_impact = paper.get('dram_impact', 'Unknown')
            takeaway = paper.get('engineering_takeaway', 'N/A')
            model_type = paper.get('model_type', 'Unknown')
            source_platform = paper.get('source', 'Unknown')
            link = paper.get('link', 'N/A')
            summary_text = paper.get('summary', 'N/A')

            dialog.append(("Explainer", f"""
SOURCE {idx}: {title}
This paper comes from {source_platform} with a relevance score of {score} out of 100.
The research focuses on {platform} platforms with a special emphasis on {model_type} model architectures.
Summary: {summary_text}
Available at: {link}
            """.strip()))

            dialog.append(("Questioner", "What's the core technical contribution here?"))

            dialog.append(("Explainer", f"""
The core insight from this research is: {memory_insight}
The DRAM impact level is {dram_impact}, which indicates the significance for memory-constrained environments.
This directly translates to the engineering takeaway: {takeaway}
What makes this particularly valuable is that it provides a concrete, implementable approach that practitioners
can apply immediately to improve their on-device AI systems.
            """.strip()))

            dialog.append(("Questioner", "How does this fit into the broader context of on-device AI?"))

            dialog.append(("Explainer", f"""
Excellent question. This source addresses a critical pain point in {platform} deployment.
Given the {dram_impact} DRAM impact, it's clear that memory optimization is at the forefront of this research.
The techniques and approaches outlined here represent the cutting edge of practical on-device AI implementation.
This is directly applicable to anyone working on mobile applications, edge computing, or constrained device scenarios.
            """.strip()))

        # 4. Trends Discussion
        dialog.append(("Questioner", "Looking at all these papers together, what are the major trends you're seeing?"))

        high_impact = len([i for i in insights if i.get('dram_impact') == 'High'])
        medium_impact = len([i for i in insights if i.get('dram_impact') == 'Medium'])
        low_impact = len([i for i in insights if i.get('dram_impact') == 'Low'])

        dialog.append(("Explainer", f"""
There are four major trends emerging. First, on-device AI strategy is shifting from "make it work" to "make it efficient."
Second, we're seeing platform-specific optimization strategies. Mobile and laptop require very different approaches.
Third, memory or DRAM remains the critical bottleneck. We have {high_impact} papers with high DRAM impact,
{medium_impact} with medium impact, and {low_impact} with low impact. And fourth, there's growing interest in
cross-platform solutions that balance the constraints of both mobile and laptop deployments.
For memory engineers specifically, this research shows that DRAM bandwidth optimization is becoming increasingly critical,
and techniques like activation swapping, quantization, and efficient attention mechanisms are the frontiers.
        """.strip()))

        # 5. Two-Minute Summary
        dialog.append(("Explainer", self._build_summary_section(insights)))

        # 6. Closing
        dialog.append(("Questioner", "Excellent summary. Where can people find these papers and get more details?"))

        dialog.append(("Explainer", """
Everything is available in our comprehensive report. You'll find PDFs, abstracts, source links,
and detailed analysis for each paper. The full resource section includes direct URLs to each paper.
Whether you're a researcher, memory engineer, or developer, there's actionable intelligence in this week's findings.
        """.strip()))

        # Final closing
        dialog.append(("Questioner", "Thank you for breaking this down. This has been incredibly valuable."))

        dialog.append(("Explainer", """
Thanks for being here. Stay tuned for next week's On-Device AI Intelligence Report podcast.
Keep innovating on the edge!
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


# Export for use
__all__ = ['PodcastGenerator', 'TranscriptGenerator']
