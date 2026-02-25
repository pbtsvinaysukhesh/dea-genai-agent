"""
PDF Report Generator
Creates professional PDF reports with all details, clickable links, and rich formatting
"""

import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("[PDF] reportlab not installed. Install with: pip install reportlab")


class PDFReportGenerator:
    """
    Generate professional PDF reports with:
    - Title page
    - Executive summary
    - Key findings
    - Detailed paper analysis
    - Resource links
    - Trend analysis
    """

    def __init__(self, output_path: str = "results/report.pdf"):
        """Initialize PDF generator"""
        self.output_path = output_path
        self.has_reportlab = HAS_REPORTLAB

        if not self.has_reportlab:
            logger.error("[PDF] reportlab required. Install: pip install reportlab")

    def generate(self, insights: List[Dict]) -> bool:
        """
        Generate comprehensive PDF report
        Returns: True if successful
        """
        if not self.has_reportlab:
            logger.error("[PDF] Cannot generate PDF - reportlab not installed")
            return False

        if not insights:
            logger.warning("[PDF] No insights to generate PDF")
            return False

        try:
            # Create PDF
            doc = SimpleDocTemplate(self.output_path, pagesize=letter)
            story = []

            # Build document
            story.extend(self._build_title_page(insights))
            story.append(PageBreak())

            story.extend(self._build_executive_summary(insights))
            story.append(PageBreak())

            story.extend(self._build_papers_section(insights))
            story.append(PageBreak())

            story.extend(self._build_resources_section(insights))

            # Build PDF
            doc.build(story)
            logger.info(f"[PDF] Report generated: {self.output_path}")
            return True

        except Exception as e:
            logger.error(f"[PDF] Generation failed: {e}")
            return False

    def _build_title_page(self, insights: List[Dict]) -> List:
        """Build title page"""
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=36,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        story.append(Spacer(letter[0], 2 * inch))
        story.append(Paragraph("On-Device AI Intelligence Report", title_style))
        story.append(Spacer(letter[0], 0.3 * inch))

        # Date
        today = datetime.now().strftime("%B %d, %Y")
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        story.append(Paragraph(today, date_style))
        story.append(Spacer(letter[0], 0.5 * inch))

        # Summary
        total = len(insights)
        avg_score = sum(i.get('relevance_score', 0) for i in insights) / total if total > 0 else 0

        summary_text = f"""
        <b>{total} Papers Analyzed</b><br/>
        Average Relevance Score: {avg_score:.1f}/100<br/>
        Generated using Hybrid RAG + Multi-Model AI
        """

        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#4a5568')
        )
        story.append(Paragraph(summary_text, summary_style))

        return story

    def _build_executive_summary(self, insights: List[Dict]) -> List:
        """Build executive summary section"""
        story = []
        styles = getSampleStyleSheet()

        # Title
        story.append(Paragraph("Executive Summary", styles['Heading1']))
        story.append(Spacer(letter[0], 0.2 * inch))

        # Metrics
        total = len(insights)
        avg_score = sum(i.get('relevance_score', 0) for i in insights) / total if total > 0 else 0

        platforms = {}
        for item in insights:
            platform = item.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1

        high_impact = len([i for i in insights if i.get('dram_impact') == 'High'])
        medium_impact = len([i for i in insights if i.get('dram_impact') == 'Medium'])

        summary_data = [
            ['Metric', 'Value'],
            ['Total Papers Analyzed', str(total)],
            ['Average Relevance Score', f'{avg_score:.1f}/100'],
            ['Mobile-Focused Papers', str(platforms.get('Mobile', 0))],
            ['Laptop-Focused Papers', str(platforms.get('Laptop', 0))],
            ['High DRAM Impact Papers', str(high_impact)],
            ['Medium Impact Papers', str(medium_impact)],
        ]

        table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))

        story.append(table)
        story.append(Spacer(letter[0], 0.3 * inch))

        return story

    def _build_papers_section(self, insights: List[Dict]) -> List:
        """Build papers section with detailed analysis"""
        story = []
        styles = getSampleStyleSheet()

        # Sort by relevance
        sorted_insights = sorted(
            insights,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )

        # Get top 6
        top_papers = sorted_insights[:6]

        story.append(Paragraph("Top 6 Research Papers", styles['Heading1']))
        story.append(Spacer(letter[0], 0.2 * inch))

        for idx, paper in enumerate(top_papers, 1):
            # Paper header
            title = paper.get('title', 'Unknown')
            score = paper.get('relevance_score', 0)
            source = paper.get('source', 'Unknown')

            header = f"#{idx} • {title} ({source})"
            story.append(Paragraph(header, styles['Heading2']))

            # Details
            details = f"""
            <b>Score:</b> {score}/100 |
            <b>Platform:</b> {paper.get('platform', 'Unknown')} |
            <b>Model Type:</b> {paper.get('model_type', 'Unknown')} |
            <b>DRAM Impact:</b> {paper.get('dram_impact', 'Unknown')}
            """
            story.append(Paragraph(details, styles['Normal']))
            story.append(Spacer(letter[0], 0.1 * inch))

            # Memory insight
            memory = paper.get('memory_insight', 'N/A')
            story.append(Paragraph("<b>💾 Memory Insight:</b>", styles['Normal']))
            story.append(Paragraph(str(memory), styles['Normal']))
            story.append(Spacer(letter[0], 0.1 * inch))

            # Takeaway
            takeaway = paper.get('engineering_takeaway', 'N/A')
            story.append(Paragraph("<b>⚙️ Engineering Takeaway:</b>", styles['Normal']))
            story.append(Paragraph(str(takeaway), styles['Normal']))
            story.append(Spacer(letter[0], 0.2 * inch))

        return story

    def _build_resources_section(self, insights: List[Dict]) -> List:
        """Build resources section with clickable links"""
        story = []
        styles = getSampleStyleSheet()

        story.append(Paragraph("Reference Resources", styles['Heading1']))
        story.append(Spacer(letter[0], 0.2 * inch))

        # Sort by relevance
        sorted_insights = sorted(
            insights,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )

        resources_data = [['#', 'Title', 'Source', 'Score']]

        for idx, paper in enumerate(sorted_insights[:10], 1):
            title = paper.get('title', 'Unknown')[:40]
            source = paper.get('source', 'Unknown')
            score = paper.get('relevance_score', 0)

            resources_data.append([str(idx), title, source, str(score)])

        table = Table(resources_data, colWidths=[0.4 * inch, 3 * inch, 1.2 * inch, 0.8 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))

        story.append(table)

        return story


# Export for use
__all__ = ['PDFReportGenerator']
