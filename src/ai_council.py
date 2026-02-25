"""
AGI Council System
Multi-AI verification with consensus mechanism
Groq analyzes → Ollama verifies → Gemini finalizes
"""

import os
import json
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from groq import Groq
import requests

logger = logging.getLogger(__name__)


class AICouncil:
    """
    Multi-AI council for consensus-based analysis
    Each AI verifies the previous AI's work
    """
    
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        ollama_url: str = "http://localhost:11434"
    ):
        # Initialize all AIs
        self.groq_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.gemini_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")
        self.ollama_url = ollama_url
        
        # Groq
        if self.groq_key:
            self.groq = Groq(api_key=self.groq_key)
            self.groq_models = [
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "gemma2-9b-it"
            ]
            self.groq_idx = 0
            logger.info("[Council] Groq initialized")
        else:
            self.groq = None
        
        # Ollama
        self.ollama_model = "gemma3:4b"
        if self._check_ollama():
            logger.info("[Council] Ollama initialized")
        
        # Gemini
        if self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self.gemini = genai.GenerativeModel("gemini-1.5-flash")
                logger.info("[Council] Gemini initialized")
            except:
                self.gemini = None
        else:
            self.gemini = None
        
        self.stats = {
            'total': 0,
            'consensus_reached': 0,
            'disagreements': 0,
            'groq_proposals': 0,
            'ollama_verifications': 0,
            'gemini_finalizations': 0
        }
    
    def _check_ollama(self) -> bool:
        """Check Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def council_analysis(self, article: Dict, previous_findings: List[Dict]) -> Dict:
        """
        AGI Council Process:
        1. Groq analyzes (initial proposal)
        2. Ollama verifies (checks for errors)
        3. Gemini finalizes (consensus + quality)
        
        Returns: Consensus analysis with verification chain
        """
        self.stats['total'] += 1
        
        # Check for duplicates first
        if self._is_duplicate(article, previous_findings):
            logger.info("[Council] DUPLICATE detected - rejecting")
            return self._create_rejection("duplicate", "Already analyzed in recent history")
        
        # STAGE 1: Groq Proposal
        groq_analysis = self._groq_propose(article, previous_findings)
        if not groq_analysis:
            return self._create_rejection("failed", "Groq analysis failed")
        
        self.stats['groq_proposals'] += 1
        logger.info(f"[Council] Groq proposed: Score {groq_analysis.get('relevance_score', 0)}")
        
        # STAGE 2: Ollama Verification
        ollama_verification = self._ollama_verify(article, groq_analysis)
        if not ollama_verification:
            logger.warning("[Council] Ollama verification failed - using Groq only")
            ollama_verification = groq_analysis
        
        self.stats['ollama_verifications'] += 1
        logger.info(f"[Council] Ollama verified: Score {ollama_verification.get('relevance_score', 0)}")
        
        # STAGE 3: Gemini Finalization
        final_consensus = self._gemini_finalize(article, groq_analysis, ollama_verification)
        if not final_consensus:
            logger.warning("[Council] Gemini failed - using Ollama result")
            final_consensus = ollama_verification
        
        self.stats['gemini_finalizations'] += 1
        
        # Calculate consensus
        scores = [
            groq_analysis.get('relevance_score', 0),
            ollama_verification.get('relevance_score', 0),
            final_consensus.get('relevance_score', 0)
        ]
        
        score_range = max(scores) - min(scores)
        if score_range <= 15:  # Agreement within 15 points
            self.stats['consensus_reached'] += 1
            consensus_status = "strong"
        else:
            self.stats['disagreements'] += 1
            consensus_status = "weak"
        
        # Enrich final result
        final_consensus['council_metadata'] = {
            'groq_score': scores[0],
            'ollama_score': scores[1],
            'gemini_score': scores[2],
            'consensus_status': consensus_status,
            'score_range': score_range,
            'verification_chain': 'Groq -> Ollama -> Gemini',
            'processed_at': datetime.now().isoformat()
        }
        
        logger.info(f"[Council] FINAL: Score {final_consensus.get('relevance_score', 0)} ({consensus_status} consensus)")
        
        return final_consensus
    
    def _is_duplicate(self, article: Dict, previous_findings: List[Dict]) -> bool:
        """Check if this is a duplicate"""
        title = article.get('title', '')
        # Ensure title is a string (handle case where it might be a dict)
        if isinstance(title, dict):
            title = str(title)
        title = str(title) if title else ''
        title = title.lower()

        for prev in previous_findings:
            prev_title = prev.get('title', '')
            # Ensure prev_title is a string
            if isinstance(prev_title, dict):
                prev_title = str(prev_title)
            prev_title = str(prev_title) if prev_title else ''
            prev_title = prev_title.lower()
            
            # Exact match
            if title == prev_title:
                return True
            
            # High similarity (simple word overlap)
            title_words = set(title.split())
            prev_words = set(prev_title.split())
            
            if len(title_words) > 5 and len(prev_words) > 5:
                overlap = len(title_words & prev_words) / len(title_words)
                if overlap > 0.8:  # 80% word overlap
                    return True
        
        return False
    
    def _groq_propose(self, article: Dict, context: List[Dict]) -> Optional[Dict]:
        """STAGE 1: Groq makes initial proposal"""
        
        # Build deep analysis prompt
        prompt = self._build_deep_analysis_prompt(article, context, "initial")
        
        for attempt in range(2):
            model = self.groq_models[self.groq_idx]
            try:
                response = self.groq.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                if "rate limit" in str(e).lower():
                    self.groq_idx = (self.groq_idx + 1) % len(self.groq_models)
                    continue
                logger.debug(f"Groq error: {e}")
                break
        
        return None
    
    def _ollama_verify(self, article: Dict, groq_analysis: Dict) -> Optional[Dict]:
        """STAGE 2: Ollama verifies Groq's analysis"""
        
        prompt = f"""VERIFICATION TASK:
Another AI (Groq) analyzed this paper. Your job is to VERIFY if the analysis is accurate.

PAPER:
Title: {article.get('title', 'N/A')}
Summary: {article.get('summary', 'N/A')}

GROQ'S ANALYSIS:
{json.dumps(groq_analysis, indent=2)}

VERIFICATION INSTRUCTIONS:
1. Read the paper carefully
2. Check if Groq's score is accurate (too high/low?)
3. Verify memory_insight has specific numbers
4. Check if engineering_takeaway is actionable
5. Adjust score if needed (+/- 10 points max)

Return JSON with:
- relevance_score: Your verified score (0-100)
- platform: Verified platform
- model_type: Verified model type
- memory_insight: Improved with more specifics
- dram_impact: Verified impact
- engineering_takeaway: Improved takeaway
- verification_notes: What you changed and why

JSON:"""
        
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=120
            )
            if response.status_code == 200:
                return json.loads(response.json()['response'])
        except Exception as e:
            logger.debug(f"Ollama verify error: {e}")
        
        return None
    
    def _gemini_finalize(self, article: Dict, groq_analysis: Dict, ollama_analysis: Dict) -> Optional[Dict]:
        """STAGE 3: Gemini creates final consensus"""
        
        prompt = f"""CONSENSUS & FINALIZATION:
You are the final arbiter. Two AIs analyzed this paper:

PAPER:
Title: {article.get('title', 'N/A')}
Summary: {article.get('summary', 'N/A')}

GROQ ANALYSIS:
Score: {groq_analysis.get('relevance_score', 0)}
Memory: {groq_analysis.get('memory_insight', 'N/A')}

OLLAMA VERIFICATION:
Score: {ollama_analysis.get('relevance_score', 0)}
Memory: {ollama_analysis.get('memory_insight', 'N/A')}
Notes: {ollama_analysis.get('verification_notes', 'N/A')}

YOUR TASK:
1. Consider both analyses
2. Create final consensus score (weighted: 40% Groq, 60% Ollama)
3. Synthesize best memory_insight from both
4. Create definitive engineering_takeaway

Return JSON with final consensus analysis.

JSON:"""
        
        try:
            response = self.gemini.generate_content(prompt)
            if response and response.text:
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                return json.loads(text)
        except Exception as e:
            logger.debug(f"Gemini finalize error: {e}")
        
        return None
    
    def _build_deep_analysis_prompt(self, article: Dict, context: List[Dict], stage: str) -> str:
        """Build AGI-level deep analysis prompt"""
        
        # Extract key findings from context
        context_summary = ""
        if context:
            recent_titles = [c.get('title', 'Unknown')[:80] for c in context[-5:]]
            context_summary = f"\nRECENT PAPERS:\n" + "\n".join(f"- {t}" for t in recent_titles)
        
        return f"""AGI-LEVEL DEEP ANALYSIS:

{context_summary}

NEW PAPER TO ANALYZE:
Title: {article.get('title', 'N/A')}
Authors: {article.get('authors', 'Unknown')}
Summary: {article.get('summary', 'N/A')}
Source: {article.get('source', 'Unknown')}

DEEP ANALYSIS REQUIREMENTS:

1. TECHNICAL DEPTH:
   - Extract SPECIFIC numbers (GB, ms, TOPS, etc.)
   - Identify optimization techniques
   - Note hardware acceleration (NPU, GPU, CPU)

2. MEMORY ANALYSIS:
   - Peak DRAM usage
   - Memory bandwidth requirements
   - Compression/quantization methods
   - Before/after comparisons

3. DEPLOYMENT REALITY:
   - Can this run on mobile? (4-8GB RAM)
   - Can this run on laptop? (8-16GB RAM)
   - What's the actual bottleneck?

4. NOVELTY CHECK:
   - Is this genuinely new?
   - Or incremental improvement?
   - Breakthrough or optimization?

5. ENGINEERING VALUE:
   - Actionable insights
   - Implementation complexity
   - Real-world applicability

SCORING:
- 95-100: Breakthrough with concrete metrics (e.g., "2GB -> 500MB proven")
- 85-94: Major innovation with strong evidence
- 70-84: Solid work with specific optimizations
- 50-69: Incremental improvement
- 30-49: Tangentially relevant
- 0-29: Not on-device or no memory focus

Return JSON with:
- relevance_score: 0-100
- platform: Mobile/Laptop/Both/Unknown
- model_type: LLM/Vision/Audio/Multimodal/Other
- memory_insight: MUST include specific numbers
- dram_impact: High/Medium/Low based on actual data
- engineering_takeaway: One concrete actionable insight
- technical_details: List of key techniques/optimizations
- deployment_feasibility: Can this actually be deployed? Why/why not?

JSON:"""
    
    def _create_rejection(self, reason: str, details: str) -> Dict:
        """Create rejection response"""
        return {
            "relevance_score": 0,
            "platform": "Unknown",
            "model_type": "Unknown",
            "memory_insight": f"Rejected: {details}",
            "dram_impact": "Unknown",
            "engineering_takeaway": f"Not analyzed - {reason}",
            "status": "rejected",
            "rejection_reason": reason,
            "council_metadata": {
                "consensus_status": "rejected",
                "processed_at": datetime.now().isoformat()
            }
        }
    
    def get_statistics(self) -> Dict:
        """Get council statistics"""
        return {
            'council_stats': self.stats,
            'consensus_rate': (
                self.stats['consensus_reached'] / self.stats['total'] * 100
                if self.stats['total'] > 0 else 0
            )
        }