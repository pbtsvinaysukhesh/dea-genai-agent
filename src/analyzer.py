"""
SIMPLE AI Analyzer with Recent Papers Context
Windows compatible, fast, with simple context awareness
"""

import os
import json
import logging
from typing import Dict, Optional
from datetime import datetime
from groq import Groq
import requests

logger = logging.getLogger(__name__)


class SimpleAIProcessor:
    """
    Simple, fast AI processor with basic context
    Windows compatible - no Unicode symbols
    """
    
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        ollama_url: str = "http://localhost:11434"
    ):
        # Groq setup
        self.groq_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if self.groq_key:
            self.groq_client = Groq(api_key=self.groq_key)
            self.groq_models = [
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "gemma2-9b-it"
            ]
            self.current_model_idx = 0
            logger.info("[OK] Groq initialized")
        else:
            self.groq_client = None
        
        # Ollama setup
        self.ollama_url = ollama_url
        self.ollama_model = "gemma3:4b"
        self.ollama_available = self._check_ollama()
        
        # Gemini setup
        self.gemini_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")
        if self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self.gemini = genai.GenerativeModel("gemini-1.5-flash")
                logger.info("[OK] Gemini initialized")
            except:
                self.gemini = None
        else:
            self.gemini = None
        
        self.stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'groq_used': 0,
            'ollama_used': 0,
            'gemini_used': 0
        }
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                logger.info("[OK] Ollama available")
                return True
        except requests.RequestException as e:
            logger.debug(f"Ollama check failed: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error checking Ollama: {e}")
        return False
    
    def process_article(self, article: Dict, context_str: str = "") -> Dict:
        """
        Process article with simple context awareness
        """
        self.stats['total'] += 1
        
        # Build prompt with context
        prompt = self._build_prompt_with_context(article, context_str)
        
        # Try providers: Groq -> Ollama -> Gemini
        result = None
        provider_used = "none"
        
        if self.groq_client:
            result = self._try_groq(prompt)
            if result:
                provider_used = "groq"
                self.stats['groq_used'] += 1
        
        if not result and self.ollama_available:
            result = self._try_ollama(prompt)
            if result:
                provider_used = "ollama"
                self.stats['ollama_used'] += 1
        
        if not result and self.gemini:
            result = self._try_gemini(prompt)
            if result:
                provider_used = "gemini"
                self.stats['gemini_used'] += 1
        
        # Validate and return
        if result and isinstance(result, dict):
            result.setdefault('relevance_score', 0)
            result.setdefault('platform', 'Unknown')
            result.setdefault('model_type', 'Unknown')
            result.setdefault('memory_insight', 'Unknown')
            result.setdefault('dram_impact', 'Unknown')
            result.setdefault('engineering_takeaway', 'Analysis completed')
            
            result['provider_used'] = provider_used
            result['processed_at'] = datetime.now().isoformat()
            
            self.stats['successful'] += 1
            logger.info(f"[+] Score: {result['relevance_score']} via {provider_used}")
            return result
        
        self.stats['failed'] += 1
        return self._get_fallback()
    
    def _build_prompt_with_context(self, article: Dict, context: str) -> str:
        """Build prompt with recent papers context"""
        
        context_section = ""
        if context and len(context) > 50:
            context_section = f"""
RECENT RESEARCH CONTEXT (Last 3 Days):
{context[:800]}

Use this context to:
- Avoid scoring duplicates highly
- Identify new vs. repeated findings
- Compare this work to recent trends

---

"""
        
        return f"""{context_section}ANALYZE THIS NEW ARTICLE:

Title: {article.get('title', 'N/A')}
Summary: {article.get('summary', 'N/A')}

Return JSON with:
- relevance_score: 0-100 
  * 90+: Breakthrough with specific metrics (e.g., "reduces DRAM by 4GB")
  * 70-89: Solid on-device work with memory details
  * 50-69: Edge/mobile AI without detailed memory analysis
  * 30-49: Tangentially related (training-focused)
  * 0-29: Not relevant or cloud-only
  
- platform: Mobile/Laptop/Both/Unknown
- model_type: LLM/Vision/Audio/Multimodal/Other/Unknown
- memory_insight: Specific memory details with numbers or "Unknown"
- dram_impact: High/Medium/Low/Unknown
- engineering_takeaway: One sentence actionable summary

Focus on: on-device inference, memory optimization, DRAM usage, mobile/laptop deployment.

JSON output:"""
    
    def _try_groq(self, prompt: str) -> Optional[Dict]:
        """Try Groq API"""
        for attempt in range(2):
            model = self.groq_models[self.current_model_idx]
            try:
                response = self.groq_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                error_str = str(e).lower()
                if "rate limit" in error_str or "429" in error_str:
                    self.current_model_idx = (self.current_model_idx + 1) % len(self.groq_models)
                    logger.warning(f"Groq rate limit, rotating model")
                    continue
                elif "decommissioned" in error_str or "400" in error_str:
                    self.current_model_idx = (self.current_model_idx + 1) % len(self.groq_models)
                    continue
                logger.debug(f"Groq error: {e}")
                break
        return None
    
    def _try_ollama(self, prompt: str) -> Optional[Dict]:
        """Try Ollama local"""
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
            logger.debug(f"Ollama error: {e}")
        return None
    
    def _try_gemini(self, prompt: str) -> Optional[Dict]:
        """Try Gemini API"""
        try:
            response = self.gemini.generate_content(prompt)
            if response and response.text:
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                return json.loads(text)
        except Exception as e:
            logger.debug(f"Gemini error: {e}")
        return None
    
    def _get_fallback(self) -> Dict:
        """Simple fallback"""
        return {
            "relevance_score": 0,
            "platform": "Unknown",
            "model_type": "Unknown",
            "memory_insight": "Analysis failed",
            "dram_impact": "Unknown",
            "engineering_takeaway": "Unable to process",
            "provider_used": "none",
            "status": "failed",
            "processed_at": datetime.now().isoformat()
        }
    
    def get_statistics(self) -> Dict:
        """Get stats"""
        return {
            'processor_stats': self.stats,
            'success_rate': (
                self.stats['successful'] / self.stats['total'] * 100
                if self.stats['total'] > 0 else 0
            )
        }