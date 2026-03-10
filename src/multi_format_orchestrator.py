"""
Multi-Format Report Orchestrator
Generates all report formats in one go: Email, PDF, PPT, Podcast, Transcript, Summary (Text + JSON)
Includes automatic backup and versioning of existing reports.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MultiFormatReportOrchestrator:
    """
    Generate comprehensive reports in multiple formats simultaneously:
    - Enhanced HTML Email
    - PDF Document (with clickable links and all sources)
    - PowerPoint Presentation (with paginated sources slides)
    - Podcast/Audio (with greeting, WAV support, metadata)
    - Summary Documents (Text + JSON with confidence levels)
    - Automatic backup and versioning of existing reports
    """

    def __init__(self, output_dir: str = None):
        """Initialize orchestrator with backup system integration"""
        # Use PathConfig if available, otherwise use provided or default
        try:
            from .path_config import PathConfig
            self.path_config = PathConfig.get_instance()
            self.output_dir = self.path_config.get_report_dir()
            self.backup_dir = self.path_config.get_backup_dir()
            self.podcast_dir = self.path_config.get_podcast_dir()
        except ImportError:
            self.path_config = None
            self.output_dir = Path(output_dir or "results/reports")
            self.backup_dir = Path("results/backup")
            self.podcast_dir = Path("results/podcasts")

        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.podcast_dir.mkdir(parents=True, exist_ok=True)

        # Initialize backup manager
        try:
            from .backup_manager import BackupManager
            self.backup_manager = BackupManager(self.backup_dir)
            logger.info("[Orchestrator] BackupManager initialized")
        except ImportError:
            self.backup_manager = None
            logger.warning("[Orchestrator] BackupManager not available")

        # Import generators
        try:
            from .enhanced_formatter import EnhancedReportFormatter
            self.email_formatter = EnhancedReportFormatter()
        except ImportError:
            self.email_formatter = None
            logger.warning("[Orchestrator] enhanced_formatter not available")

        try:
            from .pdf_generator import PDFReportGenerator
            self.pdf_gen = PDFReportGenerator(
                output_path=str(self.output_dir / "report.pdf")
            )
        except ImportError:
            self.pdf_gen = None
            logger.warning("[Orchestrator] pdf_generator not available")

        try:
            from .pptx_generator import PowerPointGenerator
            self.pptx_gen = PowerPointGenerator(
                output_path=str(self.output_dir / "report.pptx")
            )
        except ImportError:
            self.pptx_gen = None
            logger.warning("[Orchestrator] pptx_generator not available")

        try:
            from .podcast_generator import PodcastGenerator, TranscriptGenerator
            # Get greeting from PathConfig if available
            greeting = None
            if self.path_config:
                greeting = self.path_config.get_podcast_greeting()

            self.podcast_gen = PodcastGenerator(
                output_dir=str(self.podcast_dir),
                greeting=greeting,
                intro_music_path=self.path_config.get_podcast_intro_music() if self.path_config else None,
                outro_music_path=self.path_config.get_podcast_outro_music() if self.path_config else None,
            )
            self.transcript_gen = TranscriptGenerator()
        except ImportError:
            self.podcast_gen = None
            self.transcript_gen = None
            logger.warning("[Orchestrator] podcast_generator not available")

        # Initialize JSON summary generator
        try:
            from .summary_generator import JsonSummaryGenerator
            self.summary_gen = JsonSummaryGenerator()
        except ImportError:
            self.summary_gen = None
            logger.warning("[Orchestrator] summary_generator not available")

        # Initialize source link processor
        try:
            from .source_link_processor import SourceLinkProcessor
            self.source_processor = SourceLinkProcessor()
        except ImportError:
            self.source_processor = None
            logger.warning("[Orchestrator] source_link_processor not available")

    def generate_all(self, insights: List[Dict]) -> Dict[str, bool]:
        """
        Generate all report formats with automatic backup and versioning
        Returns: Dict with format -> success status
        """
        if not insights:
            logger.warning("[Orchestrator] No insights to generate reports")
            return {}

        results = {}

        logger.info(f"[Orchestrator] Starting multi-format report generation for {len(insights)} papers...")

        # BACKUP EXISTING REPORTS (before generating new ones)
        if self.backup_manager:
            files_to_backup = {
                "pdf": self.output_dir / "report.pdf",
                "pptx": self.output_dir / "report.pptx",
                "podcast_mp3": self.podcast_dir / "podcast.mp3",
                "podcast_wav": self.podcast_dir / "podcast.wav",
                "summary_json": self.output_dir / "summary.json",
                "summary_txt": self.output_dir / "summary.txt",
            }
            backup_results = self.backup_manager.backup_and_version(files_to_backup)
            logger.info(f"[Orchestrator] Backed up {sum(1 for v in backup_results.values() if v)} existing files")

        # 1. Enhanced Email
        if self.email_formatter:
            try:
                html = self.email_formatter.build_html(insights)
                email_path = self.output_dir / "email_report.html"
                email_path.write_text(html, encoding='utf-8')
                logger.info(f"[Orchestrator] ✅ Email report: {email_path}")
                results['email'] = True
            except Exception as e:
                logger.error(f"[Orchestrator] ❌ Email generation failed: {e}")
                results['email'] = False
        else:
            results['email'] = False

        # 2. PDF Report
        if self.pdf_gen:
            try:
                success = self.pdf_gen.generate(insights)
                if success:
                    logger.info(f"[Orchestrator] ✅ PDF report: {self.output_dir / 'report.pdf'}")
                results['pdf'] = success
            except Exception as e:
                logger.error(f"[Orchestrator] ❌ PDF generation failed: {e}")
                results['pdf'] = False
        else:
            results['pdf'] = False

        # 3. PowerPoint Presentation
        if self.pptx_gen:
            try:
                success = self.pptx_gen.generate(insights)
                if success:
                    logger.info(f"[Orchestrator] ✅ PowerPoint: {self.output_dir / 'report.pptx'}")
                results['pptx'] = success
            except Exception as e:
                logger.error(f"[Orchestrator] ❌ PPT generation failed: {e}")
                results['pptx'] = False
        else:
            results['pptx'] = False

        # 4. Podcast Audio (MP3 + WAV)
        if self.podcast_gen:
            try:
                podcast_results = self.podcast_gen.generate(
                    insights=insights,
                    title="On-Device AI Intelligence Report",
                    episode_number=datetime.now().strftime("%Y-%m-%d"),
                    description=f"Intelligence report on {len(insights)} papers",
                    source_links=[p.get('link') for p in insights if p.get('link')]
                )
                if podcast_results.get("mp3"):
                    logger.info(f"[Orchestrator] ✅ Podcast MP3: {podcast_results['mp3']}")
                if podcast_results.get("wav"):
                    logger.info(f"[Orchestrator] ✅ Podcast WAV: {podcast_results['wav']}")
                results['podcast'] = bool(podcast_results.get("mp3"))
            except Exception as e:
                logger.error(f"[Orchestrator] ❌ Podcast generation failed: {e}")
                results['podcast'] = False
        else:
            results['podcast'] = False

        # 5. Transcript
        if self.transcript_gen:
            try:
                success = self.transcript_gen.generate_transcript(
                    insights,
                    output_path=str(self.output_dir / "transcript.txt")
                )
                if success:
                    logger.info(f"[Orchestrator] ✅ Transcript: {self.output_dir / 'transcript.txt'}")
                results['transcript'] = success
            except Exception as e:
                logger.error(f"[Orchestrator] ❌ Transcript generation failed: {e}")
                results['transcript'] = False
        else:
            results['transcript'] = False

        # 6. Summary Documents (Text + JSON)
        try:
            summary_txt_path = self.output_dir / "summary.txt"
            summary_json_path = self.output_dir / "summary.json"

            self._generate_summary(insights, str(summary_txt_path), str(summary_json_path))
            logger.info(f"[Orchestrator] ✅ Text Summary: {summary_txt_path}")
            logger.info(f"[Orchestrator] ✅ JSON Summary: {summary_json_path}")
            results['summary'] = True
        except Exception as e:
            logger.error(f"[Orchestrator] ❌ Summary generation failed: {e}")
            results['summary'] = False

        # Print overview
        logger.info("[Orchestrator] ==================== REPORT GENERATION COMPLETE ====================")
        logger.info("[Orchestrator] Generated formats:")
        for fmt, success in results.items():
            status = "✅" if success else "❌"
            logger.info(f"  {status} {fmt.upper()}")
        logger.info("[Orchestrator] ========================================================================")

        return results

    def _generate_summary(self, insights: List[Dict], txt_path: str, json_path: str = None):
        """Generate text and JSON summaries"""
        import json

        # Generate text summary
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ON-DEVICE AI INTELLIGENCE REPORT - SUMMARY\n")
            f.write(f"Generated: {datetime.now().strftime('%B %d, %Y')}\n")
            f.write("Confidence: Based on primary sources\n")
            f.write("=" * 80 + "\n\n")

            # Metrics
            f.write("EXECUTIVE SUMMARY\n")
            f.write("-" * 80 + "\n")
            total = len(insights)
            avg_score = sum(i.get('relevance_score', 0) for i in insights) / total if total else 0

            f.write(f"Total Papers Analyzed: {total}\n")
            f.write(f"Average Relevance Score: {avg_score:.1f}/100\n\n")

            # Platform breakdown
            platforms = {}
            for item in insights:
                platform = item.get('platform', 'Unknown')
                platforms[platform] = platforms.get(platform, 0) + 1

            f.write("Platform Breakdown:\n")
            for platform, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  • {platform}: {count} papers\n")
            f.write("\n")

            # Impact analysis
            high_impact = len([i for i in insights if i.get('dram_impact') == 'High'])
            medium_impact = len([i for i in insights if i.get('dram_impact') == 'Medium'])
            low_impact = len([i for i in insights if i.get('dram_impact') == 'Low'])

            f.write("Impact Distribution:\n")
            f.write(f"  • High Impact: {high_impact} papers\n")
            f.write(f"  • Medium Impact: {medium_impact} papers\n")
            f.write(f"  • Low Impact: {low_impact} papers\n\n")

            # Top papers
            sorted_insights = sorted(
                insights,
                key=lambda x: x.get('relevance_score', 0),
                reverse=True
            )

            f.write("TOP 6 PAPERS\n")
            f.write("-" * 80 + "\n\n")

            for idx, paper in enumerate(sorted_insights[:6], 1):
                title = paper.get('title', 'Unknown')
                score = paper.get('relevance_score', 0)
                platform = paper.get('platform', 'Unknown')
                impact = paper.get('dram_impact', 'Unknown')
                source = paper.get('source', 'Unknown')
                memory = paper.get('memory_insight', 'N/A')
                takeaway = paper.get('engineering_takeaway', 'N/A')

                f.write(f"#{idx} {title}\n")
                f.write(f"  Source: {source} | Score: {score}/100\n")
                f.write(f"  Platform: {platform} | Impact: {impact}\n")
                f.write(f"  Memory Insight: {memory}\n")
                f.write(f"  Takeaway: {takeaway}\n")
                f.write("\n")

            # Key findings
            f.write("KEY FINDINGS\n")
            f.write("-" * 80 + "\n")

            techniques = {}
            for item in insights:
                tech = item.get('quantization_method', 'N/A')
                if tech != 'N/A':
                    techniques[tech] = techniques.get(tech, 0) + 1

            f.write("Top Techniques:\n")
            for tech, count in sorted(techniques.items(), key=lambda x: x[1], reverse=True)[:3]:
                f.write(f"  • {tech}: {count} papers\n")
            f.write("\n")

            f.write("=" * 80 + "\n")
            f.write("For more details, see the full reports in other formats.\n")
            f.write("=" * 80 + "\n")


__all__ = ['MultiFormatReportOrchestrator']
