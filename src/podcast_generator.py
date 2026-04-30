"""
Podcast/Audio Generator
========================

Default mode produces a natural two-speaker technical conversation:
- Host: male voice when provider supports it
- Analyst: female voice when provider supports it
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.path_config import PathConfig, get_config

logger = logging.getLogger(__name__)

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False
    logger.warning("[Audio] gtts not installed. Install with: pip install gTTS")

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False
    logger.info("[Audio] edge-tts not installed. Install with: pip install edge-tts")

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
    logger.warning(
        "[Audio] google-cloud-texttospeech not installed. "
        "Install with: pip install google-cloud-texttospeech"
    )


DialogTurn = Tuple[str, str]

DEFAULT_PODCAST_CONFIG = {
    "conversation_mode": "two_speaker",
    "provider_priority": ["google", "edge", "gtts"],
    "target_duration_minutes": 10,
    "max_turns": 24,
    "papers_to_cover": 4,
    "include_source_mentions": False,
    "include_scores_in_audio": False,
    "voices": {
        "edge": {
            "male": ["en-US-AndrewMultilingualNeural", "en-US-GuyNeural"],
            "female": ["en-US-AvaMultilingualNeural", "en-US-JennyNeural"],
            "host_rate": "+0%",
            "analyst_rate": "+6%",
            "pause_ms": 425,
        },
        "google": {
            "male": ["en-US-Neural2-J", "en-US-Neural2-D", "en-US-Neural2-C"],
            "female": ["en-US-Neural2-F", "en-US-Neural2-E"],
            "host_rate": 0.97,
            "analyst_rate": 1.02,
            "pause_ms": 475,
        },
        "gtts": {"pause_ms": 350},
    },
}


class PodcastGenerator:
    """Generate a technical two-speaker podcast and matching transcript."""

    HOST_ROLE = "Host"
    ANALYST_ROLE = "Analyst"

    def __init__(
        self,
        output_dir: str = "results/reports",
        language: str = "en",
        greeting: Optional[str] = None,
        intro_music_path: Optional[Path] = None,
        outro_music_path: Optional[Path] = None,
        generate_wav: bool = True,
        narration_mode: str = "classic",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.language = language
        self.generate_wav = generate_wav
        self.intro_music_path = intro_music_path
        self.outro_music_path = outro_music_path
        self.narration_mode = narration_mode

        self.path_config = PathConfig.get_instance()
        self.runtime_config = get_config()
        self.podcast_config = self._load_podcast_config()
        self.greeting = (
            greeting
            or self.path_config.get_podcast_greeting()
            or self.podcast_config.get("greeting")
            or "Hello everyone, welcome to the Vinay DEA podcast."
        )

        self.has_gtts = HAS_GTTS
        self.has_pydub = HAS_PYDUB
        self.has_google_tts = HAS_GOOGLE_TTS
        self.has_edge_tts = HAS_EDGE_TTS
        self.google_client = None
        self.last_dialog: List[DialogTurn] = []
        self.last_story_pack: Dict = {}

        if self.has_google_tts:
            try:
                self.google_client = texttospeech.TextToSpeechClient()
                logger.info("[Audio] Google Cloud TTS initialized")
            except Exception as exc:
                logger.warning("[Audio] Google Cloud TTS auth failed: %s", exc)
                self.has_google_tts = False

    def generate(
        self,
        insights: List[Dict],
        title: str = "On-Device AI Intelligence Report",
        episode_number: Optional[str] = None,
        description: Optional[str] = None,
        source_links: Optional[List[str]] = None,
    ) -> Dict[str, Optional[Path]]:
        if not insights:
            logger.warning("[Audio] No insights to generate podcast")
            return {"mp3": None, "wav": None, "transcript": None, "provider": None}

        run_id = episode_number or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dialog = self.build_dialog(insights)
        transcript_path = self._save_transcript(dialog, self.output_dir / "transcript.txt")

        mp3_path, provider = self._render_dialog(dialog, run_id)
        if not mp3_path:
            return {
                "mp3": None,
                "wav": None,
                "transcript": transcript_path,
                "provider": None,
            }

        wav_path = self._convert_mp3_to_wav(mp3_path) if self.generate_wav else None
        self._embed_metadata(mp3_path, title, episode_number, description, source_links)
        if wav_path:
            self._embed_wav_metadata(wav_path, title, episode_number, description, source_links)

        return {
            "mp3": mp3_path,
            "wav": wav_path,
            "transcript": transcript_path,
            "provider": provider,
        }

    def build_dialog(self, insights: List[Dict]) -> List[DialogTurn]:
        story_pack = self._build_podcast_story_pack(insights)
        dialog = self._build_dialog_script(story_pack)
        self.last_story_pack = story_pack
        self.last_dialog = dialog
        return dialog

    def _load_podcast_config(self) -> Dict:
        cfg = dict(DEFAULT_PODCAST_CONFIG)
        podcast_cfg = (self.runtime_config or {}).get("podcast", {})
        cfg.update(
            {
                "conversation_mode": podcast_cfg.get("conversation_mode", cfg["conversation_mode"]),
                "provider_priority": podcast_cfg.get("provider_priority", cfg["provider_priority"]),
                "target_duration_minutes": podcast_cfg.get(
                    "target_duration_minutes", cfg["target_duration_minutes"]
                ),
                "max_turns": podcast_cfg.get("max_turns", cfg["max_turns"]),
                "papers_to_cover": podcast_cfg.get("papers_to_cover", cfg["papers_to_cover"]),
                "include_source_mentions": podcast_cfg.get(
                    "include_source_mentions", cfg["include_source_mentions"]
                ),
                "include_scores_in_audio": podcast_cfg.get(
                    "include_scores_in_audio", cfg["include_scores_in_audio"]
                ),
                "greeting": podcast_cfg.get("greeting"),
            }
        )
        merged_voices = {}
        for provider, defaults in cfg["voices"].items():
            provider_cfg = podcast_cfg.get("voices", {}).get(provider, {})
            merged = dict(defaults)
            merged.update(provider_cfg)
            merged_voices[provider] = merged
        cfg["voices"] = merged_voices
        return cfg

    def _build_podcast_story_pack(self, insights: List[Dict]) -> Dict:
        sorted_insights = sorted(
            insights, key=lambda item: item.get("relevance_score", 0), reverse=True
        )
        selected = sorted_insights[: max(1, int(self.podcast_config["papers_to_cover"]))]
        total = len(insights)
        avg_score = (
            sum(item.get("relevance_score", 0) for item in insights) / total if total else 0
        )

        platforms: Dict[str, int] = {}
        techniques: Dict[str, int] = {}
        model_types: Dict[str, int] = {}
        high_dram = 0
        for item in insights:
            platform = item.get("platform", "Unknown")
            technique = item.get("quantization_method", "Unknown")
            model_type = item.get("model_type", "Unknown")
            platforms[platform] = platforms.get(platform, 0) + 1
            techniques[technique] = techniques.get(technique, 0) + 1
            model_types[model_type] = model_types.get(model_type, 0) + 1
            if item.get("dram_impact") == "High":
                high_dram += 1

        top_platform = max(platforms, key=platforms.get, default="Unknown")
        top_technique = max(techniques, key=techniques.get, default="Unknown")
        top_model_type = max(model_types, key=model_types.get, default="Unknown")

        beats = []
        for idx, paper in enumerate(selected, 1):
            beats.append(
                {
                    "index": idx,
                    "title": paper.get("title", "Untitled paper"),
                    "source": paper.get("source", "Unknown source"),
                    "platform": paper.get("platform", "Unknown platform"),
                    "score": paper.get("relevance_score", 0),
                    "summary": self._clean_tts_text(
                        paper.get("executive_summary")
                        or paper.get("memory_insight")
                        or paper.get("summary")
                        or "The paper focuses on efficient on-device AI execution."
                    ),
                    "impact": self._clean_tts_text(
                        paper.get("why_it_matters")
                        or paper.get("engineering_takeaway")
                        or "The main value is a practical path to improve memory efficiency."
                    ),
                    "tradeoff": self._clean_tts_text(
                        paper.get("implementation_guidance")
                        or paper.get("research_brief", {}).get("result", "")
                        or "The tradeoff is balancing memory savings against latency and quality."
                    ),
                    "metrics": [
                        self._clean_tts_text(str(metric))
                        for metric in (paper.get("key_metrics") or [])[:3]
                    ],
                    "dram_impact": paper.get("dram_impact", "Unknown"),
                }
            )

        comparisons = []
        if len(selected) >= 2:
            first, second = selected[0], selected[1]
            comparisons.append(
                self._clean_tts_text(
                    f"The strongest contrast this week is between {first.get('title', 'the first paper')} "
                    f"and {second.get('title', 'the second paper')}: one leans on model-side efficiency, "
                    f"while the other leans on system-level memory movement."
                )
            )
        comparisons.append(
            self._clean_tts_text(
                f"Across the batch, the repeated theme is {top_technique} on {top_platform} deployments, "
                f"with {top_model_type} as the most common model family."
            )
        )

        return {
            "date": datetime.now().strftime("%B %d, %Y"),
            "total_papers": total,
            "avg_score": avg_score,
            "top_platform": top_platform,
            "top_technique": top_technique,
            "top_model_type": top_model_type,
            "high_dram_count": high_dram,
            "opening_theme": self._clean_tts_text(
                f"This week feels practical: the research is less about abstract benchmarks and more "
                f"about making {top_model_type} workloads behave on {top_platform} hardware."
            ),
            "discussion_beats": beats,
            "comparisons": comparisons,
            "practical_takeaways": [
                "Profile memory bandwidth before tuning kernels.",
                "Treat quantization, cache policy, and data movement as one system problem.",
                "Prioritize papers with high DRAM impact when deciding what to prototype next.",
            ],
        }

    def _build_dialog_script(self, story_pack: Dict) -> List[DialogTurn]:
        nim_key = os.getenv("NVIDIA_NIM_API_KEY")
        if nim_key:
            ai_dialog = self._ai_rewrite_dialog(story_pack)
            if ai_dialog:
                return ai_dialog[: int(self.podcast_config["max_turns"])]
        return self._build_template_dialog(story_pack)

    def _ai_rewrite_dialog(self, story_pack: Dict) -> Optional[List[DialogTurn]]:
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
        except ImportError:
            return None

        beat_lines = []
        for beat in story_pack["discussion_beats"]:
            metric_text = ", ".join(beat["metrics"]) if beat["metrics"] else "No standout metric"
            beat_lines.append(
                "\n".join(
                    [
                        f"Paper {beat['index']}: {beat['title']}",
                        f"Platform: {beat['platform']} | Source: {beat['source']} | DRAM impact: {beat['dram_impact']}",
                        f"Summary: {beat['summary']}",
                        f"Engineering impact: {beat['impact']}",
                        f"Tradeoff: {beat['tradeoff']}",
                        f"Metrics: {metric_text}",
                    ]
                )
            )

        prompt = f"""Write a natural technical podcast conversation between exactly two speakers.
Speaker 1 is Host. Host should sound like a steady male presenter who asks concise follow-up questions.
Speaker 2 is Analyst. Analyst should sound like a sharp female engineer who explains findings clearly.

Rules:
- Output only lines that start with "Host:" or "Analyst:"
- Keep each turn to 1-3 sentences
- Keep the total turns under {int(self.podcast_config["max_turns"])}
- Avoid repeating the greeting after the opening line
- Do not sound like you are reading a report
- Use natural callbacks like "that matters because", "the catch is", "what I like here"
- {'Mention source names only when genuinely useful.' if self.podcast_config['include_source_mentions'] else 'Do not keep repeating source names.'}
- {'You may mention scores sparingly.' if self.podcast_config['include_scores_in_audio'] else 'Do not read numeric scores unless essential.'}

Open with this exact first line:
Host: {self._clean_tts_text(self.greeting)}

Episode facts:
- Date: {story_pack['date']}
- Total papers: {story_pack['total_papers']}
- Average relevance: {story_pack['avg_score']:.1f}
- Opening theme: {story_pack['opening_theme']}
- Comparison themes:
{chr(10).join(story_pack['comparisons'])}

Papers to cover:
{chr(10).join(beat_lines)}

Closing takeaways:
{chr(10).join(story_pack['practical_takeaways'])}
"""

        try:
            client = ChatNVIDIA(
                model=((self.runtime_config or {}).get("nim", {}) or {}).get(
                    "model", "moonshotai/kimi-k2-thinking"
                ),
                api_key=os.getenv("NVIDIA_NIM_API_KEY"),
                temperature=0.4,
                max_tokens=4096,
            )
            response = client.invoke(prompt)
            return self._parse_dialog_response(getattr(response, "content", ""))
        except Exception as exc:
            logger.warning("[Audio] AI dialog rewrite failed: %s", exc)
            return None

    def _parse_dialog_response(self, text: str) -> List[DialogTurn]:
        if "<think>" in text and "</think>" in text:
            text = text.split("</think>")[-1]

        dialog: List[DialogTurn] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("Host:"):
                spoken = self._clean_tts_text(line[len("Host:") :].strip())
                if spoken:
                    dialog.append((self.HOST_ROLE, spoken))
            elif line.startswith("Analyst:"):
                spoken = self._clean_tts_text(line[len("Analyst:") :].strip())
                if spoken:
                    dialog.append((self.ANALYST_ROLE, spoken))
        return dialog if len(dialog) >= 8 else []

    def _build_template_dialog(self, story_pack: Dict) -> List[DialogTurn]:
        dialog: List[DialogTurn] = [
            (self.HOST_ROLE, self._clean_tts_text(self.greeting)),
            (
                self.ANALYST_ROLE,
                self._clean_tts_text(
                    f"Today is {story_pack['date']}, and this batch feels unusually practical. "
                    f"We reviewed {story_pack['total_papers']} papers, and the thread running through them "
                    f"is how to make models behave on real devices."
                ),
            ),
            (self.HOST_ROLE, "What is the headline before we get into individual papers?"),
            (
                self.ANALYST_ROLE,
                self._clean_tts_text(
                    f"{story_pack['opening_theme']} The repeated bottleneck is memory movement."
                ),
            ),
            (
                self.HOST_ROLE,
                "So the interesting work is not just smaller models. It is better system behavior too?",
            ),
            (
                self.ANALYST_ROLE,
                self._clean_tts_text(
                    f"{story_pack['comparisons'][0]} That is why these papers feel closer to shipping code than research theater."
                ),
            ),
        ]

        for beat in story_pack["discussion_beats"]:
            title_fragment = beat["title"] if len(beat["title"]) < 80 else beat["title"][:77] + "..."
            source_fragment = (
                f" from {beat['source']}" if self.podcast_config["include_source_mentions"] else ""
            )
            score_fragment = (
                f" It scored {beat['score']} in our ranking."
                if self.podcast_config["include_scores_in_audio"]
                else ""
            )
            metric_fragment = f" One useful number to remember is {beat['metrics'][0]}." if beat["metrics"] else ""
            dialog.extend(
                [
                    (
                        self.HOST_ROLE,
                        self._clean_tts_text(
                            f"Let's start with {title_fragment}{source_fragment}. What made it worth pulling into the conversation?{score_fragment}"
                        ),
                    ),
                    (
                        self.ANALYST_ROLE,
                        self._clean_tts_text(
                            f"{beat['summary']} {metric_fragment} The practical point is that it targets {beat['platform']} constraints directly."
                        ),
                    ),
                    (
                        self.HOST_ROLE,
                        "What is the engineering catch once you move from a paper result to a product build?",
                    ),
                    (
                        self.ANALYST_ROLE,
                        self._clean_tts_text(
                            f"{beat['tradeoff']} The reason it matters is simple: {beat['impact']}"
                        ),
                    ),
                ]
            )

        dialog.extend(
            [
                (
                    self.HOST_ROLE,
                    "If you step back from the individual papers, what pattern would you tell an engineering team to pay attention to?",
                ),
                (
                    self.ANALYST_ROLE,
                    self._clean_tts_text(
                        story_pack["comparisons"][-1]
                        + f" And {story_pack['high_dram_count']} of the papers explicitly treat DRAM as a high-impact bottleneck."
                    ),
                ),
                (
                    self.HOST_ROLE,
                    "What should someone do Monday morning if they want to act on this instead of just admiring the research?",
                ),
                (
                    self.ANALYST_ROLE,
                    self._clean_tts_text(" ".join(story_pack["practical_takeaways"])),
                ),
                (
                    self.HOST_ROLE,
                    "That is a solid place to leave it. Thanks for turning the papers into something people can actually use.",
                ),
                (
                    self.ANALYST_ROLE,
                    "Always happy to. The full report has the source trail, and we will keep the next episode just as practical.",
                ),
            ]
        )
        return dialog[: int(self.podcast_config["max_turns"])]

    def _render_dialog(self, dialog: List[DialogTurn], run_id: str) -> Tuple[Optional[Path], Optional[str]]:
        for provider in self._iter_available_providers():
            path = self._render_with_provider(dialog, provider, run_id)
            if path:
                return path, provider
        return None, None

    def _iter_available_providers(self) -> List[str]:
        available = []
        for provider in self.podcast_config["provider_priority"]:
            if provider == "edge" and self.has_edge_tts and self.has_pydub:
                available.append(provider)
            elif provider == "google" and self.has_google_tts and self.google_client and self.has_pydub:
                available.append(provider)
            elif provider == "gtts" and self.has_gtts:
                available.append(provider)
        return available

    def _render_with_provider(self, dialog: List[DialogTurn], provider: str, run_id: str) -> Optional[Path]:
        if provider == "edge":
            return self._render_with_edge(dialog, run_id)
        if provider == "google":
            return self._render_with_google(dialog, run_id)
        if provider == "gtts":
            return self._render_with_gtts(dialog, run_id)
        return None

    def _render_with_edge(self, dialog: List[DialogTurn], run_id: str) -> Optional[Path]:
        voice_cfg = self.podcast_config["voices"]["edge"]
        mp3_path = self.output_dir / f"podcast_{run_id}.mp3"

        async def _synthesize_all() -> List[AudioSegment]:
            segments: List[AudioSegment] = []
            for idx, (speaker, text) in enumerate(dialog):
                rate = voice_cfg["host_rate"] if speaker == self.HOST_ROLE else voice_cfg["analyst_rate"]
                segment = await self._synthesize_edge_segment(
                    text, self._voice_candidates_for_provider("edge", speaker), rate, idx
                )
                if segment is None:
                    return []
                segments.append(segment)
                segments.append(AudioSegment.silent(duration=int(voice_cfg["pause_ms"])))
            return segments

        try:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                segments = loop.run_until_complete(_synthesize_all())
            finally:
                asyncio.set_event_loop(None)
                loop.close()

            if not segments:
                return None

            combined = segments[0]
            for segment in segments[1:]:
                combined += segment
            combined.export(str(mp3_path), format="mp3", bitrate="192k")
            return mp3_path
        except Exception as exc:
            logger.warning("[Audio] edge-tts generation failed: %s", exc)
            return None

    async def _synthesize_edge_segment(
        self, text: str, voices: List[str], rate: str, index: int
    ) -> Optional[AudioSegment]:
        for voice in voices:
            seg_path = self.output_dir / f"_edge_seg_{index}.mp3"
            try:
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                await communicate.save(str(seg_path))
                return AudioSegment.from_mp3(str(seg_path))
            except Exception as exc:
                logger.warning("[Audio] edge-tts voice %s failed: %s", voice, exc)
            finally:
                try:
                    seg_path.unlink(missing_ok=True)
                except Exception:
                    pass
        return None

    def _render_with_google(self, dialog: List[DialogTurn], run_id: str) -> Optional[Path]:
        voice_cfg = self.podcast_config["voices"]["google"]
        mp3_path = self.output_dir / f"podcast_{run_id}.mp3"
        try:
            segments: List[AudioSegment] = []
            for speaker, text in dialog:
                rate = voice_cfg["host_rate"] if speaker == self.HOST_ROLE else voice_cfg["analyst_rate"]
                audio = self._synthesize_google_segment(text, speaker, float(rate))
                if audio is None:
                    return None
                segments.append(audio)
                segments.append(AudioSegment.silent(duration=int(voice_cfg["pause_ms"])))

            combined = segments[0]
            for segment in segments[1:]:
                combined += segment
            combined.export(str(mp3_path), format="mp3", bitrate="192k")
            return mp3_path
        except Exception as exc:
            logger.warning("[Audio] Google TTS generation failed: %s", exc)
            return None

    def _synthesize_google_segment(self, text: str, speaker: str, speaking_rate: float) -> Optional[AudioSegment]:
        gender = (
            texttospeech.SsmlVoiceGender.MALE if speaker == self.HOST_ROLE else texttospeech.SsmlVoiceGender.FEMALE
        )
        for voice_name in self._voice_candidates_for_provider("google", speaker):
            try:
                response = self.google_client.synthesize_speech(
                    input=texttospeech.SynthesisInput(text=text),
                    voice=texttospeech.VoiceSelectionParams(
                        language_code="en-US", name=voice_name, ssml_gender=gender
                    ),
                    audio_config=texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.MP3,
                        speaking_rate=speaking_rate,
                    ),
                )
                return AudioSegment.from_mp3(io.BytesIO(response.audio_content))
            except Exception as exc:
                logger.warning("[Audio] Google voice %s failed: %s", voice_name, exc)
        return None

    def _render_with_gtts(self, dialog: List[DialogTurn], run_id: str) -> Optional[Path]:
        mp3_path = self.output_dir / f"podcast_{run_id}.mp3"
        try:
            script = "\n\n".join(f"{speaker}: {text}" for speaker, text in dialog)
            gTTS(text=script, lang=self.language, slow=False).save(str(mp3_path))
            return mp3_path
        except Exception as exc:
            logger.warning("[Audio] gTTS generation failed: %s", exc)
            return None

    def _voice_candidates_for_provider(self, provider: str, speaker: str) -> List[str]:
        key = "male" if speaker == self.HOST_ROLE else "female"
        return list(self.podcast_config["voices"][provider].get(key, []))

    def _save_transcript(self, dialog: List[DialogTurn], output_path: Path) -> Optional[Path]:
        lines = ["PODCAST TRANSCRIPT", "=" * 80, ""]
        for speaker, text in dialog:
            lines.append(f"{speaker}:")
            lines.append(text)
            lines.append("")
            lines.append("-" * 40)
            lines.append("")
        try:
            output_path.write_text("\n".join(lines), encoding="utf-8")
            return output_path
        except Exception as exc:
            logger.error("[Transcript] Generation failed: %s", exc)
            return None

    def _clean_tts_text(self, text: str) -> str:
        cleaned = str(text or "")
        cleaned = cleaned.replace("•", " ")
        cleaned = cleaned.replace("—", ", ")
        cleaned = cleaned.replace("–", ", ")
        cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"[_#`]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _convert_mp3_to_wav(self, mp3_path: Path) -> Optional[Path]:
        if not self.has_pydub:
            return None
        try:
            wav_path = mp3_path.with_suffix(".wav")
            AudioSegment.from_mp3(str(mp3_path)).export(str(wav_path), format="wav")
            return wav_path
        except Exception as exc:
            logger.warning("[Audio] WAV conversion failed: %s", exc)
            return None

    def _embed_metadata(
        self,
        mp3_path: Path,
        title: str,
        episode_number: Optional[str] = None,
        description: Optional[str] = None,
        source_links: Optional[List[str]] = None,
    ) -> bool:
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
        except Exception:
            return False

    def _embed_wav_metadata(
        self,
        wav_path: Path,
        title: str,
        episode_number: Optional[str] = None,
        description: Optional[str] = None,
        source_links: Optional[List[str]] = None,
    ) -> bool:
        try:
            from src.audio_metadata import AudioMetadataEmbedder
            return AudioMetadataEmbedder.embed_audio_metadata(
                file_path=wav_path,
                title=title,
                episode_number=episode_number,
                date=datetime.utcnow().isoformat(),
                description=description,
                source_links=source_links or [],
            )
        except Exception:
            return False


class TranscriptGenerator:
    """Generate transcript from the same dialog used for podcast audio."""

    def generate_transcript(self, insights: List[Dict], output_path: str = "results/transcript.txt") -> bool:
        try:
            generator = PodcastGenerator(output_dir=str(Path(output_path).parent))
            dialog = generator.build_dialog(insights)
            return bool(generator._save_transcript(dialog, Path(output_path)))
        except Exception as exc:
            logger.error("[Transcript] Generation failed: %s", exc)
            return False


class AGIPodcastEngine:
    """Compatibility wrapper for callers that still import the legacy class."""

    def __init__(
        self,
        output_dir: Path,
        generate_wav: bool = True,
        google_client=None,
        has_gtts: bool = False,
        has_pydub: bool = False,
        language: str = "en",
    ):
        self.output_dir = output_dir
        self.generate_wav = generate_wav
        self.google_client = google_client
        self.has_gtts = has_gtts
        self.has_pydub = has_pydub
        self.language = language

    def generate(self, insights: List[Dict], run_id: str) -> Dict:
        generator = PodcastGenerator(
            output_dir=str(self.output_dir),
            generate_wav=self.generate_wav,
            language=self.language,
            narration_mode="agi",
        )
        if self.google_client is not None:
            generator.google_client = self.google_client
            generator.has_google_tts = True
        if self.has_gtts:
            generator.has_gtts = True
        if self.has_pydub:
            generator.has_pydub = True
        return generator.generate(
            insights,
            title="On-Device AI Intelligence Report",
            episode_number=run_id,
        )


__all__ = ["PodcastGenerator", "TranscriptGenerator", "AGIPodcastEngine"]
