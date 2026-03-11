"""
LLM-Powered Podcast Generator
Generates natural podcast dialogues using LLM intelligence to decide content dynamically.
The LLM analyzes papers and creates natural Explainer/Questioner conversation.
"""

import logging
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import os

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    logger.warning("[LLM Podcast] groq not installed. Install with: pip install groq")

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False
    logger.warning("[LLM Podcast] gtts not installed. Install with: pip install gtts")


class LLMPodcastGenerator:
    """
    Generate podcasts using LLM for natural, intelligent conversation.
    The LLM decides what's important from the papers and creates dynamic dialogue.
    Not a script reader - actual intelligent discussion.
    """

    def __init__(
        self,
        output_dir: str = "results/podcasts",
        greeting: Optional[str] = None,
        llm_model: str = "mixtral-8x7b-32768",  # GROQ fast model
    ):
        """Initialize LLM podcast generator

        Args:
            output_dir: Directory for output files
            greeting: Custom greeting phrase
            llm_model: GROQ model to use
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.greeting = greeting or "Hello everyone, welcome to Vinay's DEA podcast."
        self.llm_model = llm_model

        # Initialize GROQ client
        self.groq_client = None
        self.has_groq = HAS_GROQ

        if HAS_GROQ:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                try:
                    self.groq_client = Groq(api_key=api_key)
                    logger.info("[LLM Podcast] GROQ client initialized for natural dialogue")
                except Exception as e:
                    logger.warning(f"[LLM Podcast] GROQ init failed: {e}")
                    self.has_groq = False
            else:
                logger.warning("[LLM Podcast] GROQ_API_KEY not set")
                self.has_groq = False

        self.has_gtts = HAS_GTTS

    def generate(
        self,
        insights: List[Dict],
        title: str = "On-Device AI Intelligence Report",
        episode_number: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Optional[Path]]:
        """Generate podcast using LLM-generated natural dialogue

        Args:
            insights: List of paper/insight dictionaries
            title: Podcast episode title
            episode_number: Episode ID or number
            description: Episode description

        Returns:
            Dict with 'mp3' path (or None if not generated)
        """
        if not insights:
            logger.warning("[LLM Podcast] No insights to generate podcast")
            return {"mp3": None}

        if not self.has_groq:
            logger.error("[LLM Podcast] GROQ not available - cannot generate")
            return {"mp3": None}

        try:
            # Generate podcast script using LLM
            logger.info(f"[LLM Podcast] Generating natural dialogue from {len(insights)} papers...")
            dialog = self._generate_natural_dialog(insights, title)

            if not dialog:
                logger.error("[LLM Podcast] Failed to generate dialogue")
                return {"mp3": None}

            # Convert dialogue to audio using gTTS
            logger.info(f"[LLM Podcast] Converting {len(dialog)} dialogue segments to audio...")
            mp3_path = self._dialog_to_audio(dialog)

            if not mp3_path:
                logger.error("[LLM Podcast] Failed to generate audio")
                return {"mp3": None}

            logger.info(f"[LLM Podcast] Podcast generated: {mp3_path}")
            return {"mp3": mp3_path}

        except Exception as e:
            logger.error(f"[LLM Podcast] Generation failed: {e}")
            return {"mp3": None}

    def _generate_natural_dialog(self, insights: List[Dict], title: str) -> Optional[List[Tuple[str, str]]]:
        """
        Use LLM to analyze papers and generate natural podcast dialogue.
        LLM decides what's important, what to discuss, what to skip.
        """
        try:
            # Prepare paper summary for LLM
            papers_json = json.dumps(insights, indent=2)

            prompt = f"""You are creating a professional podcast on on-device AI optimization.

Podcast Title: {title}
Greeting: {self.greeting}

You have {len(insights)} research papers to discuss. Analyze them intelligently and decide:
- What are the MOST important findings?
- What insights are most actionable?
- What should be highlighted vs what's less important?
- Create a NATURAL conversation, not a boring script

Generate a podcast dialogue between:
- Explainer (male voice): Expert analyst discussing the research
- Questioner (female voice): Intelligent questioner asking relevant follow-ups

RULES:
1. Start with the greeting
2. Discuss papers naturally - NOT reading a list
3. Skip trivial or redundant points
4. Focus on actionable insights
5. Make it sound like a REAL conversation with natural pauses
6. Include transitions and real dialogue patterns
7. Discuss 4-6 MOST important papers in depth (not all papers)
8. End with key takeaways
9. Keep total dialogue segments to 25-35 exchanges (for reasonable audio length)

Papers to analyze:
{papers_json}

Generate the podcast as a JSON array of dialogue exchanges:
[
  {{"speaker": "Explainer", "text": "greeting here"}},
  {{"speaker": "Questioner", "text": "response"}},
  ...
]

Make it CONVERSATIONAL and INTELLIGENT. LLM should decide what's worth discussing.
Return ONLY the JSON array, no other text."""

            logger.debug(f"[LLM Podcast] Sending prompt to GROQ...")

            # Call GROQ to generate dialogue
            message = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.llm_model,
                temperature=0.7,
                max_tokens=4000,
            )

            response_text = message.choices[0].message.content.strip()

            # Parse JSON response
            try:
                dialogue_list = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                start = response_text.find('[')
                end = response_text.rfind(']') + 1
                if start >= 0 and end > start:
                    dialogue_list = json.loads(response_text[start:end])
                else:
                    logger.error("[LLM Podcast] Could not parse LLM response as JSON")
                    return None

            # Convert to list of (speaker, text) tuples
            dialog = []
            for item in dialogue_list:
                if isinstance(item, dict) and "speaker" in item and "text" in item:
                    dialog.append((item["speaker"], item["text"]))
                else:
                    logger.warning(f"[LLM Podcast] Unexpected dialogue format: {item}")

            logger.info(f"[LLM Podcast] Generated {len(dialog)} dialogue segments")
            return dialog if dialog else None

        except Exception as e:
            logger.error(f"[LLM Podcast] Dialogue generation failed: {e}")
            return None

    def _dialog_to_audio(self, dialog: List[Tuple[str, str]]) -> Optional[Path]:
        """Convert dialogue to audio file"""
        if not self.has_gtts:
            logger.error("[LLM Podcast] gTTS not available for audio generation")
            return None

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            mp3_path = self.output_dir / f"podcast_{timestamp}.mp3"

            # Combine all dialogue into one script
            full_script = ""
            for speaker, text in dialog:
                full_script += f"{speaker}: {text}\n\n"

            logger.info(f"[LLM Podcast] Generating audio from dialogue ({len(full_script)} chars)...")

            # Generate speech using gTTS
            tts = gTTS(text=full_script, lang="en", slow=False)
            tts.save(str(mp3_path))

            logger.info(f"[LLM Podcast] Audio saved: {mp3_path}")
            return mp3_path

        except Exception as e:
            logger.error(f"[LLM Podcast] Audio generation failed: {e}")
            return None


__all__ = ['LLMPodcastGenerator']
