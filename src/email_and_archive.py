"""
Email Tracker & Results Archiver
- Tracks which papers have been emailed
- Only sends NEW papers (never re-sends)
- Archives ALL analysis results
"""

import os
import json
import logging
from typing import Dict, List, Set
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class EmailTracker:
    """
    Tracks which papers have been sent via email
    Ensures no paper is sent twice
    """
    
    def __init__(self, tracker_file: str = "data/email_sent_tracker.json"):
        self.tracker_file = tracker_file
        
        # Create data directory
        os.makedirs(os.path.dirname(tracker_file), exist_ok=True)
        
        # Load sent papers
        self.sent_papers = self._load_sent_papers()
        
        logger.info(f"[EmailTracker] Loaded {len(self.sent_papers)} previously sent papers")
    
    def _load_sent_papers(self) -> Set[str]:
        """Load IDs of papers already sent"""
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('sent_paper_ids', []))
            except Exception as e:
                logger.warning(f"[EmailTracker] Could not load tracker: {e}")
                return set()
        return set()
    
    def _save_sent_papers(self):
        """Save sent papers to tracker"""
        data = {
            'sent_paper_ids': list(self.sent_papers),
            'total_sent': len(self.sent_papers),
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.tracker_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def filter_unsent_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        Filter to only papers NOT yet sent
        Returns: List of papers that haven't been emailed
        """
        unsent = []
        
        for paper in papers:
            paper_id = self._generate_paper_id(paper)
            
            if paper_id not in self.sent_papers:
                unsent.append(paper)
            else:
                logger.debug(f"[EmailTracker] Skipping already-sent: {paper.get('title', 'Unknown')[:50]}")
        
        logger.info(f"[EmailTracker] Filtered: {len(papers)} total → {len(unsent)} unsent")
        return unsent
    
    def mark_as_sent(self, papers: List[Dict]):
        """Mark papers as sent"""
        for paper in papers:
            paper_id = self._generate_paper_id(paper)
            self.sent_papers.add(paper_id)
        
        self._save_sent_papers()
        logger.info(f"[EmailTracker] Marked {len(papers)} papers as sent")
    
    def _generate_paper_id(self, paper: Dict) -> str:
        """
        Generate unique ID for paper
        Uses title + date for uniqueness
        """
        # Create stable ID from title
        title = paper.get('title', 'unknown').lower().strip()
        
        # Add date if available
        date = paper.get('date', paper.get('published', ''))
        
        # Generate hash
        id_string = f"{title}_{date}"
        return hashlib.md5(id_string.encode()).hexdigest()
    
    def get_statistics(self) -> Dict:
        """Get email tracker statistics"""
        return {
            'total_papers_sent': len(self.sent_papers),
            'tracker_file': self.tracker_file
        }


class ResultsArchiver:
    """
    Archives ALL analysis results for future reference
    Creates comprehensive, searchable archives
    """
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = results_dir
        
        # Create directory structure
        os.makedirs(results_dir, exist_ok=True)
        
        # Daily results
        self.daily_dir = os.path.join(results_dir, "daily")
        os.makedirs(self.daily_dir, exist_ok=True)
        
        # Complete archive (monthly)
        self.archive_dir = os.path.join(results_dir, "archive")
        os.makedirs(self.archive_dir, exist_ok=True)
        
        # Analysis metadata
        self.meta_dir = os.path.join(results_dir, "metadata")
        os.makedirs(self.meta_dir, exist_ok=True)
        
        logger.info(f"[Archiver] Results directory: {results_dir}")
    
    def archive_session_results(
        self,
        papers: List[Dict],
        session_stats: Dict,
        session_id: str = None
    ) -> str:
        """
        Archive complete session results
        Returns: Path to saved file
        """
        if not session_id:
            session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create comprehensive results package
        results_package = {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'total_papers': len(papers),
            'papers': papers,
            'statistics': session_stats,
            'metadata': {
                'archive_version': '1.0',
                'created_at': datetime.now().isoformat()
            }
        }
        
        # Save daily results
        daily_file = os.path.join(
            self.daily_dir,
            f"analysis_{session_id}.json"
        )
        
        with open(daily_file, 'w', encoding='utf-8') as f:
            json.dump(results_package, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[Archiver] Saved daily results: {daily_file}")
        
        # Append to monthly archive
        self._append_to_monthly_archive(papers)
        
        # Save metadata
        self._save_session_metadata(session_id, papers, session_stats)
        
        return daily_file
    
    def _append_to_monthly_archive(self, papers: List[Dict]):
        """Append papers to monthly archive"""
        month = datetime.now().strftime('%Y%m')
        archive_file = os.path.join(
            self.archive_dir,
            f"archive_{month}.json"
        )
        
        # Load existing or create new
        if os.path.exists(archive_file):
            with open(archive_file, 'r', encoding='utf-8') as f:
                archive_data = json.load(f)
        else:
            archive_data = {
                'month': month,
                'papers': [],
                'created_at': datetime.now().isoformat()
            }
        
        # Append new papers
        archive_data['papers'].extend(papers)
        archive_data['last_updated'] = datetime.now().isoformat()
        archive_data['total_papers'] = len(archive_data['papers'])
        
        # Save
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(archive_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[Archiver] Updated monthly archive: {archive_file} (total: {archive_data['total_papers']})")
    
    def _save_session_metadata(self, session_id: str, papers: List[Dict], stats: Dict):
        """Save session metadata for quick lookups"""
        meta_file = os.path.join(
            self.meta_dir,
            f"meta_{session_id}.json"
        )
        
        # Extract key metrics
        metadata = {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'total_papers': len(papers),
            'top_papers': [
                {
                    'title': p.get('title', 'Unknown')[:80],
                    'score': p.get('relevance_score', 0),
                    'platform': p.get('platform', 'Unknown')
                }
                for p in sorted(papers, key=lambda x: x.get('relevance_score', 0), reverse=True)[:10]
            ],
            'statistics': stats
        }
        
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    def get_session_history(self, days: int = 7) -> List[Dict]:
        """Get recent session history"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        
        sessions = []
        for filename in os.listdir(self.meta_dir):
            if not filename.startswith('meta_'):
                continue
            
            filepath = os.path.join(self.meta_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                
                session_time = datetime.fromisoformat(meta['timestamp'])
                if session_time > cutoff:
                    sessions.append(meta)
            except:
                continue
        
        return sorted(sessions, key=lambda x: x['timestamp'], reverse=True)
    
    def create_summary_report(self, days: int = 30) -> Dict:
        """Create summary report of all archived papers"""
        sessions = self.get_session_history(days=days)
        
        total_papers = sum(s['total_papers'] for s in sessions)
        
        # Platform distribution
        platforms = {}
        for session in sessions:
            for paper in session.get('top_papers', []):
                platform = paper.get('platform', 'Unknown')
                platforms[platform] = platforms.get(platform, 0) + 1
        
        summary = {
            'period': f'Last {days} days',
            'total_sessions': len(sessions),
            'total_papers': total_papers,
            'platform_distribution': platforms,
            'latest_session': sessions[0] if sessions else None
        }
        
        return summary
    
    def get_statistics(self) -> Dict:
        """Get archiver statistics"""
        daily_files = len([f for f in os.listdir(self.daily_dir) if f.endswith('.json')])
        archive_files = len([f for f in os.listdir(self.archive_dir) if f.endswith('.json')])
        
        return {
            'results_dir': self.results_dir,
            'daily_sessions': daily_files,
            'monthly_archives': archive_files,
            'latest_session': self._get_latest_session_id()
        }
    
    def _get_latest_session_id(self) -> str:
        """Get ID of most recent session"""
        files = [f for f in os.listdir(self.daily_dir) if f.startswith('analysis_')]
        
        if files:
            latest = sorted(files)[-1]
            return latest.replace('analysis_', '').replace('.json', '')
        
        return None