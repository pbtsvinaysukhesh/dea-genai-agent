"""
FINAL FIX: Correct Gemini import + _reasoning field fix
"""

import os
import json
import time
import logging
from typing import Dict, Optional, List, Tuple
from enum import Enum
from datetime import datetime
import requests
from groq import Groq

# CORRECT Gemini import
try:
    import google.genai as genai  # NOT google.genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    GROQ = "groq"
    OLLAMA = "ollama"
    GEMINI = "gemini"


class ModelStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class GroqClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = Groq(api_key=api_key)
        self.model_pool = [
            "llama-3.1-8b-instant", 
            "mixtral-8x7b-32768", 
            "llama-3.3-70b-versatile",
            "gemma2-9b-it"
        ]
        self.current_idx = 0

    def check_health(self) -> ModelStatus:
        try:
            self.client.models.list()
            return ModelStatus.HEALTHY
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return ModelStatus.FAILED

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        for _ in range(2):
            model = self.model_pool[self.current_idx]
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=kwargs.get('temperature', 0.1),
                    response_format={"type": "json_object"} if kwargs.get('json_mode', True) else None,
                )
                return response.choices[0].message.content
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    self.current_idx = (self.current_idx + 1) % len(self.model_pool)
                    logger.warning(f"🔄 Groq {model} limited. Rotating to {self.model_pool[self.current_idx]}")
                    continue
                logger.error(f"Groq error: {e}")
                return None
        return None


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.available_models = []
        self.default_model = "gemma3:4b"
        self._load_available_models()
    
    def _load_available_models(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.available_models = [m['name'] for m in data.get('models', [])]
                logger.info(f"Ollama models available: {self.available_models}")
        except Exception as e:
            logger.warning(f"Could not load Ollama models: {e}")
    
    def generate(self, prompt: str, model: str = None, temperature: float = 0.1, format: str = "json") -> Optional[str]:
        model = model or self.default_model
        
        if model not in self.available_models:
            logger.warning(f"Model {model} not found")
            return None
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": format,
            "options": {"temperature": temperature, "top_p": 0.95}
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get('response', '')
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return None
    
    def check_health(self) -> ModelStatus:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return ModelStatus.HEALTHY if response.status_code == 200 else ModelStatus.DEGRADED
        except:
            return ModelStatus.FAILED


class GeminiClient:
    def __init__(self, api_key: str):
        if not GEMINI_AVAILABLE:
            raise ImportError("google.genai not available")
        self.api_key = api_key
        genai.configure(api_key=api_key)  # CORRECT: genai.configure
        self.default_model = "gemini-2.5-flash"
        self.model = None
    
    def generate(self, prompt: str, model: str = None, temperature: float = 0.1, system_instruction: str = None) -> Optional[str]:
        model_name = model or self.default_model
        try:
            if self.model is None or self.model.model_name != model_name:
                self.model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={"response_mime_type": "application/json", "temperature": temperature},
                    system_instruction=system_instruction
                )
            response = self.model.generate_content(prompt)
            return response.text if response else None
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return None
    
    def check_health(self) -> ModelStatus:
        try:
            test_model = genai.GenerativeModel("gemini-2.5-flash")
            response = test_model.generate_content("Say OK")
            return ModelStatus.HEALTHY if response else ModelStatus.FAILED
        except:
            return ModelStatus.FAILED


class MultiModelOrchestrator:
    def __init__(self, groq_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None,
                 ollama_url: str = "http://localhost:11434", enable_groq: bool = True,
                 enable_ollama: Optional[bool] = None, enable_gemini: bool = True):

        # If enable_ollama not explicitly set, read from environment variable
        if enable_ollama is None:
            enable_ollama = os.getenv("ENABLE_OLLAMA", "true").lower() == "true"

        self.providers: Dict[ModelProvider, any] = {}
        
        if enable_groq:
            groq_key = groq_api_key or os.getenv("GROQ_API_KEY")
            if groq_key:
                self.providers[ModelProvider.GROQ] = GroqClient(groq_key)
                logger.info("✓ Groq provider initialized")
        
        if enable_ollama:
            ollama_client = OllamaClient(ollama_url)
            if ollama_client.check_health() == ModelStatus.HEALTHY:
                self.providers[ModelProvider.OLLAMA] = ollama_client
                logger.info("✓ Ollama provider initialized")
        
        if enable_gemini and GEMINI_AVAILABLE:
            gemini_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")
            if gemini_key:
                try:
                    self.providers[ModelProvider.GEMINI] = GeminiClient(gemini_key)
                    logger.info("✓ Gemini provider initialized")
                except Exception as e:
                    logger.warning(f"Gemini init failed: {e}")
        
        if not self.providers:
            raise ValueError("No model providers available!")
        
        self.priority_order = [ModelProvider.GROQ, ModelProvider.OLLAMA, ModelProvider.GEMINI]
        self.stats = {
            'total_requests': 0, 'successful_requests': 0, 'failed_requests': 0,
            'provider_usage': {p.value: 0 for p in ModelProvider},
            'provider_failures': {p.value: 0 for p in ModelProvider},
            'avg_response_time': {}
        }
        self.health_status = {}
        self.last_health_check = {}
    
    def generate(self, prompt: str, system_instruction: str = None, temperature: float = 0.1,
                 max_tokens: int = 4096, json_mode: bool = True, 
                 preferred_provider: Optional[ModelProvider] = None) -> Tuple[Optional[str], ModelProvider]:
        
        self.stats['total_requests'] += 1
        
        providers_to_try = ([preferred_provider] + [p for p in self.priority_order if p != preferred_provider]) \
                           if preferred_provider and preferred_provider in self.providers else self.priority_order
        
        for provider_type in providers_to_try:
            if provider_type not in self.providers:
                continue
            
            if not self._is_provider_healthy(provider_type):
                logger.warning(f"Provider {provider_type.value} unhealthy, skipping")
                continue
            
            provider = self.providers[provider_type]
            logger.info(f"Attempting generation with {provider_type.value}")
            start_time = time.time()
            
            try:
                if provider_type == ModelProvider.GROQ:
                    response = provider.generate(prompt=prompt, temperature=temperature, json_mode=json_mode)
                elif provider_type == ModelProvider.OLLAMA:
                    response = provider.generate(prompt=prompt, temperature=temperature, format="json" if json_mode else "")
                elif provider_type == ModelProvider.GEMINI:
                    response = provider.generate(prompt=prompt, temperature=temperature, system_instruction=system_instruction)
                
                if response:
                    elapsed = time.time() - start_time
                    self.stats['successful_requests'] += 1
                    self.stats['provider_usage'][provider_type.value] += 1
                    if provider_type.value not in self.stats['avg_response_time']:
                        self.stats['avg_response_time'][provider_type.value] = []
                    self.stats['avg_response_time'][provider_type.value].append(elapsed)
                    logger.info(f"✓ Success with {provider_type.value} ({elapsed:.2f}s)")
                    return response, provider_type
                    
            except Exception as e:
                logger.error(f"Error with {provider_type.value}: {e}")
                self.stats['provider_failures'][provider_type.value] += 1
                self._mark_provider_unhealthy(provider_type)
        
        self.stats['failed_requests'] += 1
        logger.error("All providers failed!")
        return None, None
    
    def _is_provider_healthy(self, provider_type: ModelProvider) -> bool:
        now = time.time()
        last_check = self.last_health_check.get(provider_type, 0)
        if now - last_check < 60:
            return self.health_status.get(provider_type, True)
        if provider_type not in self.providers:
            return False
        provider = self.providers[provider_type]
        status = provider.check_health()
        self.health_status[provider_type] = (status == ModelStatus.HEALTHY)
        self.last_health_check[provider_type] = now
        return self.health_status[provider_type]
    
    def _mark_provider_unhealthy(self, provider_type: ModelProvider):
        self.health_status[provider_type] = False
        self.last_health_check[provider_type] = time.time()
    
    def get_statistics(self) -> Dict:
        stats = self.stats.copy()
        for provider, times in self.stats['avg_response_time'].items():
            if times:
                stats[f'{provider}_avg_time'] = sum(times) / len(times)
        if stats['total_requests'] > 0:
            stats['success_rate'] = (stats['successful_requests'] / stats['total_requests'] * 100)
        return stats
    
    def get_health_status(self) -> Dict[str, str]:
        status = {}
        for provider_type in ModelProvider:
            if provider_type in self.providers:
                is_healthy = self._is_provider_healthy(provider_type)
                status[provider_type.value] = "healthy" if is_healthy else "unhealthy"
            else:
                status[provider_type.value] = "disabled"
        return status


class EnterpriseAIProcessor:
    """
    FINAL FIXED VERSION:
    - Correct Gemini import
    - Includes _reasoning in prompt
    - Fixed context variable
    """
    
    def __init__(self, groq_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None,
                 ollama_url: str = "http://localhost:11434", knowledge_manager = None):
        
        self.orchestrator = MultiModelOrchestrator(
            groq_api_key=groq_api_key, 
            gemini_api_key=gemini_api_key, 
            ollama_url=ollama_url
        )
        self.knowledge_manager = knowledge_manager
        self.system_instruction = self._build_system_instruction()
        self.stats = {'total_processed': 0, 'successful': 0, 'failed': 0}
    
    def _build_system_instruction(self) -> str:
        return """You are a Senior AI Performance Engineer specializing in on-device AI.

CRITICAL: ALWAYS return valid JSON with ALL required fields including _reasoning.

Required JSON Schema:
{
  "_reasoning": "Step-by-step thought process explaining the score",
  "relevance_score": 0-100 integer,
  "platform": "Mobile|Laptop|Both|IoT|Edge|Unknown",
  "model_type": "LLM|Vision|Audio|Multimodal|Other|Unknown",
  "memory_insight": "Specific technical details about memory/DRAM",
  "dram_impact": "High|Medium|Low|Unknown",
  "engineering_takeaway": "One clear actionable sentence"
}

SCORING:
- 90-100: Breakthrough on-device memory work
- 70-89: Solid on-device AI with memory implications
- 50-69: Edge/mobile AI without detailed memory
- 30-49: Tangentially related
- 0-29: Not relevant or cloud-only"""
    
    def process_article(self, article: Dict, context_str: str = "", retry_count: int = 0) -> Dict:
        self.stats['total_processed'] += 1
        
        # Get Graph RAG context
        context = ""
        if self.knowledge_manager:
            try:
                if hasattr(self.knowledge_manager, 'get_contextual_knowledge'):
                    context = self.knowledge_manager.get_contextual_knowledge(
                        query_paper=article, context_days=30
                    )
                    logger.info("✓ Retrieved Graph RAG context")
                else:
                    context = self.knowledge_manager.load_recent_context(days=7) if hasattr(self.knowledge_manager, 'load_recent_context') else ""
            except Exception as e:
                logger.warning(f"Failed to retrieve context: {e}")
        
        if not context and context_str:
            context = context_str
        
        # Build FIXED prompt
        prompt = self._build_prompt_with_reasoning(article, context)
        
        try:
            response_text, provider_used = self.orchestrator.generate(
                prompt=prompt,
                system_instruction=self.system_instruction,
                temperature=0.1,
                json_mode=True
            )
            
            if not response_text:
                raise ValueError("Empty response from all providers")
            
            result = self._parse_response(response_text)
            
            # ENSURE _reasoning exists
            if '_reasoning' not in result or not result['_reasoning']:
                result['_reasoning'] = "Analysis completed"
            
            result['provider_used'] = provider_used.value if provider_used else "unknown"
            result['processed_at'] = datetime.now().isoformat()
            
            # Add to knowledge graph
            if self.knowledge_manager and result.get('relevance_score', 0) >= 60:
                try:
                    self.knowledge_manager.add_paper({**article, **result}, embedding=None)
                    logger.info("✓ Added to Knowledge Graph")
                except Exception as e:
                    logger.warning(f"KG update failed: {e}")
            
            self.stats['successful'] += 1
            logger.info(f"✓ Processed with {provider_used.value if provider_used else 'unknown'}")
            return result
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            self.stats['failed'] += 1
            if retry_count < 2:
                time.sleep(2)
                return self.process_article(article, context_str, retry_count + 1)
            return self._get_fallback_response(str(e))
    
    def _build_prompt_with_reasoning(self, article: Dict, context: str) -> str:
        """FIXED: Explicitly asks for _reasoning field"""
        context_section = f"\n{context}\n" if context else "\nNo historical context.\n"
        
        return f"""{context_section}

ANALYZE THIS ARTICLE:

Title: {article.get('title', 'N/A')}
Authors: {article.get('authors', 'Unknown')}
Summary: {article.get('summary', 'N/A')}

REQUIRED JSON OUTPUT (include ALL fields):
{{
  "_reasoning": "<Explain: Why is this on-device relevant? What memory implications? Why this score?>",
  "relevance_score": <0-100 integer>,
  "platform": "<Mobile|Laptop|Both|IoT|Edge|Unknown>",
  "model_type": "<LLM|Vision|Audio|Multimodal|Other|Unknown>",
  "memory_insight": "<Specific memory/DRAM details or 'Unknown'>",
  "dram_impact": "<High|Medium|Low|Unknown>",
  "engineering_takeaway": "<One actionable sentence>"
}}

CRITICAL: Must include _reasoning field explaining your score!"""
    
    def _parse_response(self, response_text: str) -> Dict:
        try:
            return json.loads(response_text)
        except:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response_text[start:end])
            raise ValueError("Could not parse JSON")
    
    def _get_fallback_response(self, error: str) -> Dict:
        return {
            "_reasoning": f"Analysis failed: {error}",
            "relevance_score": 0,
            "platform": "Unknown",
            "model_type": "Unknown",
            "memory_insight": f"Analysis unavailable: {error}",
            "dram_impact": "Unknown",
            "engineering_takeaway": f"Unable to process: {error}",
            "status": "failed",
            "error_reason": error,
            "processed_at": datetime.now().isoformat()
        }
    
    def get_statistics(self) -> Dict:
        return {
            'processor_stats': self.stats,
            'orchestrator_stats': self.orchestrator.get_statistics(),
            'provider_health': self.orchestrator.get_health_status()
        }