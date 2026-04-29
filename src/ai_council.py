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

try:
    from src.retry import (
        retry_with_backoff, CircuitBreaker,
        is_rate_limit_error, smart_rate_limit_sleep,
    )
    _groq_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=120, name="groq")
    _ollama_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60, name="ollama")
    _gemini_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=120, name="gemini")
    _HAS_RETRY = True
except ImportError:
    _groq_breaker = _ollama_breaker = _gemini_breaker = None
    _HAS_RETRY = False

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

        # Ollama (optional - disabled in GitHub Actions)
        self.enable_ollama = os.getenv("ENABLE_OLLAMA", "true").lower() == "true"
        self.ollama_model = "gemma3:4b"
        self.ollama_available = self._check_ollama() if self.enable_ollama else False
        if self.ollama_available:
            logger.info("[Council] Ollama initialized")
        
        # Gemini — new google-genai SDK
        self.gemini = None
        self._gemini_client = None
        if self.gemini_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.gemini_key)
                # Quick probe
                test = self._gemini_client.models.generate_content(
                    model="gemini-2.5-flash", contents="ping"
                )
                if test and test.text:
                    self.gemini = True   # flag: client is ready
                    logger.info("[Council] Gemini initialized (gemini-2.5-flash)")
                else:
                    logger.warning("[Council] Gemini probe returned empty")
            except Exception as e:
                logger.warning(f"[Council] Gemini init failed: {e}")
        else:
            logger.warning("[Council] GOOGLE_API_KEY not set — Gemini unavailable")

        # NVIDIA NIM — Kimi-K2 Thinking (deep synthesis stage)
        self._nim_client = None
        self.nim_available = False
        nim_key = os.getenv("NVIDIA_NIM_API_KEY")
        if nim_key:
            try:
                from langchain_nvidia_ai_endpoints import ChatNVIDIA
                self._nim_client = ChatNVIDIA(
                    model="moonshotai/kimi-k2-thinking",
                    api_key=nim_key,
                    temperature=0.2,
                    max_tokens=4096,
                )
                # Quick probe
                test_resp = self._nim_client.invoke("ping")
                if test_resp and test_resp.content:
                    self.nim_available = True
                    logger.info("[Council] ✓ NVIDIA NIM initialized (kimi-k2-thinking)")
                else:
                    logger.warning("[Council] NIM probe returned empty")
            except ImportError:
                logger.warning(
                    "[Council] langchain-nvidia-ai-endpoints not installed. "
                    "Install: pip install langchain-nvidia-ai-endpoints"
                )
            except Exception as e:
                logger.warning(f"[Council] NIM init failed: {e}")
        else:
            logger.info("[Council] NVIDIA_NIM_API_KEY not set — NIM synthesis disabled")

        self.stats = {
            'total': 0,
            'consensus_reached': 0,
            'disagreements': 0,
            'groq_proposals': 0,
            'ollama_verifications': 0,
            'gemini_finalizations': 0,
            'nim_syntheses': 0
        }
    
    def _check_ollama(self) -> bool:
        """Check Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
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
        
        # STAGE 1: Groq PRIMARY → Gemini fallback
        groq_analysis = self._groq_propose(article, previous_findings)
        if groq_analysis:
            base_analysis = groq_analysis
            logger.info(f"[Council] Groq proposed: Score {groq_analysis.get('relevance_score', 0)}")
        elif self._gemini_client:
            # Gemini fallback when Groq fails
            prompt = self._build_deep_analysis_prompt(article, previous_findings, "gemini_fallback")
            try:
                response = self._gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                if response and response.text:
                    text = response.text.strip()
                    if '```json' in text:
                        text = text.split('```json')[1].split('```')[0].strip()
                    base_analysis = json.loads(text)
                    logger.info(f"[Gemini Fallback] Success: Score {base_analysis.get('relevance_score', 0)}")
                else:
                    return self._create_rejection("failed", "All analysis failed")
            except Exception as e:
                logger.error(f"[Gemini Fallback] failed: {e}")
                return self._create_rejection("failed", "All analysis failed")
        else:
            return self._create_rejection("failed", "All analysis failed")

        self.stats['groq_proposals'] += 1 if groq_analysis else 0
        logger.info(f"[Council] Primary proposed: Score {base_analysis.get('relevance_score', 0)}")
        
        # STAGE 2: Ollama Verification (skipped if unavailable)
        ollama_verification = None
        if self.ollama_available:
            ollama_verification = self._ollama_verify(article, base_analysis)
        if not ollama_verification:
            logger.info("[Council] Ollama skipped/failed — using base analysis")
            ollama_verification = base_analysis
        else:
            self.stats['ollama_verifications'] += 1
        logger.info(f"[Council] Ollama verified: Score {ollama_verification.get('relevance_score', 0)}")

        # STAGE 3: Gemini Finalization
        final_consensus = self._gemini_finalize(article, base_analysis, ollama_verification)
        if not final_consensus:
            logger.warning("[Council] Gemini failed - using Ollama result")
            final_consensus = ollama_verification
        
        self.stats['gemini_finalizations'] += 1

        # STAGE 4: NIM Deep Synthesis (optional — enriches with executive content)
        if self.nim_available and final_consensus.get('relevance_score', 0) >= 50:
            nim_enrichment = self._nim_synthesize(article, final_consensus)
            if nim_enrichment:
                # Merge NIM's rich fields into final consensus
                for key in ('executive_summary', 'research_brief', 'key_metrics',
                            'why_it_matters', 'implementation_guidance'):
                    if key in nim_enrichment and nim_enrichment[key]:
                        final_consensus[key] = nim_enrichment[key]
                self.stats['nim_syntheses'] += 1
                logger.info("[Council] NIM enrichment applied")
        
        # Calculate consensus
        scores = [
            base_analysis.get('relevance_score', 0),
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

        verification_chain = 'Groq -> Ollama -> Gemini'
        if self.nim_available and self.stats['nim_syntheses'] > 0:
            verification_chain += ' -> NIM(Kimi-K2)'
        
        # Enrich final result
        final_consensus['council_metadata'] = {
            'groq_score': scores[0],
            'ollama_score': scores[1],
            'gemini_score': scores[2],
            'consensus_status': consensus_status,
            'score_range': score_range,
            'verification_chain': verification_chain,
            'nim_enriched': self.stats['nim_syntheses'] > 0,
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
        """STAGE 1: Groq makes initial proposal (429-aware)"""

        # Circuit breaker: skip if Groq API is in OPEN state
        if _groq_breaker and not _groq_breaker.can_execute():
            logger.warning("[Council] Groq circuit breaker OPEN — skipping")
            return None

        prompt = self._build_deep_analysis_prompt(article, context, "initial")

        for attempt in range(4):
            model = self.groq_models[self.groq_idx]
            try:
                response = self.groq.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                if _groq_breaker:
                    _groq_breaker.record_success()
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                if _HAS_RETRY and is_rate_limit_error(e):
                    # Rotate model first
                    self.groq_idx = (self.groq_idx + 1) % len(self.groq_models)
                    # Sleep using server's Retry-After
                    smart_rate_limit_sleep(e, attempt)
                    if _groq_breaker:
                        _groq_breaker.record_failure()
                    continue
                elif "rate limit" in str(e).lower():
                    # Fallback if retry module not loaded
                    self.groq_idx = (self.groq_idx + 1) % len(self.groq_models)
                    import time; time.sleep(30)
                    continue
                logger.debug(f"Groq error: {e}")
                if _groq_breaker:
                    _groq_breaker.record_failure()
                break

        return None
    
    def _ollama_verify(self, article: Dict, groq_analysis: Dict) -> Optional[Dict]:
        """STAGE 2: Ollama verifies Groq's analysis (429-aware)"""

        if _ollama_breaker and not _ollama_breaker.can_execute():
            logger.warning("[Council] Ollama circuit breaker OPEN — skipping")
            return None

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

        for attempt in range(3):
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
                # Explicit 429 check for HTTP responses
                if response.status_code == 429:
                    if _HAS_RETRY:
                        smart_rate_limit_sleep(Exception(f"Ollama 429: {response.text}"), attempt)
                    else:
                        import time; time.sleep(30)
                    if _ollama_breaker:
                        _ollama_breaker.record_failure()
                    continue
                if response.status_code == 200:
                    if _ollama_breaker:
                        _ollama_breaker.record_success()
                    return json.loads(response.json()['response'])
            except Exception as e:
                if _HAS_RETRY and is_rate_limit_error(e):
                    smart_rate_limit_sleep(e, attempt)
                    if _ollama_breaker:
                        _ollama_breaker.record_failure()
                    continue
                logger.debug(f"Ollama verify error: {e}")
                if _ollama_breaker:
                    _ollama_breaker.record_failure()
                break

        return None
    
    def _gemini_finalize(self, article: Dict, groq_analysis: Dict, ollama_analysis: Dict) -> Optional[Dict]:
        """STAGE 3: Gemini creates final consensus — 429-aware"""
        if not self._gemini_client:
            return None

        if _gemini_breaker and not _gemini_breaker.can_execute():
            logger.warning("[Council] Gemini circuit breaker OPEN — skipping")
            return None

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

        for attempt in range(3):
            try:
                response = self._gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                if response and response.text:
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    if _gemini_breaker:
                        _gemini_breaker.record_success()
                    return json.loads(text)
            except Exception as e:
                if _HAS_RETRY and is_rate_limit_error(e):
                    smart_rate_limit_sleep(e, attempt)
                    if _gemini_breaker:
                        _gemini_breaker.record_failure()
                    continue
                logger.debug(f"Gemini finalize error: {e}")
                if _gemini_breaker:
                    _gemini_breaker.record_failure()
                break

        return None

    def _nim_synthesize(self, article: Dict, consensus: Dict) -> Optional[Dict]:
        """
        STAGE 4: NIM Kimi-K2-Thinking — Deep Synthesis.

        Takes the council consensus and rewrites it into research-grade
        executive content suitable for PPT slides and podcast narration.
        Only called for papers scoring >= 50 (TurboQuant: skip low-value work).
        """
        if not self._nim_client:
            return None

        title = article.get('title', 'N/A')
        summary = article.get('summary', 'N/A')
        score = consensus.get('relevance_score', 0)
        mem = consensus.get('memory_insight', 'N/A')
        takeaway = consensus.get('engineering_takeaway', 'N/A')
        platform = consensus.get('platform', 'Unknown')
        model_type = consensus.get('model_type', 'Unknown')
        dram = consensus.get('dram_impact', 'Unknown')

        prompt = f"""You are a senior research analyst writing an executive intelligence brief.

PAPER:
Title: {title}
Summary: {summary[:1500]}
Platform: {platform} | Model Type: {model_type} | DRAM Impact: {dram}

COUNCIL CONSENSUS (Score: {score}/100):
Memory Insight: {mem}
Engineering Takeaway: {takeaway}

TASK: Rewrite this into a structured executive brief that a VP of Engineering would read in a slide deck. Be specific, cite numbers from the paper, and write in complete sentences.

Return ONLY a JSON object with these fields:
{{
  "executive_summary": "<3-4 complete sentences: what the paper does, the method, and the quantified result>",
  "research_brief": {{
    "problem": "<1-2 sentences: what bottleneck this addresses>",
    "method": "<1-2 sentences: what technique is proposed>",
    "result": "<1-2 sentences WITH numbers: what was achieved>",
    "limitation": "<1 sentence: any caveat>"
  }},
  "key_metrics": ["<metric1>", "<metric2>", "<metric3>"],
  "why_it_matters": "<2-3 sentences: practical implication for memory/storage engineers>",
  "implementation_guidance": "<1-2 sentences: how a practitioner would apply this>"
}}

JSON:"""

        for attempt in range(3):
            try:
                response = self._nim_client.invoke(prompt)
                if response and response.content:
                    text = response.content.strip()
                    # Handle thinking tokens: extract only the final JSON
                    if '<think>' in text and '</think>' in text:
                        text = text.split('</think>')[-1].strip()
                    if '```json' in text:
                        text = text.split('```json')[1].split('```')[0].strip()
                    elif '```' in text:
                        text = text.split('```')[1].split('```')[0].strip()
                    result = json.loads(text)
                    logger.info(f"[NIM] ✓ Kimi-K2 synthesis complete for: {title[:50]}")
                    return result
            except Exception as e:
                if _HAS_RETRY and is_rate_limit_error(e):
                    smart_rate_limit_sleep(e, attempt)
                    continue
                logger.debug(f"[NIM] Synthesis error (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    import time
                    time.sleep(2)
                    continue
                break

        return None

    def _build_deep_analysis_prompt(self, article: Dict, context: List[Dict], stage: str) -> str:
        """Build research-grade analysis prompt that produces consumable executive content."""

        # Extract key findings from context
        context_summary = ""
        if context:
            recent_titles = [c.get('title', 'Unknown')[:80] for c in context[-5:]]
            context_summary = f"\nRECENT PAPERS (avoid overlap):\n" + "\n".join(f"- {t}" for t in recent_titles)

        full_text_snippet = ""
        ft = article.get('full_text', '')
        if ft and len(ft) > 200:
            full_text_snippet = f"\nFULL TEXT EXCERPT (first 2000 chars):\n{ft[:2000]}\n"

        return f"""You are a senior research analyst writing an executive intelligence brief for memory & storage engineers.

{context_summary}

PAPER TO ANALYZE:
Title: {article.get('title', 'N/A')}
Authors: {article.get('authors', 'Unknown')}
Source: {article.get('source', 'Unknown')}
Summary: {article.get('summary', 'N/A')}
{full_text_snippet}

INSTRUCTIONS — Write like a research analyst, NOT a chatbot:

1. READ the paper carefully. Extract SPECIFIC numbers, techniques, and results.
2. Write an "executive_summary" — 3 to 4 complete sentences that a VP of Engineering would read in a slide deck. Include the core finding, the method, and the quantified result.
3. Write a "research_brief" as a structured dict with:
   - "problem": What bottleneck or challenge does this address? (1-2 sentences)
   - "method": What technique or approach is proposed? (1-2 sentences)
   - "result": What was achieved? Include numbers (GB, ms, %, TOPS). (1-2 sentences)
   - "limitation": Any caveats or constraints? (1 sentence)
4. Extract "key_metrics" — a list of 3-5 specific measurements from the paper (e.g., "2.1GB peak DRAM", "1.8x speedup on Snapdragon 8 Gen 3", "4-bit GPTQ reduces size by 73%")
5. Write "why_it_matters" — a 2-3 sentence paragraph explaining the practical implication for an engineer working on on-device AI / memory optimization. Be concrete, not vague.
6. Write "implementation_guidance" — 1-2 sentences on how a practitioner would apply this (e.g., "Apply INT4 quantization using AutoGPTQ on your Llama-3 model before deploying to Android NNAPI").

SCORING (be honest — inflated scores waste engineers' time):
- 90-100: Breakthrough with proven metrics on real hardware
- 75-89: Strong innovation with specific optimizations and benchmarks
- 60-74: Solid incremental work with measurable improvements
- 40-59: Tangentially relevant or missing concrete evidence
- 0-39: Not related to on-device AI or memory optimization

Return a single JSON object:
{{
  "relevance_score": <int 0-100>,
  "platform": "<Mobile|Laptop|Edge|Server|Both|Unknown>",
  "model_type": "<LLM|Vision|Audio|Multimodal|Diffusion|Other>",
  "executive_summary": "<3-4 sentence paragraph for slide deck>",
  "research_brief": {{
    "problem": "<1-2 sentences>",
    "method": "<1-2 sentences>",
    "result": "<1-2 sentences with numbers>",
    "limitation": "<1 sentence>"
  }},
  "key_metrics": ["<metric1>", "<metric2>", "<metric3>"],
  "why_it_matters": "<2-3 sentence paragraph>",
  "implementation_guidance": "<1-2 sentences>",
  "memory_insight": "<backward-compat: 2-3 sentence summary of memory/DRAM finding>",
  "dram_impact": "<High|Medium|Low>",
  "engineering_takeaway": "<backward-compat: 1-2 sentence actionable insight>",
  "quantization_method": "<technique name or N/A>",
  "technical_details": ["<technique1>", "<technique2>"],
  "deployment_feasibility": "<1-2 sentences>"
}}

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