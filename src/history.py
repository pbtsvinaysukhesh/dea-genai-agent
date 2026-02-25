"""
Enhanced History Manager for On-Device AI Memory Intelligence Agent
Improved context management, trend detection, and data persistence
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Enhanced history manager for tracking and analyzing research trends
    """
    
    def __init__(self, file_path: str = "data/history.json"):
        self.file_path = file_path
        self.ensure_dir()
    
    def ensure_dir(self):
        """Ensure data directory and history file exist"""
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            if not os.path.exists(self.file_path):
                with open(self.file_path, 'w') as f:
                    json.dump([], f)
                logger.info(f"Created new history file: {self.file_path}")
        except Exception as e:
            logger.error(f"Error creating history directory: {e}")
    
    def load_recent_context(self, days: int = 7) -> str:
        """
        Returns a summary string of insights from the last N days
        
        Args:
            days: Number of days to look back
            
        Returns:
            Formatted context string for AI analysis
        """
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            # Filter for recent items
            cutoff = datetime.now() - timedelta(days=days)
            recent_items = [
                item for item in data 
                if 'date' in item and datetime.fromisoformat(item['date']) > cutoff
            ]
            
            if not recent_items:
                logger.info("No recent context available")
                return ""
            
            # Sort by date (most recent first)
            recent_items.sort(key=lambda x: x['date'], reverse=True)
            
            # Format for AI prompt
            context_str = f"PREVIOUS RESEARCH CONTEXT (Last {days} Days):\n"
            context_str += "=" * 60 + "\n\n"
            
            # Group by platform
            mobile_items = [i for i in recent_items if i.get('platform') == 'Mobile']
            laptop_items = [i for i in recent_items if i.get('platform') == 'Laptop']
            
            # Add mobile trends
            if mobile_items:
                context_str += "📱 MOBILE TRENDS:\n"
                for item in mobile_items[:5]:  # Top 5
                    context_str += f"- [{item.get('date', 'Unknown')[:10]}] {item.get('title', 'Unknown')}\n"
                    context_str += f"  Memory: {item.get('memory_insight', 'N/A')}\n"
                    context_str += f"  Takeaway: {item.get('engineering_takeaway', 'N/A')}\n\n"
            
            # Add laptop trends
            if laptop_items:
                context_str += "💻 LAPTOP TRENDS:\n"
                for item in laptop_items[:5]:  # Top 5
                    context_str += f"- [{item.get('date', 'Unknown')[:10]}] {item.get('title', 'Unknown')}\n"
                    context_str += f"  Memory: {item.get('memory_insight', 'N/A')}\n"
                    context_str += f"  Takeaway: {item.get('engineering_takeaway', 'N/A')}\n\n"
            
            # Add observed trends
            trends = self._detect_trends(recent_items)
            if trends:
                context_str += "🔍 OBSERVED TRENDS:\n"
                for trend in trends:
                    context_str += f"- {trend}\n"
                context_str += "\n"
            
            logger.info(f"Loaded context with {len(recent_items)} recent articles")
            return context_str
            
        except Exception as e:
            logger.error(f"Error loading recent context: {e}")
            return ""
    
    def _detect_trends(self, items: List[Dict]) -> List[str]:
        """
        Detect trends from recent research
        
        Args:
            items: List of recent research items
            
        Returns:
            List of trend descriptions
        """
        trends = []
        
        try:
            # Count quantization methods
            quant_methods = {}
            for item in items:
                method = item.get('quantization_method', 'Unknown')
                if method != 'Unknown':
                    quant_methods[method] = quant_methods.get(method, 0) + 1
            
            if quant_methods:
                top_method = max(quant_methods, key=quant_methods.get)
                count = quant_methods[top_method]
                if count >= 3:
                    trends.append(f"{top_method} quantization appearing in {count} recent papers")
            
            # Count model types
            model_types = {}
            for item in items:
                mtype = item.get('model_type', 'Unknown')
                if mtype != 'Unknown':
                    model_types[mtype] = model_types.get(mtype, 0) + 1
            
            if model_types:
                top_type = max(model_types, key=model_types.get)
                count = model_types[top_type]
                if count >= 3:
                    trends.append(f"{top_type} models dominating research ({count} papers)")
            
            # Count high DRAM impact papers
            high_impact = len([i for i in items if i.get('dram_impact') == 'High'])
            if high_impact >= 3:
                trends.append(f"Increased focus on high DRAM impact solutions ({high_impact} papers)")
            
            # Detect memory size trends
            memory_sizes = []
            for item in items:
                insight = item.get('memory_insight', '')
                # Simple pattern matching for GB values
                if 'GB' in insight:
                    try:
                        # Extract number before GB
                        parts = insight.split('GB')
                        for part in parts[:-1]:
                            words = part.split()
                            if words:
                                try:
                                    size = float(words[-1])
                                    memory_sizes.append(size)
                                except:
                                    pass
                    except:
                        pass
            
            if len(memory_sizes) >= 3:
                avg_size = sum(memory_sizes) / len(memory_sizes)
                trends.append(f"Average memory footprint: {avg_size:.1f} GB across recent papers")
            
        except Exception as e:
            logger.error(f"Error detecting trends: {e}")
        
        return trends
    
    def save_insights(self, insights: List[Dict]):
        """
        Append new insights to the history file
        
        Args:
            insights: List of analyzed articles to save
        """
        try:
            # Load existing data
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
            else:
                data = []
            
            # Add timestamp to new items
            today = datetime.now().isoformat()
            for item in insights:
                # Only save if not already present
                if not any(existing.get('title') == item.get('title') for existing in data):
                    item['date'] = today
                    item['saved_at'] = today
                    data.append(item)
            
            # Keep file size manageable (keep last 200 items)
            if len(data) > 200:
                data = data[-200:]
            
            # Save back to file
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(insights)} insights to history")
            
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def get_statistics(self, days: int = 30) -> Dict:
        """
        Get statistics about historical data
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with statistics
        """
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            # Filter for time period
            cutoff = datetime.now() - timedelta(days=days)
            period_items = [
                item for item in data 
                if 'date' in item and datetime.fromisoformat(item['date']) > cutoff
            ]
            
            if not period_items:
                return {
                    'total_articles': 0,
                    'avg_relevance_score': 0,
                    'days_analyzed': days
                }
            
            # Calculate statistics
            total = len(period_items)
            avg_score = sum(i.get('relevance_score', 0) for i in period_items) / total
            
            # Count by platform
            platforms = {}
            for item in period_items:
                platform = item.get('platform', 'Unknown')
                platforms[platform] = platforms.get(platform, 0) + 1
            
            # Count by DRAM impact
            dram_impacts = {}
            for item in period_items:
                impact = item.get('dram_impact', 'Unknown')
                dram_impacts[impact] = dram_impacts.get(impact, 0) + 1
            
            return {
                'total_articles': total,
                'avg_relevance_score': round(avg_score, 1),
                'days_analyzed': days,
                'by_platform': platforms,
                'by_dram_impact': dram_impacts,
                'date_range': {
                    'start': cutoff.date().isoformat(),
                    'end': datetime.now().date().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}
    
    def export_csv(self, output_path: str, days: int = 30):
        """
        Export history to CSV file
        
        Args:
            output_path: Path for CSV output
            days: Number of days to export
        """
        try:
            import csv
            
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            # Filter for time period
            cutoff = datetime.now() - timedelta(days=days)
            period_items = [
                item for item in data 
                if 'date' in item and datetime.fromisoformat(item['date']) > cutoff
            ]
            
            if not period_items:
                logger.warning("No data to export")
                return
            
            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'date', 'title', 'source', 'relevance_score', 
                    'platform', 'model_type', 'dram_impact',
                    'memory_insight', 'engineering_takeaway', 'link'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for item in period_items:
                    row = {field: item.get(field, 'N/A') for field in fieldnames}
                    writer.writerow(row)
            
            logger.info(f"Exported {len(period_items)} articles to {output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
    
    def clear_old_data(self, days: int = 90):
        """
        Remove data older than specified days
        
        Args:
            days: Keep data from last N days
        """
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            cutoff = datetime.now() - timedelta(days=days)
            recent_data = [
                item for item in data 
                if 'date' in item and datetime.fromisoformat(item['date']) > cutoff
            ]
            
            removed = len(data) - len(recent_data)
            
            with open(self.file_path, 'w') as f:
                json.dump(recent_data, f, indent=2)
            
            logger.info(f"Cleared {removed} old entries, kept {len(recent_data)} recent entries")
            
        except Exception as e:
            logger.error(f"Error clearing old data: {e}")
    
    def search_history(self, keyword: str, days: int = 30) -> List[Dict]:
        """
        Search history for articles matching keyword
        
        Args:
            keyword: Search term
            days: Number of days to search
            
        Returns:
            List of matching articles
        """
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            # Filter by date
            cutoff = datetime.now() - timedelta(days=days)
            recent_items = [
                item for item in data 
                if 'date' in item and datetime.fromisoformat(item['date']) > cutoff
            ]
            
            # Search in title and memory_insight
            keyword_lower = keyword.lower()
            matches = [
                item for item in recent_items
                if keyword_lower in item.get('title', '').lower()
                or keyword_lower in item.get('memory_insight', '').lower()
                or keyword_lower in item.get('engineering_takeaway', '').lower()
            ]
            
            logger.info(f"Found {len(matches)} articles matching '{keyword}'")
            return matches
            
        except Exception as e:
            logger.error(f"Error searching history: {e}")
            return []