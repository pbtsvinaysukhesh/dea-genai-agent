"""
Enhanced Email Formatter with Rich Content
Generates beautiful emails with 6+ papers, detailed insights, and embedded resources
"""

import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class EnhancedReportFormatter:
    """
    Premium email formatter with:
    - 6+ papers with detailed analysis
    - Clickable resource links
    - Executive summary
    - Key findings
    - Trend analysis
    - Call-to-action buttons
    """

    def build_html(self, insights: List[Dict]) -> str:
        """Build comprehensive HTML report with 6+ papers"""
        if not insights:
            return self._build_empty_report()

        # Sort by relevance score
        sorted_insights = sorted(
            insights,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )

        # Get top 6+ papers
        top_papers = sorted_insights[:6]

        # Build report sections
        html = self._build_header()
        html += self._build_executive_summary(sorted_insights)
        html += self._build_key_findings(sorted_insights)
        html += self._build_trend_analysis(sorted_insights)
        html += self._build_papers_section(top_papers)
        html += self._build_resources_section(top_papers)
        html += self._build_cta_section()
        html += self._build_footer(len(sorted_insights))

        return html

    def _build_header(self) -> str:
        """Modern header with branding"""
        today = datetime.now().strftime("%B %d, %Y")

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>On-Device AI Intelligence Report</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #2d3748;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 50px 30px;
            text-align: center;
            color: white;
        }}
        .header h1 {{
            margin: 0;
            font-size: 36px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        .header p {{
            margin: 10px 0 0 0;
            font-size: 16px;
            opacity: 0.95;
        }}
        .content-area {{
            padding: 40px 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 24px;
            font-weight: 700;
            color: #1a202c;
            margin: 0 0 20px 0;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        .card {{
            background: #f7fafc;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }}
        .paper-card {{
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: box-shadow 0.3s ease;
        }}
        .paper-card:hover {{
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }}
        .paper-rank {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .paper-title {{
            font-size: 18px;
            font-weight: 600;
            color: #2d3748;
            margin: 10px 0;
            line-height: 1.4;
        }}
        .paper-title a {{
            color: #2d3748;
            text-decoration: none;
            border-bottom: 2px solid #667eea;
        }}
        .paper-title a:hover {{
            color: #667eea;
        }}
        .meta-badges {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 15px 0;
        }}
        .badge {{
            background: #edf2f7;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            color: #4a5568;
            font-weight: 500;
        }}
        .badge.high {{
            background: #f0fff4;
            color: #22543d;
            border: 1px solid #9ae6b4;
        }}
        .insight-box {{
            background: #fffaf0;
            border-left: 4px solid #ed8936;
            padding: 15px;
            border-radius: 8px;
            margin: 12px 0;
        }}
        .memory-box {{
            background: #edf2f7;
            border-left: 4px solid #667eea;
            padding: 15px;
            border-radius: 8px;
            margin: 12px 0;
        }}
        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 28px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            margin: 8px 8px 8px 0;
            transition: transform 0.2s ease;
        }}
        .cta-button:hover {{
            transform: translateY(-2px);
        }}
        .resource-link {{
            display: inline-block;
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
            padding: 2px 0;
            border-bottom: 1px solid #667eea;
            margin: 4px 4px 4px 0;
        }}
        .resource-link:hover {{
            color: #764ba2;
        }}
        .stat-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }}
        .stat-item {{
            background: white;
            border: 1px solid #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 28px;
            font-weight: 700;
            color: #667eea;
            margin: 0;
        }}
        .stat-label {{
            font-size: 12px;
            color: #718096;
            margin-top: 5px;
        }}
        .footer {{
            background: #f7fafc;
            padding: 30px;
            text-align: center;
            color: #718096;
            font-size: 13px;
            border-top: 1px solid #e2e8f0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🚀 On-Device AI Intelligence Report</h1>
            <p>{today}</p>
        </div>

        <!-- Content -->
        <div class="content-area">
"""

    def _build_executive_summary(self, all_insights: List[Dict]) -> str:
        """Executive summary with key metrics"""
        total = len(all_insights)
        avg_score = sum(i.get('relevance_score', 0) for i in all_insights) / total if total > 0 else 0

        # Platform breakdown
        platforms = {}
        for item in all_insights:
            platform = item.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1

        # Impact analysis
        high_impact = len([i for i in all_insights if i.get('dram_impact') == 'High'])
        medium_impact = len([i for i in all_insights if i.get('dram_impact') == 'Medium'])
        low_impact = len([i for i in all_insights if i.get('dram_impact') == 'Low'])

        # Model types
        model_types = {}
        for item in all_insights:
            mtype = item.get('model_type', 'Unknown')
            if mtype != 'Unknown':
                model_types[mtype] = model_types.get(mtype, 0) + 1

        top_model = max(model_types.items(), key=lambda x: x[1])[0] if model_types else 'N/A'

        # Sources
        sources = {}
        for item in all_insights:
            source = item.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1

        return f"""
            <!-- Executive Summary -->
            <div class="section">
                <h2 class="section-title">📊 Executive Summary</h2>

                <div class="stat-row">
                    <div class="stat-item">
                        <div class="stat-number">{total}</div>
                        <div class="stat-label">Papers Analyzed</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{avg_score:.1f}</div>
                        <div class="stat-label">Avg. Relevance Score</div>
                    </div>
                </div>

                <div class="card">
                    <h3 style="margin: 0 0 15px 0; color: #2d3748;">Key Metrics</h3>
                    <ul style="margin: 0; padding-left: 20px; line-height: 2;">
                        <li><strong>{platforms.get('Mobile', 0)}</strong> mobile papers | <strong>{platforms.get('Laptop', 0)}</strong> laptop papers</li>
                        <li><strong>{high_impact}</strong> high impact | <strong>{medium_impact}</strong> medium impact | <strong>{low_impact}</strong> low impact</li>
                        <li>Leading model type: <strong>{top_model}</strong></li>
                        <li>Sources: {', '.join([f"<strong>{k}</strong> ({v})" for k, v in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:3]])}</li>
                    </ul>
                </div>
            </div>
"""

    def _build_key_findings(self, insights: List[Dict]) -> str:
        """Key findings and insights"""
        # Find most mentioned techniques
        techniques = {}
        for item in insights:
            tech = item.get('quantization_method', 'N/A')
            if tech != 'N/A':
                techniques[tech] = techniques.get(tech, 0) + 1

        top_techniques = sorted(techniques.items(), key=lambda x: x[1], reverse=True)[:3]

        # Find DRAM insights
        dram_mentions = [i for i in insights if 'dram' in str(i.get('memory_insight', '')).lower()]

        return f"""
            <!-- Key Findings -->
            <div class="section">
                <h2 class="section-title">🎯 Key Findings</h2>

                <div class="card">
                    <h3 style="margin: 0 0 12px 0; color: #2d3748;">Top Optimization Techniques</h3>
                    <ul style="margin: 0; padding-left: 20px; line-height: 2;">
                        {chr(10).join([f"<li><strong>{tech}</strong> ({count} papers)</li>" for tech, count in top_techniques])}
                    </ul>
                </div>

                <div class="card">
                    <h3 style="margin: 0 0 12px 0; color: #2d3748;">DRAM Optimization Focus</h3>
                    <p style="margin: 0;">{len(dram_mentions)} papers specifically address DRAM bandwidth and memory optimization challenges.</p>
                </div>
            </div>
"""

    def _build_trend_analysis(self, insights: List[Dict]) -> str:
        """Trend analysis"""
        # Active researchers/sources
        sources = {}
        for item in insights:
            source = item.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1

        top_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)[:3]

        return f"""
            <!-- Trends -->
            <div class="section">
                <h2 class="section-title">📈 Research Trends</h2>

                <div class="card">
                    <h3 style="margin: 0 0 12px 0; color: #2d3748;">Most Active Sources</h3>
                    <ul style="margin: 0; padding-left: 20px; line-height: 2;">
                        {chr(10).join([f"<li><strong>{source}</strong>: {count} papers</li>" for source, count in top_sources])}
                    </ul>
                </div>

                <div class="insight-box">
                    <strong>💡 Insight:</strong> The focus on edge AI and mobile inference continues to grow, with emphasis on memory efficiency and latency reduction.
                </div>
            </div>
"""

    def _build_papers_section(self, top_papers: List[Dict]) -> str:
        """Build detailed papers section"""
        html = """
            <!-- Top Papers -->
            <div class="section">
                <h2 class="section-title">📚 Top 6 Research Papers</h2>
"""

        for idx, paper in enumerate(top_papers, 1):
            html += self._build_enhanced_paper_card(paper, idx)

        html += """
            </div>
"""
        return html

    def _build_enhanced_paper_card(self, paper: Dict, rank: int) -> str:
        """Build enhanced paper card with all details"""
        # Extract data
        title = paper.get('title', 'Unknown')
        score = paper.get('relevance_score', 0)
        platform = paper.get('platform', 'Unknown')
        model_type = paper.get('model_type', 'Unknown')
        dram_impact = paper.get('dram_impact', 'Unknown')
        memory_insight = paper.get('memory_insight', 'No details')
        takeaway = paper.get('engineering_takeaway', 'No takeaway')
        link = paper.get('link', '#')
        source = paper.get('source', 'Unknown')
        summary = paper.get('summary', '')[:200]
        quantization = paper.get('quantization_method', 'N/A')

        # Score badge color
        if score >= 90:
            score_class = 'high'
        elif score >= 70:
            score_class = 'medium'
        else:
            score_class = 'low'

        return f"""
            <div class="paper-card">
                <div class="paper-rank">#{rank} • Score: {score}/100 • {source}</div>

                <h3 class="paper-title">
                    <a href="{link}" target="_blank">{title}</a>
                </h3>

                <div class="meta-badges">
                    <span class="badge">{platform}</span>
                    <span class="badge">{model_type}</span>
                    <span class="badge high">{dram_impact} Impact</span>
                    <span class="badge">{quantization}</span>
                </div>

                <p style="color: #4a5568; font-size: 14px; line-height: 1.6; margin: 12px 0;">
                    {summary}
                </p>

                <div class="memory-box">
                    <strong style="color: #667eea;">💾 Memory Insight:</strong><br>
                    {memory_insight}
                </div>

                <div class="insight-box">
                    <strong style="color: #ed8936;">⚙️ Engineering Takeaway:</strong><br>
                    {takeaway}
                </div>

                <div style="margin-top: 12px;">
                    <a href="{link}" target="_blank" class="cta-button">Read Full Paper →</a>
                </div>
            </div>
"""

    def _build_resources_section(self, top_papers: List[Dict]) -> str:
        """Build clickable resources section"""
        html = """
            <!-- Resources -->
            <div class="section">
                <h2 class="section-title">🔗 Quick Resource Links</h2>

                <div class="card">
                    <h3 style="margin: 0 0 15px 0; color: #2d3748;">Paper Links</h3>
"""

        for idx, paper in enumerate(top_papers, 1):
            title = paper.get('title', 'Paper')[:60]
            link = paper.get('link', '#')
            source = paper.get('source', '')

            html += f"""
                    <div style="margin: 10px 0;">
                        <a href="{link}" target="_blank" class="resource-link">
                            {idx}. {title}... ({source})
                        </a>
                    </div>
"""

        html += """
                </div>
            </div>
"""
        return html

    def _build_cta_section(self) -> str:
        """Call-to-action section"""
        return """
            <!-- CTA -->
            <div class="section">
                <h2 class="section-title">💼 Next Steps</h2>

                <div class="card">
                    <p style="margin: 0 0 15px 0;">Want more details? Here are your options:</p>
                    <div>
                        <a href="#" class="cta-button">📄 Download PDF Report</a>
                        <a href="#" class="cta-button">🎤 Listen to Podcast</a>
                        <a href="#" class="cta-button">📊 View Full Presentation</a>
                    </div>
                </div>
            </div>
"""

    def _build_footer(self, total_count: int) -> str:
        """Footer"""
        return f"""
            <!-- Footer -->
            <div class="footer">
                <p style="margin: 0;">Showing top 6 of {total_count} papers analyzed</p>
                <p style="margin: 10px 0 0 0;">🤖 Powered by Hybrid RAG + Multi-Model AI (Groq, Ollama, Gemini)</p>
                <p style="margin: 5px 0 0 0;">On-Device AI Memory Intelligence Agent</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    def _build_empty_report(self) -> str:
        """Empty state"""
        today = datetime.now().strftime("%B %d, %Y")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>No Results</title>
</head>
<body style="font-family: Arial, sans-serif; padding: 40px; background: #f5f7fa;">
    <div style="max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; text-align: center;">
        <h2 style="color: #2d3748;">No Relevant Papers Found</h2>
        <p style="color: #718096;">{today}</p>
        <p style="color: #4a5568;">No papers met the relevance threshold today. Check back tomorrow!</p>
    </div>
</body>
</html>
"""
