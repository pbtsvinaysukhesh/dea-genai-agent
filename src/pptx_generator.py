"""
PowerPoint Presentation Generator
Creates professional slides with analysis, findings, and resources
"""

import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.dml.color import RGBColor
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False
    logger.warning("[PPT] python-pptx not installed. Install with: pip install python-pptx")


class PowerPointGenerator:
    """
    Generate professional PowerPoint presentations with:
    - Title slide
    - Executive summary
    - Key findings
    - Paper summaries (6 slides)
    - Trend analysis
    - Call-to-action
    """

    def __init__(self, output_path: str = "results/report.pptx"):
        """Initialize PowerPoint generator"""
        self.output_path = output_path
        self.has_pptx = HAS_PPTX
        self.colors = {
            'primary': RGBColor(102, 126, 234),      # #667eea
            'secondary': RGBColor(118, 75, 162),     # #764ba2
            'heading': RGBColor(26, 32, 44),         # #1a202c
            'text': RGBColor(45, 55, 72),            # #2d3748
            'accent': RGBColor(237, 137, 54),        # #ed8936
            'white': RGBColor(255, 255, 255),
        }

        if not self.has_pptx:
            logger.error("[PPT] python-pptx required. Install: pip install python-pptx")

    def generate(self, insights: List[Dict]) -> bool:
        """
        Generate comprehensive PowerPoint presentation
        Returns: True if successful
        """
        if not self.has_pptx:
            logger.error("[PPT] Cannot generate - python-pptx not installed")
            return False

        if not insights:
            logger.warning("[PPT] No insights to generate presentation")
            return False

        try:
            prs = Presentation()
            prs.slide_width = Inches(10)
            prs.slide_height = Inches(7.5)

            # Build slides
            self._add_title_slide(prs, insights)
            self._add_executive_summary_slide(prs, insights)
            self._add_key_findings_slide(prs, insights)

            # Sort by relevance
            sorted_insights = sorted(
                insights,
                key=lambda x: x.get('relevance_score', 0),
                reverse=True
            )

            # Add paper slides (top 6)
            for idx, paper in enumerate(sorted_insights[:6], 1):
                self._add_paper_slide(prs, paper, idx)

            self._add_trends_slide(prs, insights)
            self._add_resources_slide(prs, sorted_insights[:10])
            self._add_cta_slide(prs)

            # Save
            prs.save(self.output_path)
            logger.info(f"[PPT] Presentation generated: {self.output_path}")
            return True

        except Exception as e:
            logger.error(f"[PPT] Generation failed: {e}")
            return False

    def _add_title_slide(self, prs: Presentation, insights: List[Dict]):
        """Add title slide"""
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.colors['primary']

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(9), Inches(1))
        title_frame = title_box.text_frame
        title_frame.text = "On-Device AI Intelligence"
        title_frame.paragraphs[0].font.size = Pt(54)
        title_frame.paragraphs[0].font.bold = True
        title_frame.paragraphs[0].font.color.rgb = self.colors['white']

        # Subtitle
        subtitle_box = slide.shapes.add_textbox(Inches(0.5), Inches(3.7), Inches(9), Inches(1))
        subtitle_frame = subtitle_box.text_frame
        subtitle_frame.text = f"Research Intelligence Report • {datetime.now().strftime('%B %d, %Y')}"
        subtitle_frame.paragraphs[0].font.size = Pt(24)
        subtitle_frame.paragraphs[0].font.color.rgb = self.colors['white']

        # Footer
        footer_box = slide.shapes.add_textbox(Inches(0.5), Inches(6.5), Inches(9), Inches(0.8))
        footer_frame = footer_box.text_frame
        footer_frame.text = f"{len(insights)} Papers Analyzed • Hybrid RAG + Multi-Model AI"
        footer_frame.paragraphs[0].font.size = Pt(16)
        footer_frame.paragraphs[0].font.color.rgb = RGBColor(200, 200, 200)

    def _add_executive_summary_slide(self, prs: Presentation, insights: List[Dict]):
        """Add executive summary slide"""
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title = slide.shapes.title
        title.text = "Executive Summary"
        title.text_frame.paragraphs[0].font.size = Pt(44)
        title.text_frame.paragraphs[0].font.color.rgb = self.colors['primary']

        # Calculate metrics
        total = len(insights)
        avg_score = sum(i.get('relevance_score', 0) for i in insights) / total if total > 0 else 0

        platforms = {}
        for item in insights:
            platform = item.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1

        high_impact = len([i for i in insights if i.get('dram_impact') == 'High'])

        # Content
        left = Inches(0.5)
        top = Inches(1.8)
        width = Inches(9)
        height = Inches(5)

        text_box = slide.shapes.add_textbox(left, top, width, height)
        text_frame = text_box.text_frame
        text_frame.word_wrap = True

        metrics = [
            f"📊 Total Papers: {total}",
            f"⭐ Average Score: {avg_score:.1f}/100",
            f"📱 Mobile Papers: {platforms.get('Mobile', 0)}",
            f"💻 Laptop Papers: {platforms.get('Laptop', 0)}",
            f"🔥 High Impact: {high_impact} papers",
        ]

        for idx, metric in enumerate(metrics):
            if idx > 0:
                text_frame.add_paragraph()
            p = text_frame.paragraphs[idx]
            p.text = metric
            p.font.size = Pt(24)
            p.font.color.rgb = self.colors['text']
            p.space_before = Pt(12)

    def _add_key_findings_slide(self, prs: Presentation, insights: List[Dict]):
        """Add key findings slide"""
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title = slide.shapes.title
        title.text = "Key Findings"
        title.text_frame.paragraphs[0].font.size = Pt(44)
        title.text_frame.paragraphs[0].font.color.rgb = self.colors['primary']

        # Techniques
        techniques = {}
        for item in insights:
            tech = item.get('quantization_method', 'N/A')
            if tech != 'N/A':
                techniques[tech] = techniques.get(tech, 0) + 1

        top_techniques = sorted(techniques.items(), key=lambda x: x[1], reverse=True)[:3]

        # Content
        left = Inches(0.5)
        top = Inches(1.8)
        width = Inches(9)
        height = Inches(5)

        text_box = slide.shapes.add_textbox(left, top, width, height)
        text_frame = text_box.text_frame
        text_frame.word_wrap = True

        findings = ["🎯 Top Optimization Techniques:"]
        for tech, count in top_techniques:
            findings.append(f"   • {tech}: {count} papers")

        findings.append("")
        findings.append("💡 Key Insights:")
        findings.append("   • Strong focus on DRAM bandwidth optimization")
        findings.append("   • Quantization methods are trending across platforms")
        findings.append("   • Mobile inference optimization is a primary concern")

        for idx, finding in enumerate(findings):
            if idx > 0:
                text_frame.add_paragraph()
            p = text_frame.paragraphs[idx]
            p.text = finding
            p.font.size = Pt(18)
            p.font.color.rgb = self.colors['text']
            p.space_before = Pt(6)

    def _add_paper_slide(self, prs: Presentation, paper: Dict, rank: int):
        """Add paper detail slide"""
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title = slide.shapes.title
        title.text = f"#{rank}: {paper.get('title', 'Unknown')[:50]}"
        title.text_frame.paragraphs[0].font.size = Pt(32)
        title.text_frame.paragraphs[0].font.color.rgb = self.colors['primary']

        # Content
        left = Inches(0.5)
        top = Inches(1.5)
        width = Inches(9)
        height = Inches(5.5)

        text_box = slide.shapes.add_textbox(left, top, width, height)
        text_frame = text_box.text_frame
        text_frame.word_wrap = True

        score = paper.get('relevance_score', 0)
        platform = paper.get('platform', 'Unknown')
        model_type = paper.get('model_type', 'Unknown')
        dram_impact = paper.get('dram_impact', 'Unknown')
        memory_insight = paper.get('memory_insight', 'N/A')
        takeaway = paper.get('engineering_takeaway', 'N/A')

        content = [
            f"Score: {score}/100 | Platform: {platform} | Model: {model_type}",
            f"DRAM Impact: {dram_impact}",
            "",
            "💾 Memory Insight:",
            str(memory_insight)[:200],
            "",
            "⚙️ Engineering Takeaway:",
            str(takeaway)[:200],
        ]

        for idx, line in enumerate(content):
            if idx > 0:
                text_frame.add_paragraph()
            p = text_frame.paragraphs[idx]
            p.text = line
            p.font.size = Pt(16)
            p.font.color.rgb = self.colors['text']
            if idx in [0, 2, 4, 6]:  # Headers
                p.font.bold = True
            p.space_before = Pt(4)

    def _add_trends_slide(self, prs: Presentation, insights: List[Dict]):
        """Add trends slide"""
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title = slide.shapes.title
        title.text = "Research Trends"
        title.text_frame.paragraphs[0].font.size = Pt(44)
        title.text_frame.paragraphs[0].font.color.rgb = self.colors['primary']

        # Sources
        sources = {}
        for item in insights:
            source = item.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1

        top_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)[:3]

        # Content
        left = Inches(0.5)
        top = Inches(1.8)
        width = Inches(9)
        height = Inches(5)

        text_box = slide.shapes.add_textbox(left, top, width, height)
        text_frame = text_box.text_frame
        text_frame.word_wrap = True

        trends = ["📈 Most Active Sources:"]
        for source, count in top_sources:
            trends.append(f"   • {source}: {count} papers")

        trends.append("")
        trends.append("🔮 Emerging Patterns:")
        trends.append("   • Increasing focus on edge device optimization")
        trends.append("   • Memory efficiency is the top priority")
        trends.append("   • Cross-platform compatibility studies growing")

        for idx, trend in enumerate(trends):
            if idx > 0:
                text_frame.add_paragraph()
            p = text_frame.paragraphs[idx]
            p.text = trend
            p.font.size = Pt(18)
            p.font.color.rgb = self.colors['text']
            p.space_before = Pt(6)

    def _add_resources_slide(self, prs: Presentation, resources: List[Dict]):
        """Add resources slide"""
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title = slide.shapes.title
        title.text = "Reference Resources"
        title.text_frame.paragraphs[0].font.size = Pt(44)
        title.text_frame.paragraphs[0].font.color.rgb = self.colors['primary']

        # Content
        left = Inches(0.5)
        top = Inches(1.8)
        width = Inches(9)
        height = Inches(5)

        text_box = slide.shapes.add_textbox(left, top, width, height)
        text_frame = text_box.text_frame
        text_frame.word_wrap = True

        for idx, resource in enumerate(resources):
            if idx > 0:
                text_frame.add_paragraph()
            title_text = resource.get('title', 'Unknown')[:60]
            source = resource.get('source', '')
            score = resource.get('relevance_score', 0)

            p = text_frame.paragraphs[idx]
            p.text = f"{idx + 1}. {title_text} ({source}) - {score}/100"
            p.font.size = Pt(14)
            p.font.color.rgb = self.colors['text']
            p.space_before = Pt(6)

    def _add_cta_slide(self, prs: Presentation):
        """Add call-to-action slide"""
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.colors['secondary']

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2), Inches(9), Inches(1.5))
        title_frame = title_box.text_frame
        title_frame.text = "Next Steps"
        title_frame.paragraphs[0].font.size = Pt(54)
        title_frame.paragraphs[0].font.bold = True
        title_frame.paragraphs[0].font.color.rgb = self.colors['white']

        # Action items
        actions_box = slide.shapes.add_textbox(Inches(0.5), Inches(3.8), Inches(9), Inches(3))
        actions_frame = actions_box.text_frame
        actions_frame.word_wrap = True

        actions = [
            "📄 Download the full PDF report",
            "🎤 Listen to the audio podcast",
            "📊 View detailed analysis dashboard",
            "🔗 Access all paper resources",
        ]

        for idx, action in enumerate(actions):
            if idx > 0:
                actions_frame.add_paragraph()
            p = actions_frame.paragraphs[idx]
            p.text = action
            p.font.size = Pt(20)
            p.font.color.rgb = self.colors['white']
            p.space_before = Pt(10)


__all__ = ['PowerPointGenerator']
