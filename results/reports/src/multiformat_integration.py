"""
Multi-Format Report Integration
Seamlessly integrates multi-format report generation into the email pipeline
"""

import logging
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MultiFormatReportIntegration:
    """
    Integration layer for multi-format report generation
    Generates email, PDF, PowerPoint, Podcast, and other formats
    """

    def __init__(self, output_dir: str = "results/reports"):
        """Initialize integration"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Import orchestrator
        try:
            from .multi_format_orchestrator import MultiFormatReportOrchestrator
            self.orchestrator = MultiFormatReportOrchestrator(output_dir=output_dir)
            self.available = True
            logger.info("[MultiFormat] Orchestrator initialized successfully")
        except ImportError as e:
            self.orchestrator = None
            self.available = False
            logger.warning(f"[MultiFormat] Orchestrator not available: {e}")

    def generate_multiformat_reports(self, insights: List[Dict]) -> Tuple[str, Dict]:
        """
        Generate all report formats for the given insights

        Args:
            insights: List of paper insights to report on

        Returns:
            Tuple of (email_html_content, generation_results_dict)
        """
        if not self.available or not self.orchestrator:
            logger.error("[MultiFormat] Orchestrator not available")
            return "", {}

        if not insights:
            logger.warning("[MultiFormat] No insights to generate reports")
            return "", {}

        logger.info(f"[MultiFormat] Generating multi-format reports for {len(insights)} papers...")

        try:
            # Generate all formats
            results = self.orchestrator.generate_all(insights)

            # Get email HTML content
            email_html = self._read_email_report()

            # Log summary
            logger.info("[MultiFormat] ==================== GENERATION SUMMARY ====================")
            for fmt, success in results.items():
                status = "✅" if success else "❌"
                logger.info(f"  {status} {fmt.upper()}")
            logger.info("[MultiFormat] ================================================================")

            return email_html, results

        except Exception as e:
            logger.error(f"[MultiFormat] Generation failed: {e}")
            return "", {}

    def _read_email_report(self) -> str:
        """Read the generated email HTML report"""
        email_path = os.path.join(self.output_dir, "email_report.html")

        try:
            if os.path.exists(email_path):
                with open(email_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"[MultiFormat] Email report not found: {email_path}")
                return ""
        except Exception as e:
            logger.error(f"[MultiFormat] Failed to read email report: {e}")
            return ""

    def get_attachment_paths(self) -> List[str]:
        """Get paths of all generated report files (for email attachments)"""
        attachments = []

        files_to_attach = [
            "report.pdf",
            "report.pptx",
            "podcast.mp3",
            "transcript.txt",
            "summary.txt"
        ]

        for filename in files_to_attach:
            filepath = os.path.join(self.output_dir, filename)
            if os.path.exists(filepath):
                attachments.append(filepath)
                logger.info(f"[MultiFormat] Will attach: {filename}")

        return attachments

    def get_generation_stats(self) -> Dict:
        """Get statistics about generated reports"""
        stats = {
            'output_directory': self.output_dir,
            'generated_files': {},
            'total_size_mb': 0.0
        }

        if not os.path.exists(self.output_dir):
            return stats

        try:
            for filename in os.listdir(self.output_dir):
                filepath = os.path.join(self.output_dir, filename)
                if os.path.isfile(filepath):
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    stats['generated_files'][filename] = f"{size_mb:.2f} MB"
                    stats['total_size_mb'] += size_mb
        except Exception as e:
            logger.error(f"[MultiFormat] Failed to get stats: {e}")

        return stats


def generate_multiformat_email_report(papers: List[Dict], output_dir: str = "results/reports") -> Tuple[str, List[str], Dict]:
    """
    Convenience function to generate multi-format reports and return email content + attachments

    Usage in main.py:
        email_html, attachments, results = generate_multiformat_email_report(unsent_papers)
        if email_html and mailer:
            mailer.send(email_html, attachments=attachments)

    Args:
        papers: List of paper insights
        output_dir: Directory to save reports

    Returns:
        Tuple of (email_html, attachment_paths, generation_results)
    """
    integration = MultiFormatReportIntegration(output_dir=output_dir)

    # Generate all formats
    email_html, results = integration.generate_multiformat_reports(papers)

    # Get attachments
    attachments = integration.get_attachment_paths()

    # Log summary
    stats = integration.get_generation_stats()
    logger.info(f"\n[MultiFormat] Generation complete:")
    logger.info(f"  Email HTML: {len(email_html)} bytes")
    logger.info(f"  Attachments: {len(attachments)} files")
    logger.info(f"  Total Size: {stats['total_size_mb']:.2f} MB")

    return email_html, attachments, results


__all__ = ['MultiFormatReportIntegration', 'generate_multiformat_email_report']
