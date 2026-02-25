"""
Modern Email Formatter - Beautiful, Professional Design
Shows top 6 papers + executive summary
"""

import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportFormatter:
    """
    Modern, beautiful email report formatter
    """
    
    def build_html(self, insights: List[Dict]) -> str:
        """
        Build modern HTML report with top 6 papers + summary
        """
        if not insights:
            return self._build_empty_report()
        
        # Sort by relevance score
        sorted_insights = sorted(
            insights, 
            key=lambda x: x.get('relevance_score', 0), 
            reverse=True
        )
        
        # Get top 6
        top_papers = sorted_insights[:6]
        
        # Build report
        html = self._build_modern_header()
        html += self._build_executive_summary(sorted_insights)
        html += self._build_top_papers_section(top_papers)
        html += self._build_footer(len(sorted_insights))
        
        return html
    
    def _build_modern_header(self) -> str:
        """Modern header with gradient"""
        today = datetime.now().strftime("%B %d, %Y")
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>On-Device AI Intelligence Report</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f7fa;">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 20px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 32px; font-weight: 700; letter-spacing: -0.5px;">
            On-Device AI Intelligence
        </h1>
        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">
            {today}
        </p>
    </div>
    
    <!-- Content Container -->
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
"""
    
    def _build_executive_summary(self, all_insights: List[Dict]) -> str:
        """Executive summary with key metrics"""
        
        # Calculate statistics
        total = len(all_insights)
        avg_score = sum(i.get('relevance_score', 0) for i in all_insights) / total if total > 0 else 0
        
        # Count by platform
        platforms = {}
        for item in all_insights:
            platform = item.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1
        
        # Count by impact
        high_impact = len([i for i in all_insights if i.get('dram_impact') == 'High'])
        medium_impact = len([i for i in all_insights if i.get('dram_impact') == 'Medium'])
        
        # Top models
        model_types = {}
        for item in all_insights:
            mtype = item.get('model_type', 'Unknown')
            if mtype != 'Unknown':
                model_types[mtype] = model_types.get(mtype, 0) + 1
        
        top_model = max(model_types.items(), key=lambda x: x[1])[0] if model_types else 'N/A'
        
        return f"""
        <!-- Executive Summary Card -->
        <div style="background: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <h2 style="margin: 0 0 20px 0; font-size: 24px; color: #1a202c;">Executive Summary</h2>
            
            <div style="display: grid; gap: 15px;">
                <!-- Key Metrics -->
                <div style="background: #f7fafc; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
                    <div style="font-size: 14px; color: #718096; margin-bottom: 5px;">Total Papers Analyzed</div>
                    <div style="font-size: 28px; font-weight: 700; color: #2d3748;">{total}</div>
                </div>
                
                <div style="background: #f7fafc; padding: 20px; border-radius: 8px; border-left: 4px solid #48bb78;">
                    <div style="font-size: 14px; color: #718096; margin-bottom: 5px;">Average Relevance Score</div>
                    <div style="font-size: 28px; font-weight: 700; color: #2d3748;">{avg_score:.1f}/100</div>
                </div>
                
                <!-- Key Insights -->
                <div style="background: #edf2f7; padding: 20px; border-radius: 8px;">
                    <h3 style="margin: 0 0 15px 0; font-size: 16px; color: #2d3748;">Key Insights</h3>
                    <ul style="margin: 0; padding-left: 20px; color: #4a5568; line-height: 1.8;">
                        <li><strong>{platforms.get('Mobile', 0)}</strong> mobile-focused papers, <strong>{platforms.get('Laptop', 0)}</strong> laptop-focused</li>
                        <li><strong>{high_impact}</strong> high DRAM impact solutions identified</li>
                        <li>Dominant model type: <strong>{top_model}</strong></li>
                        <li><strong>{medium_impact}</strong> medium-impact memory optimizations</li>
                    </ul>
                </div>
            </div>
        </div>
"""
    
    def _build_top_papers_section(self, top_papers: List[Dict]) -> str:
        """Build top 6 papers section"""
        
        html = """
        <!-- Top Papers Section -->
        <div style="background: white; border-radius: 12px; padding: 30px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <h2 style="margin: 0 0 25px 0; font-size: 24px; color: #1a202c;">
                Top 6 Research Papers
            </h2>
"""
        
        for idx, paper in enumerate(top_papers, 1):
            html += self._build_paper_card(paper, idx)
        
        html += """
        </div>
"""
        return html
    
    def _build_paper_card(self, paper: Dict, rank: int) -> str:
        """Build individual paper card"""
        
        # Get data
        title = paper.get('title', 'Unknown')
        score = paper.get('relevance_score', 0)
        platform = paper.get('platform', 'Unknown')
        model_type = paper.get('model_type', 'Unknown')
        dram_impact = paper.get('dram_impact', 'Unknown')
        memory_insight = paper.get('memory_insight', 'No details available')
        takeaway = paper.get('engineering_takeaway', 'No takeaway available')
        link = paper.get('link', '#')
        source = paper.get('source', 'Unknown')
        
        # Color coding for score
        if score >= 90:
            score_color = '#48bb78'  # Green
            score_bg = '#f0fff4'
        elif score >= 70:
            score_color = '#4299e1'  # Blue
            score_bg = '#ebf8ff'
        else:
            score_color = '#ed8936'  # Orange
            score_bg = '#fffaf0'
        
        # Impact badge color
        impact_colors = {
            'High': '#48bb78',
            'Medium': '#ed8936',
            'Low': '#a0aec0'
        }
        impact_color = impact_colors.get(dram_impact, '#a0aec0')
        
        return f"""
            <!-- Paper Card #{rank} -->
            <div style="margin-bottom: 25px; padding-bottom: 25px; border-bottom: 1px solid #e2e8f0;">
                
                <!-- Rank Badge -->
                <div style="display: inline-block; background: linear-gradient(135deg, {score_color} 0%, {impact_color} 100%); color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-bottom: 12px;">
                    #{rank} • Score: {score}
                </div>
                
                <!-- Title -->
                <h3 style="margin: 10px 0; font-size: 18px; color: #2d3748; line-height: 1.4;">
                    <a href="{link}" style="color: #2d3748; text-decoration: none;">{title}</a>
                </h3>
                
                <!-- Metadata Badges -->
                <div style="margin: 12px 0; display: flex; gap: 8px; flex-wrap: wrap;">
                    <span style="background: #edf2f7; padding: 4px 10px; border-radius: 4px; font-size: 12px; color: #4a5568;">
                        {platform}
                    </span>
                    <span style="background: #edf2f7; padding: 4px 10px; border-radius: 4px; font-size: 12px; color: #4a5568;">
                        {model_type}
                    </span>
                    <span style="background: {score_bg}; color: {impact_color}; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                        {dram_impact} Impact
                    </span>
                    <span style="background: #edf2f7; padding: 4px 10px; border-radius: 4px; font-size: 12px; color: #718096;">
                        {source}
                    </span>
                </div>
                
                <!-- Memory Insight -->
                <div style="background: #f7fafc; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 3px solid {impact_color};">
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #718096; margin-bottom: 5px; font-weight: 600;">
                        Memory Insight
                    </div>
                    <div style="color: #2d3748; font-size: 14px; line-height: 1.6;">
                        {memory_insight}
                    </div>
                </div>
                
                <!-- Engineering Takeaway -->
                <div style="background: #fffaf0; padding: 15px; border-radius: 8px; border-left: 3px solid #ed8936;">
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #718096; margin-bottom: 5px; font-weight: 600;">
                        Engineering Takeaway
                    </div>
                    <div style="color: #2d3748; font-size: 14px; line-height: 1.6; font-weight: 500;">
                        {takeaway}
                    </div>
                </div>
            </div>
"""
    
    def _build_footer(self, total_count: int) -> str:
        """Modern footer"""
        
        return f"""
        <!-- Footer -->
        <div style="text-align: center; padding: 30px 20px; color: #718096; font-size: 13px;">
            <p style="margin: 0;">
                Showing top 6 of {total_count} total papers analyzed
            </p>
            <p style="margin: 10px 0 0 0;">
                On-Device AI Memory Intelligence Agent
            </p>
            <p style="margin: 5px 0 0 0; font-size: 11px; color: #a0aec0;">
                Powered by Multi-Model AI (Groq + Ollama + Gemini)
            </p>
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
        <p style="color: #4a5568;">No papers met the relevance threshold today.</p>
    </div>
</body>
</html>
"""
    
    def build_text_summary(self, insights: List[Dict]) -> str:
        """Plain text summary for logs"""
        if not insights:
            return "No relevant papers found."
        
        sorted_insights = sorted(
            insights,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )
        
        summary = f"\n{'='*60}\n"
        summary += f"ON-DEVICE AI INTELLIGENCE REPORT\n"
        summary += f"{'='*60}\n\n"
        summary += f"Total Papers: {len(insights)}\n"
        summary += f"Top 6 Papers:\n\n"
        
        for idx, paper in enumerate(sorted_insights[:6], 1):
            summary += f"{idx}. {paper.get('title', 'Unknown')}\n"
            summary += f"   Score: {paper.get('relevance_score', 0)} | "
            summary += f"Platform: {paper.get('platform', 'Unknown')} | "
            summary += f"Impact: {paper.get('dram_impact', 'Unknown')}\n\n"
        
        return summary