"""
HITL (Human-In-The-Loop) Validation System
Allows human review before finalizing analysis
Includes confidence scoring and manual review queue
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class HITLValidator:
    """
    Human-In-The-Loop validation system
    Papers with low confidence or high scores get human review
    """
    
    def __init__(
        self,
        review_dir: str = "data/hitl_review",
        auto_approve_threshold: float = 0.85,  # 85%+ confidence = auto-approve
        require_review_score: int = 90  # Score 90+ requires human review
    ):
        self.review_dir = review_dir
        self.auto_approve_threshold = auto_approve_threshold
        self.require_review_score = require_review_score
        
        # Create review directory
        os.makedirs(review_dir, exist_ok=True)
        os.makedirs(f"{review_dir}/pending", exist_ok=True)
        os.makedirs(f"{review_dir}/approved", exist_ok=True)
        os.makedirs(f"{review_dir}/rejected", exist_ok=True)
        
        self.stats = {
            'total_checked': 0,
            'auto_approved': 0,
            'pending_review': 0,
            'human_approved': 0,
            'human_rejected': 0
        }
        
        logger.info(f"[HITL] Initialized (auto-approve: {auto_approve_threshold}, review threshold: {require_review_score})")
    
    def validate_paper(self, paper: Dict, analysis: Dict) -> Tuple[str, str, Dict]:
        """
        Validate paper analysis
        Returns: (status, reason, validated_analysis)
        
        Status:
        - 'auto_approved': High confidence, auto-approved
        - 'needs_review': Low confidence or high score, needs human
        - 'pending': Waiting for human review
        """
        self.stats['total_checked'] += 1
        
        # Calculate confidence
        confidence = self._calculate_confidence(paper, analysis)
        score = analysis.get('relevance_score', 0)
        
        # Add confidence to analysis
        analysis['hitl_confidence'] = confidence
        analysis['hitl_status'] = 'pending'
        
        # Decision logic
        if confidence >= self.auto_approve_threshold and score < self.require_review_score:
            # High confidence, normal score → Auto-approve
            self.stats['auto_approved'] += 1
            analysis['hitl_status'] = 'auto_approved'
            
            logger.info(f"[HITL] AUTO-APPROVED (confidence: {confidence:.0%}, score: {score})")
            return 'auto_approved', 'High confidence analysis', analysis
        
        else:
            # Low confidence OR high score → Human review
            self.stats['pending_review'] += 1
            analysis['hitl_status'] = 'needs_review'
            
            # Save for review
            review_id = self._save_for_review(paper, analysis, confidence)
            
            reason = self._get_review_reason(confidence, score)
            logger.info(f"[HITL] NEEDS REVIEW: {reason} (ID: {review_id})")
            
            return 'needs_review', reason, analysis
    
    def _calculate_confidence(self, paper: Dict, analysis: Dict) -> float:
        """
        Calculate confidence score (0-1) based on multiple factors
        """
        confidence_factors = []
        
        # Factor 1: Council consensus (if available)
        if 'council_metadata' in analysis:
            meta = analysis['council_metadata']
            score_range = meta.get('score_range', 20)
            
            if score_range <= 10:
                confidence_factors.append(0.95)  # Strong consensus
            elif score_range <= 20:
                confidence_factors.append(0.75)  # Moderate consensus
            else:
                confidence_factors.append(0.50)  # Weak consensus
        
        # Factor 2: Data completeness
        required_fields = ['memory_insight', 'engineering_takeaway', 'platform', 'model_type']
        filled_fields = sum(1 for f in required_fields if analysis.get(f) and analysis[f] != 'Unknown')
        completeness = filled_fields / len(required_fields)
        confidence_factors.append(completeness)
        
        # Factor 3: Specific numbers in memory_insight
        memory_insight = analysis.get('memory_insight', '')
        # Ensure memory_insight is a string (handle case where it might be a dict)
        if isinstance(memory_insight, dict):
            memory_insight = str(memory_insight)
        memory_insight = str(memory_insight) if memory_insight else ''
        has_numbers = any(char.isdigit() for char in memory_insight)
        has_units = any(unit in memory_insight.lower() for unit in ['gb', 'mb', 'ms', 'tops', '%'])
        
        if has_numbers and has_units:
            confidence_factors.append(0.9)
        elif has_numbers:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # Factor 4: Full text availability (if using Playwright)
        if paper.get('has_full_text', False):
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.6)
        
        # Factor 5: Multiple AI agreement (if available)
        if 'crew_metadata' in analysis:
            confidence_factors.append(0.95)  # CrewAI = high confidence
        
        # Calculate weighted average
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        return 0.5
    
    def _get_review_reason(self, confidence: float, score: int) -> str:
        """Get human-readable review reason"""
        reasons = []
        
        if confidence < self.auto_approve_threshold:
            reasons.append(f"Low confidence ({confidence:.0%})")
        
        if score >= self.require_review_score:
            reasons.append(f"High score ({score}) requires verification")
        
        return " + ".join(reasons) if reasons else "Manual review requested"
    
    def _save_for_review(self, paper: Dict, analysis: Dict, confidence: float) -> str:
        """Save paper for human review"""
        
        # Generate review ID
        review_id = hashlib.md5(
            f"{paper.get('title', '')}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]
        
        # Create review package
        review_package = {
            'review_id': review_id,
            'created_at': datetime.now().isoformat(),
            'confidence': confidence,
            'paper': {
                'title': paper.get('title', 'Unknown'),
                'abstract': paper.get('abstract', paper.get('summary', ''))[:500],
                'url': paper.get('link', ''),
                'source': paper.get('source', 'Unknown'),
                'full_text_available': paper.get('has_full_text', False)
            },
            'analysis': analysis,
            'review_questions': self._generate_review_questions(analysis)
        }
        
        # Save to pending
        review_file = f"{self.review_dir}/pending/{review_id}.json"
        with open(review_file, 'w', encoding='utf-8') as f:
            json.dump(review_package, f, indent=2)
        
        logger.info(f"[HITL] Saved for review: {review_file}")
        return review_id
    
    def _generate_review_questions(self, analysis: Dict) -> List[str]:
        """Generate questions for human reviewer"""
        questions = []
        
        score = analysis.get('relevance_score', 0)
        
        if score >= 90:
            questions.append("Is this genuinely a breakthrough? Or incremental improvement?")

        memory_insight = analysis.get('memory_insight', '')
        # Ensure memory_insight is a string (handle case where it might be a dict)
        if isinstance(memory_insight, dict):
            memory_insight = str(memory_insight)
        memory_insight = str(memory_insight) if memory_insight else ''

        if 'unknown' in memory_insight.lower() or not any(c.isdigit() for c in memory_insight):
            questions.append("Can you find specific memory numbers in the paper?")
        
        if analysis.get('dram_impact') == 'High':
            questions.append("Is the DRAM impact claim supported by benchmarks?")
        
        if 'council_metadata' in analysis:
            meta = analysis['council_metadata']
            if meta.get('score_range', 0) > 15:
                questions.append("AIs disagreed on score. Which assessment is more accurate?")
        
        return questions
    
    def get_pending_reviews(self) -> List[Dict]:
        """Get all papers pending human review"""
        pending_dir = f"{self.review_dir}/pending"
        pending_files = [f for f in os.listdir(pending_dir) if f.endswith('.json')]
        
        reviews = []
        for filename in pending_files:
            with open(f"{pending_dir}/{filename}", 'r', encoding='utf-8') as f:
                reviews.append(json.load(f))
        
        return sorted(reviews, key=lambda x: x.get('created_at', ''), reverse=True)
    
    def approve_review(self, review_id: str, notes: str = "") -> bool:
        """Human approves a review"""
        pending_file = f"{self.review_dir}/pending/{review_id}.json"
        
        if not os.path.exists(pending_file):
            logger.error(f"[HITL] Review {review_id} not found")
            return False
        
        # Load review
        with open(pending_file, 'r', encoding='utf-8') as f:
            review = json.load(f)
        
        # Add approval
        review['human_review'] = {
            'status': 'approved',
            'reviewed_at': datetime.now().isoformat(),
            'notes': notes
        }
        
        # Move to approved
        approved_file = f"{self.review_dir}/approved/{review_id}.json"
        with open(approved_file, 'w', encoding='utf-8') as f:
            json.dump(review, f, indent=2)
        
        # Remove from pending
        os.remove(pending_file)
        
        self.stats['human_approved'] += 1
        logger.info(f"[HITL] Approved: {review_id}")
        return True
    
    def reject_review(self, review_id: str, reason: str = "") -> bool:
        """Human rejects a review"""
        pending_file = f"{self.review_dir}/pending/{review_id}.json"
        
        if not os.path.exists(pending_file):
            logger.error(f"[HITL] Review {review_id} not found")
            return False
        
        # Load review
        with open(pending_file, 'r', encoding='utf-8') as f:
            review = json.load(f)
        
        # Add rejection
        review['human_review'] = {
            'status': 'rejected',
            'reviewed_at': datetime.now().isoformat(),
            'reason': reason
        }
        
        # Move to rejected
        rejected_file = f"{self.review_dir}/rejected/{review_id}.json"
        with open(rejected_file, 'w', encoding='utf-8') as f:
            json.dump(review, f, indent=2)
        
        # Remove from pending
        os.remove(pending_file)
        
        self.stats['human_rejected'] += 1
        logger.info(f"[HITL] Rejected: {review_id}")
        return True
    
    def show_review_interface(self, review_id: str = None):
        """Show interactive review interface"""
        
        if review_id:
            # Show specific review
            pending_file = f"{self.review_dir}/pending/{review_id}.json"
            if not os.path.exists(pending_file):
                print(f"Review {review_id} not found")
                return
            
            with open(pending_file, 'r', encoding='utf-8') as f:
                review = json.load(f)
            
            self._display_review(review)
        
        else:
            # Show all pending
            pending = self.get_pending_reviews()
            
            if not pending:
                print("\n[HITL] No pending reviews")
                return
            
            print(f"\n{'='*80}")
            print(f"PENDING HUMAN REVIEWS: {len(pending)}")
            print(f"{'='*80}\n")
            
            for idx, review in enumerate(pending, 1):
                print(f"{idx}. [{review['review_id']}] {review['paper']['title'][:60]}")
                print(f"   Score: {review['analysis'].get('relevance_score', 0)}")
                print(f"   Confidence: {review['confidence']:.0%}")
                print()
    
    def _display_review(self, review: Dict):
        """Display single review for human"""
        print(f"\n{'='*80}")
        print(f"REVIEW: {review['review_id']}")
        print(f"{'='*80}\n")
        
        # Paper info
        print(f"Title: {review['paper']['title']}")
        print(f"Source: {review['paper']['source']}")
        print(f"URL: {review['paper']['url']}")
        print()
        
        # Analysis
        analysis = review['analysis']
        print(f"Relevance Score: {analysis.get('relevance_score', 0)}")
        print(f"Confidence: {review['confidence']:.0%}")
        print(f"Platform: {analysis.get('platform', 'Unknown')}")
        print(f"DRAM Impact: {analysis.get('dram_impact', 'Unknown')}")
        print()
        print(f"Memory Insight: {analysis.get('memory_insight', 'N/A')}")
        print()
        print(f"Engineering Takeaway: {analysis.get('engineering_takeaway', 'N/A')}")
        print()
        
        # Review questions
        if review.get('review_questions'):
            print("Review Questions:")
            for q in review['review_questions']:
                print(f"  - {q}")
            print()
    
    def get_statistics(self) -> Dict:
        """Get HITL statistics"""
        pending_count = len(self.get_pending_reviews())
        
        return {
            **self.stats,
            'currently_pending': pending_count,
            'auto_approve_rate': (
                self.stats['auto_approved'] / self.stats['total_checked'] * 100
                if self.stats['total_checked'] > 0 else 0
            )
        }