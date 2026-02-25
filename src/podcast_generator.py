"""
Podcast/Audio Generator
Creates audio files with narration and summaries (like NotebookLM)
"""

import logging
from typing import List, Dict
from datetime import datetime
import io

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


class PodcastGenerator:
    """
    Generate audio podcasts with:
    - Professional narration
    - Executive summary
    - Paper summaries
    - Key insights
    - Engaging transitions
    - Multiple voices/styles
    """

    def __init__(self, output_path: str = "results/podcast.mp3", language: str = "en"):
        """Initialize podcast generator"""
        self.output_path = output_path
        self.language = language
        self.has_gtts = HAS_GTTS
        self.has_pydub = HAS_PYDUB

        if not self.has_gtts:
            logger.error("[Audio] gTTS required. Install: pip install gtts")

    def generate(self, insights: List[Dict]) -> bool:
        """
        Generate podcast audio file
        Returns: True if successful
        """
        if not self.has_gtts:
            logger.error("[Audio] Cannot generate - gtts not installed")
            return False

        if not insights:
            logger.warning("[Audio] No insights to generate podcast")
            return False

        try:
            # Build script
            script = self._build_podcast_script(insights)

            # Generate audio
            logger.info(f"[Audio] Generating podcast from script ({len(script)} characters)...")

            tts = gTTS(text=script, lang=self.language, slow=False)
            tts.save(self.output_path)

            logger.info(f"[Audio] Podcast generated: {self.output_path}")
            return True

        except Exception as e:
            logger.error(f"[Audio] Generation failed: {e}")
            return False

    def _build_podcast_script(self, insights: List[Dict]) -> str:
        """Build podcast script as natural speech"""
        today = datetime.now().strftime("%B %d, %Y")

        script = f"""
Welcome to the On-Device AI Intelligence Report podcast for {today}.

I'm your AI research analyst, and today we're reviewing the latest research in on-device AI and mobile optimization.

Let me start with a quick executive summary. We've analyzed {len(insights)} papers this week.
The average relevance score is {sum(i.get('relevance_score', 0) for i in insights) / len(insights):.1f} out of 100.

"""

        # Add metrics
        platforms = {}
        for item in insights:
            platform = item.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1

        script += f"We found {platforms.get('Mobile', 0)} mobile-focused papers and {platforms.get('Laptop', 0)} laptop-focused papers. "

        high_impact = len([i for i in insights if i.get('dram_impact') == 'High'])
        script += f"Notable is that {high_impact} papers addressed high DRAM impact challenges.\n\n"

        # Add key findings
        script += """
Now, let's dive into the key findings this week.

The three most mentioned optimization techniques are:
"""

        techniques = {}
        for item in insights:
            tech = item.get('quantization_method', 'N/A')
            if tech != 'N/A':
                techniques[tech] = techniques.get(tech, 0) + 1

        top_techniques = sorted(techniques.items(), key=lambda x: x[1], reverse=True)[:3]
        for idx, (tech, count) in enumerate(top_techniques, 1):
            script += f"{idx}. {tech}, mentioned in {count} papers. "

        script += "\n\n"

        # Add top papers summaries
        sorted_insights = sorted(
            insights,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )

        script += "Let me now walk you through our top research papers for the week.\n\n"

        for idx, paper in enumerate(sorted_insights[:6], 1):
            title = paper.get('title', 'Unknown')
            score = paper.get('relevance_score', 0)
            platform = paper.get('platform', 'Unknown')
            insight = paper.get('memory_insight', 'No details')
            takeaway = paper.get('engineering_takeaway', 'No takeaway')

            script += f"Paper {idx}: {title}\n"
            script += f"Score: {score} out of 100. This paper focuses on {platform.lower()} platforms.\n"
            script += f"Key insight: {insight}\n"
            script += f"Engineering takeaway: {takeaway}\n\n"

        # Add closing
        script += """
That wraps up our top papers for this week.

The main trends we're seeing include:
- Continued focus on DRAM bandwidth optimization
- Growing interest in mixed-precision quantization
- Increasing adoption of neural architecture search for efficient models
- Cross-platform deployment becoming more important

For the complete analysis, check out the full PDF report and resource links.

This has been the On-Device AI Intelligence Report podcast.
Thank you for listening, and I'll see you next week with fresh research insights!
"""

        return script

    def generate_conversation(self, insights: List[Dict], output_path: str = None) -> bool:
        """
        Generate a multi-voice conversation/interview style podcast
        (Requires more advanced setup)
        """
        if output_path is None:
            output_path = self.output_path

        try:
            # This would require additional setup with voice cloning
            # For now, we'll generate a narrative style podcast
            logger.info("[Audio] Generating conversation-style podcast...")

            script = self._build_conversation_script(insights)
            tts = gTTS(text=script, lang=self.language, slow=False)
            tts.save(output_path)

            logger.info(f"[Audio] Conversation podcast generated: {output_path}")
            return True

        except Exception as e:
            logger.error(f"[Audio] Conversation generation failed: {e}")
            return False

    def _build_conversation_script(self, insights: List[Dict]) -> str:
        """Build a conversational podcast script"""
        script = """
Host: Welcome back to the AI Research Briefing. I'm your host. Today we're talking about
the latest on-device AI research with our AI analyst. Welcome back!

AI Analyst: Thanks for having me! It's great to be here.

Host: So, what's the big story this week in on-device AI?

AI Analyst: Well, there's a lot of exciting progress. We've seen a real focus on
making large language models run efficiently on phones and laptops.

Host: That's fascinating. What are the biggest challenges researchers are tackling?

AI Analyst: The main challenge is DRAM bandwidth. Modern models need to move
a lot of data, and that's often the bottleneck on mobile devices.

Host: And what solutions are they finding?

AI Analyst: Quantization is huge - reducing the precision of weights and activations.
We're also seeing more research into efficient architectures specifically designed for edge devices.

Host: That sounds promising. Are there any particularly interesting papers this week?

AI Analyst: Absolutely. Let me highlight our top discoveries...

"""

        sorted_insights = sorted(
            insights,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )

        for idx, paper in enumerate(sorted_insights[:3], 1):
            title = paper.get('title', 'Unknown')
            insight = paper.get('memory_insight', 'interesting findings')

            script += f"\nAI Analyst: Paper {idx} shows {insight}.\n"
            script += f"Host: That's really interesting! Tell us more about the specifics.\n"
            script += f"AI Analyst: Well, the key innovation is...\n"

        script += """

Host: This is really valuable stuff. Where can people access these papers?

AI Analyst: Everything is available in our full report. Links, PDFs, abstracts - all there.

Host: Great! Thanks for breaking this down for us. And folks, remember to check out
the full resources. Until next time, keep innovating!
"""

        return script


class TranscriptGenerator:
    """
    Generate transcripts of podcast or analysis
    """

    def __init__(self):
        """Initialize transcript generator"""
        pass

    def generate_transcript(self, insights: List[Dict], output_path: str = "results/transcript.txt") -> bool:
        """
        Generate text transcript of podcast
        """
        try:
            podcast_gen = PodcastGenerator()
            script = podcast_gen._build_podcast_script(insights)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("ON-DEVICE AI INTELLIGENCE REPORT PODCAST TRANSCRIPT\n")
                f.write("=" * 80 + "\n\n")
                f.write(script)
                f.write("\n\n" + "=" * 80 + "\n")
                f.write("END OF TRANSCRIPT\n")
                f.write("=" * 80 + "\n")

            logger.info(f"[Transcript] Generated: {output_path}")
            return True

        except Exception as e:
            logger.error(f"[Transcript] Generation failed: {e}")
            return False


__all__ = ['PodcastGenerator', 'TranscriptGenerator']
