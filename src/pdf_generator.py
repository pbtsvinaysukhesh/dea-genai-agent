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

            story.extend(self._build_methodology_section(insights))
            story.append(PageBreak())

            story.extend(self._build_papers_section(insights))
            story.append(PageBreak())

            story.extend(self._build_trends_section(insights))
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

    def _build_methodology_section(self, insights: List[Dict]) -> List:
        """Build methodology and analysis process section"""
        story = []
        styles = getSampleStyleSheet()

        # Title
        story.append(Paragraph("Analysis Methodology", styles['Heading1']))
        story.append(Spacer(letter[0], 0.2 * inch))

        # Methodology text
        methodology_text = """
        <b>Hybrid Retrieval-Augmented Generation (RAG) Approach</b><br/><br/>
        This report uses an on-device AI intelligence system that combines multiple advanced techniques:
        <br/><br/>

        <b>Data Collection & Retrieval:</b><br/>
        Papers are collected from multiple sources (arXiv, RSS feeds, GitHub, Google Scholar) and indexed using hybrid search combining BM25 full-text search with semantic embeddings. Maximum Marginal Relevance (MMR) ranking ensures diverse, non-redundant results.
        <br/><br/>

        <b>AI Analysis Pipeline:</b><br/>
        The system uses an intelligent fallback chain for analysis:
        <br/>
        • <b>Groq API:</b> Primary provider (llama-3.1-8b, llama-3.3-70b, gemma2-9b)
        <br/>
        • <b>Ollama Local:</b> Fallback for local inference (gemma3:4b)
        <br/>
        • <b>Google Gemini:</b> Secondary fallback for API-based analysis
        <br/><br/>

        <b>Relevance Scoring System:</b><br/>
        Each paper receives a relevance score (0-100) based on:
        <br/>
        • 90+: Breakthrough with specific metrics (e.g., "reduces DRAM by 4GB")
        <br/>
        • 70-89: Solid on-device work with memory details
        <br/>
        • 50-69: Edge/mobile AI without detailed memory analysis
        <br/>
        • 30-49: Tangentially related (training-focused)
        <br/>
        • 0-29: Not relevant or cloud-only
        <br/><br/>

        <b>Analysis Focus Areas:</b><br/>
        • On-device inference optimization
        <br/>
        • Memory optimization (DRAM usage reduction)
        <br/>
        • Mobile and laptop deployment strategies
        <br/>
        • Model compression and quantization techniques
        <br/><br/>

        <b>Key Metrics Extracted:</b><br/>
        • relevance_score: Relevance to on-device AI (0-100)
        <br/>
        • platform: Target platform (Mobile, Laptop, Both)
        <br/>
        • model_type: Model class (LLM, Vision, Audio, Multimodal)
        <br/>
        • memory_insight: Specific memory optimization details
        <br/>
        • dram_impact: DRAM impact level (High, Medium, Low)
        <br/>
        • engineering_takeaway: Actionable implementation insight
        """

        story.append(Paragraph(methodology_text, styles['Normal']))
        story.append(Spacer(letter[0], 0.2 * inch))

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

            # Core metrics
            details = f"""
            <b>Relevance Score:</b> {score}/100 |
            <b>Platform:</b> {paper.get('platform', 'Unknown')} |
            <b>Model Type:</b> {paper.get('model_type', 'Unknown')} |
            <b>DRAM Impact:</b> {paper.get('dram_impact', 'Unknown')}
            """
            story.append(Paragraph(details, styles['Normal']))
            story.append(Spacer(letter[0], 0.15 * inch))

            # Memory insight
            memory = paper.get('memory_insight', 'N/A')
            story.append(Paragraph("<b>Memory Insight:</b>", styles['Normal']))
            story.append(Paragraph(str(memory), styles['Normal']))
            story.append(Spacer(letter[0], 0.1 * inch))

            # Platform-specific insight
            platform = paper.get('platform', 'Unknown')
            platform_text = self._get_platform_insight(platform)
            story.append(Paragraph(f"<b>Platform Implication ({platform}):</b>", styles['Normal']))
            story.append(Paragraph(platform_text, styles['Normal']))
            story.append(Spacer(letter[0], 0.1 * inch))

            # Model type insight
            model_type = paper.get('model_type', 'Unknown')
            model_text = self._get_model_type_insight(model_type)
            story.append(Paragraph(f"<b>Model Type Analysis ({model_type}):</b>", styles['Normal']))
            story.append(Paragraph(model_text, styles['Normal']))
            story.append(Spacer(letter[0], 0.1 * inch))

            # DRAM impact explanation
            dram = paper.get('dram_impact', 'Unknown')
            dram_text = self._get_dram_impact_explanation(dram)
            story.append(Paragraph(f"<b>DRAM Impact Assessment ({dram}):</b>", styles['Normal']))
            story.append(Paragraph(dram_text, styles['Normal']))
            story.append(Spacer(letter[0], 0.1 * inch))

            # Takeaway
            takeaway = paper.get('engineering_takeaway', 'N/A')
            story.append(Paragraph("<b>Engineering Takeaway:</b>", styles['Normal']))
            story.append(Paragraph(str(takeaway), styles['Normal']))
            story.append(Spacer(letter[0], 0.2 * inch))

        return story

    def _get_platform_insight(self, platform: str) -> str:
        """Get platform-specific insight text"""
        insights = {
            'Mobile': "Mobile deployment requires extreme optimization. Focus on reducing model size, quantization, and memory footprint. Latency and battery life are primary concerns.",
            'Laptop': "Laptop deployment allows more computational resources. Focus on throughput optimization and leveraging available CPU/GPU. Heat dissipation and power consumption matter.",
            'Both': "Cross-platform solution demonstrates broad applicability. Must balance mobile constraints with laptop optimization opportunities.",
            'Unknown': "Platform details not specified in analysis."
        }
        return insights.get(platform, insights['Unknown'])

    def _get_model_type_insight(self, model_type: str) -> str:
        """Get model type specific insight text"""
        insights = {
            'LLM': "Large Language Models require significant memory and compute. Focus on model quantization, distillation, and efficient attention mechanisms.",
            'Vision': "Vision models need optimized convolutions and spatial operations. Focus on architecture efficiency and input resolution optimization.",
            'Audio': "Audio models require real-time processing capability. Focus on streaming inference and low-latency operations.",
            'Multimodal': "Multimodal models integrate multiple input types. Focus on efficient fusion mechanisms and selective computation.",
            'Other': "Model type information provided for unique architecture.",
            'Unknown': "Model type details not specified in analysis."
        }
        return insights.get(model_type, insights['Unknown'])

    def _get_dram_impact_explanation(self, impact: str) -> str:
        """Get DRAM impact explanation"""
        impacts = {
            'High': "This research shows significant DRAM consumption. Critical for deployment on constrained devices. Requires optimization or device with sufficient memory.",
            'Medium': "Moderate DRAM usage. Feasible on mid-range devices with proper optimization. May require memory-efficient techniques.",
            'Low': "Minimal DRAM footprint. Suitable for memory-constrained devices. Demonstrates efficient implementation.",
            'Unknown': "DRAM impact not specified. Check memory_insight for details."
        }
        return impacts.get(impact, impacts['Unknown'])

    def _build_trends_section(self, insights: List[Dict]) -> List:
        """Build trends and conclusions section"""
        story = []
        styles = getSampleStyleSheet()

        story.append(Paragraph("Research Trends & Conclusions", styles['Heading1']))
        story.append(Spacer(letter[0], 0.2 * inch))

        # Analyze distributions
        platforms = {}
        model_types = {}
        dram_impacts = {}

        for paper in insights:
            platform = paper.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1

            model_type = paper.get('model_type', 'Unknown')
            model_types[model_type] = model_types.get(model_type, 0) + 1

            dram = paper.get('dram_impact', 'Unknown')
            dram_impacts[dram] = dram_impacts.get(dram, 0) + 1

        # Build trends text
        total = len(insights)
        avg_score = sum(i.get('relevance_score', 0) for i in insights) / total if total > 0 else 0

        trends_text = "<b>Research Landscape Overview:</b><br/>"
        trends_text += f"Total papers analyzed: {total} with average relevance score of {avg_score:.1f}/100<br/><br/>"

        trends_text += "<b>Platform Focus Distribution:</b><br/>"
        for platform, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            trends_text += f"• {platform}: {count} papers ({pct:.1f}%)<br/>"

        trends_text += "<br/><b>Model Type Distribution:</b><br/>"
        for model_type, count in sorted(model_types.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            trends_text += f"• {model_type}: {count} papers ({pct:.1f}%)<br/>"

        trends_text += "<br/><b>DRAM Impact Levels:</b><br/>"
        for impact, count in sorted(dram_impacts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            trends_text += f"• {impact}: {count} papers ({pct:.1f}%)<br/>"

        story.append(Paragraph(trends_text, styles['Normal']))
        story.append(Spacer(letter[0], 0.2 * inch))

        # Key findings
        findings_text = """
        <b>Key Research Findings:</b><br/><br/>

        <b>1. On-Device AI Strategy</b><br/>
        The research landscape shows a strong focus on making AI models practical for edge devices. Memory optimization and inference efficiency are central concerns across the research community.
        <br/><br/>

        <b>2. Platform-Specific Optimization</b><br/>
        Mobile and laptop deployments require different optimization strategies. Mobile demands extreme efficiency while laptops can leverage additional computational resources. Cross-platform solutions are emerging as important.
        <br/><br/>

        <b>3. Model Diversity</b><br/>
        The field spans multiple model types (LLMs, Vision, Audio, Multimodal). Each type presents unique optimization challenges requiring specialized techniques.
        <br/><br/>

        <b>4. DRAM Bottleneck</b><br/>
        Memory (DRAM) remains a critical constraint. Papers with high DRAM impact indicate significant challenges that require targeted optimization.
        <br/><br/>

        <b>Recommendations for Implementation:</b><br/>
        • Prioritize papers with highest relevance scores for immediate implementation<br/>
        • Consider platform-specific strategies for mobile vs. laptop deployments<br/>
        • Leverage model-specific optimization techniques identified in the research<br/>
        • Address DRAM constraints through quantization, distillation, or architectural changes<br/>
        • Monitor emerging trends in efficient model deployment
        """

        story.append(Paragraph(findings_text, styles['Normal']))
        story.append(Spacer(letter[0], 0.2 * inch))

        return story

    def _build_resources_section(self, insights: List[Dict]) -> List:
        """Build resources section with clickable links"""
        story = []
        styles = getSampleStyleSheet()

        story.append(Paragraph("Reference Resources", styles['Heading1']))
        story.append(Spacer(letter[0], 0.2 * inch))

        story.append(Paragraph("Top 10 Ranked Papers:", styles['Heading2']))
        story.append(Spacer(letter[0], 0.1 * inch))

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
        story.append(Spacer(letter[0], 0.3 * inch))

        # Add URL references if available
        story.append(Paragraph("Paper Sources and URLs:", styles['Heading2']))
        story.append(Spacer(letter[0], 0.1 * inch))

        urls_text = ""
        for idx, paper in enumerate(sorted_insights[:6], 1):
            title = paper.get('title', 'Unknown')
            url = paper.get('url', '')
            source = paper.get('source', 'Unknown')

            if url:
                urls_text += f"{idx}. <b>{title}</b><br/>"
                urls_text += f"   Source: {source} | URL: <u>{url}</u><br/><br/>"
            else:
                urls_text += f"{idx}. <b>{title}</b><br/>"
                urls_text += f"   Source: {source}<br/><br/>"

        if urls_text:
            story.append(Paragraph(urls_text, styles['Normal']))
        else:
            story.append(Paragraph("URL information not available for the top-ranked papers.", styles['Normal']))

        story.append(Spacer(letter[0], 0.2 * inch))

        return story


# Export for use
__all__ = ['PDFReportGenerator']
