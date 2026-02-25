"""
Relevance Judge Module
Filters out irrelevant noise before expensive analysis.
"""
import json
import logging
from src.multimodal_orchestrator import MultiModelOrchestrator

logger = logging.getLogger(__name__)

class RelevanceJudge:
    def __init__(self, orchestrator: MultiModelOrchestrator):
        self.orchestrator = orchestrator

    def is_relevant(self, article: dict) -> bool:
        """
        Quickly judges if an article is related to On-Device AI/Memory.
        Returns True/False.
        """
        # 1. Keyword Heuristic (Fastest)
        text = (article.get('title', '') + " " + article.get('summary', '')).lower()
        keywords = ['on-device', 'mobile', 'edge', 'memory', 'dram', 'quantization', 'npu', 'latency', 'bandwidth']
        
        # If no keywords found, it's likely noise (unless it's a GitHub release)
        if not any(k in text for k in keywords) and "github" not in article.get('source', '').lower():
            logger.info(f"[-] Judge: Keyword reject '{article['title'][:30]}'")
            return False

        # 2. LLM Judge (More accurate)
        summary_text = article.get('summary', '')
        if not summary_text or len(summary_text) < 10:
            summary_text = "No summary provided. Judge based on the Title alone. If the Title mentions a known AI library, score it highly."

        prompt = f"""
        Task: Judge relevance for "On-Device AI Memory/Performance Engineering".
        Title: {article.get('title')}
        Summary: {summary_text[:500]}

        Return JSON: {{"is_relevant": true/false, "reason": "short reason"}}
        """
        
        try:
            # Use a slightly higher temperature for variety in reasoning
            response_text, _ = self.orchestrator.generate(prompt, temperature=0.1, json_mode=True)
            if response_text:
                data = json.loads(response_text)
                is_rel = data.get('is_relevant', False)
                if not is_rel:
                    logger.info(f"[-] Judge: LLM reject '{article['title'][:30]}' ({data.get('reason')})")
                return is_rel
        except Exception as e:
            logger.warning(f"Judge error: {e}. Defaulting to True.")
            return True # Fail open (allow it) if judge crashes

        return True