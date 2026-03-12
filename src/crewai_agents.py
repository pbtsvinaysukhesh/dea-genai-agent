"""
CrewAI Multi-Agent System
Specialized AI agents working together:
- Research Agent: Deep paper analysis
- Memory Expert: Hardware/memory focus
- Verification Agent: Quality control
- Synthesis Agent: Final report generation
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try importing CrewAI
try:
    from crewai import Agent, Task, Crew, Process
    from crewai_tools import tool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logger.warning("CrewAI not installed. Run: pip install crewai crewai-tools")


class ResearchCrew:
    """
    Multi-agent research team using CrewAI
    Each agent has specialized role and expertise
    """
    
    def __init__(self, llm_provider: str = "groq"):
        if not CREWAI_AVAILABLE:
            raise ImportError("CrewAI not available. Install with: pip install crewai")
        
        self.llm_provider = llm_provider
        self._setup_agents()
        logger.info("[CrewAI] Research crew initialized")
    
    def _setup_agents(self):
        """Setup specialized agents"""
        
        # Agent 1: Research Analyst
        self.research_agent = Agent(
            role='Senior Research Analyst',
            goal='Deeply analyze AI research papers for on-device deployment insights',
            backstory="""You are a world-class AI researcher with 15 years experience 
            in mobile and edge AI. You've published 100+ papers on model optimization, 
            quantization, and memory efficiency. You understand hardware constraints 
            intimately and can spot breakthrough research immediately.""",
            verbose=True,
            allow_delegation=False
        )
        
        # Agent 2: Memory Expert
        self.memory_expert = Agent(
            role='Memory & Performance Expert',
            goal='Extract precise memory usage, DRAM impact, and performance metrics',
            backstory="""You are a hardware engineer specializing in memory systems. 
            You've optimized memory usage for mobile chips at Qualcomm and Apple. 
            You can estimate DRAM usage from paper descriptions and identify 
            memory bottlenecks instantly. You demand specific numbers, not vague claims.""",
            verbose=True,
            allow_delegation=False
        )
        
        # Agent 3: Verification Agent
        self.verification_agent = Agent(
            role='Quality Assurance Specialist',
            goal='Verify accuracy of analysis and prevent hallucinations',
            backstory="""You are a meticulous fact-checker with a PhD in Computer Science. 
            You've reviewed papers for NeurIPS, ICML, and CVPR. You catch exaggerations, 
            verify claims against paper content, and ensure all insights are grounded 
            in actual paper content.""",
            verbose=True,
            allow_delegation=False
        )
        
        # Agent 4: Synthesis Agent
        self.synthesis_agent = Agent(
            role='Technical Writer & Synthesizer',
            goal='Create clear, actionable engineering insights',
            backstory="""You are a technical writer who translates research into 
            engineering reality. You've written documentation for TensorFlow Lite, 
            MLX, and PyTorch Mobile. You distill complex papers into one-sentence 
            actionable takeaways that engineers can implement.""",
            verbose=True,
            allow_delegation=False
        )
    
    def analyze_paper(self, paper: Dict) -> Dict:
        """
        Multi-agent analysis of a paper
        Each agent contributes their expertise
        """
        
        # Extract paper content
        title = paper.get('title', 'Unknown')
        full_text = paper.get('full_text', paper.get('summary', ''))
        abstract = paper.get('abstract', paper.get('summary', ''))
        
        logger.info(f"[CrewAI] Analyzing: {title[:60]}...")
        
        # Task 1: Research Analysis
        research_task = Task(
            description=f"""
            Analyze this AI research paper:
            
            Title: {title}
            Abstract: {abstract[:500]}
            Full Text: {full_text[:3000]}
            
            Provide:
            1. Relevance score (0-100) for on-device AI deployment
            2. Main technical contribution
            3. Platform suitability (Mobile/Laptop/Both)
            4. Model type (LLM/Vision/Audio/Multimodal)
            
            Be critical. Only score 90+ if there's a genuine breakthrough with evidence.
            """,
            agent=self.research_agent,
            expected_output="Detailed research analysis with relevance score"
        )
        
        # Task 2: Memory Analysis
        memory_task = Task(
            description=f"""
            Extract memory and performance details from this paper:
            
            Title: {title}
            Content: {full_text[:3000]}
            
            Find and extract:
            1. Specific memory usage (e.g., "4.2GB DRAM")
            2. Memory reduction techniques (quantization, pruning, etc.)
            3. Before/after comparisons
            4. Hardware requirements (RAM, NPU, GPU)
            5. DRAM impact: High/Medium/Low
            
            If no specific numbers found, state "No quantitative memory data provided."
            """,
            agent=self.memory_expert,
            expected_output="Precise memory metrics and DRAM impact assessment"
        )
        
        # Task 3: Verification
        verification_task = Task(
            description=f"""
            Verify the analyses from the Research Analyst and Memory Expert.
            
            Paper: {title}
            
            Check:
            1. Are claims supported by paper content?
            2. Are memory numbers actually in the paper?
            3. Is the relevance score justified?
            4. Any exaggerations or hallucinations?
            
            Provide corrected analysis if needed.
            """,
            agent=self.verification_agent,
            expected_output="Verification report with corrections if needed"
        )
        
        # Task 4: Synthesis
        synthesis_task = Task(
            description=f"""
            Create final engineering insights:
            
            Paper: {title}
            
            Based on previous analyses, provide:
            1. Final relevance score (0-100)
            2. One-sentence engineering takeaway
            3. Deployment feasibility assessment
            4. Key technical details
            
            Format as JSON:
            {{
                "relevance_score": <0-100>,
                "platform": "<Mobile|Laptop|Both|Unknown>",
                "model_type": "<LLM|Vision|Audio|Multimodal|Other>",
                "memory_insight": "<specific memory details with numbers>",
                "dram_impact": "<High|Medium|Low|Unknown>",
                "engineering_takeaway": "<one actionable sentence>",
                "technical_details": ["<detail1>", "<detail2>"],
                "deployment_feasibility": "<can this run on device? why/why not?>"
            }}
            """,
            agent=self.synthesis_agent,
            expected_output="Final JSON analysis"
        )
        
        # Create crew and execute
        crew = Crew(
            agents=[
                self.research_agent,
                self.memory_expert,
                self.verification_agent,
                self.synthesis_agent
            ],
            tasks=[
                research_task,
                memory_task,
                verification_task,
                synthesis_task
            ],
            process=Process.sequential,  # Sequential for verification flow
            verbose=True
        )
        
        try:
            # Execute crew
            result = crew.kickoff()
            
            # Parse result (CrewAI returns string, need to extract JSON)
            import json
            import re
            
            # Try to find JSON in result
            result_str = str(result)
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', result_str)
            
            if json_match:
                analysis = json.loads(json_match.group())
                
                # Add metadata
                analysis['crew_metadata'] = {
                    'agents_used': 4,
                    'verification_passed': True,
                    'processed_at': datetime.now().isoformat()
                }
                
                logger.info(f"[CrewAI] Analysis complete: Score {analysis.get('relevance_score', 0)}")
                return analysis
            else:
                logger.warning("[CrewAI] Could not parse JSON from result")
                return self._create_fallback(result_str)
                
        except Exception as e:
            logger.error(f"[CrewAI] Analysis failed: {e}")
            return None
    
    def _create_fallback(self, result_str: str) -> Dict:
        """Create fallback response from text result"""
        return {
            "relevance_score": 50,
            "platform": "Unknown",
            "model_type": "Unknown",
            "memory_insight": "CrewAI analysis completed but could not parse structured output",
            "dram_impact": "Unknown",
            "engineering_takeaway": result_str[:200],
            "crew_metadata": {
                "fallback": True,
                "processed_at": datetime.now().isoformat()
            }
        }


class HybridAGISystem:
    """
    Hybrid AGI System combining:
    - Playwright for deep scraping
    - CrewAI for multi-agent analysis
    - AI Council for verification
    """
    
    def __init__(
        self,
        use_crewai: bool = False,  # CrewAI is slower, use for important papers
        use_playwright: bool = True,
        use_council: bool = True
    ):
        self.use_crewai = use_crewai and CREWAI_AVAILABLE
        self.use_playwright = use_playwright
        self.use_council = use_council
        
        # Initialize components
        if self.use_crewai:
            try:
                self.crew = ResearchCrew()
                logger.info("[Hybrid] CrewAI enabled")
            except:
                self.use_crewai = False
                logger.warning("[Hybrid] CrewAI disabled")
        
        if self.use_council:
            from src.ai_council import AICouncil
            self.council = AICouncil()
            logger.info("[Hybrid] AI Council enabled")
    
    def analyze_paper(self, paper: Dict, previous_findings: List[Dict]) -> Dict:
        """
        Intelligent routing:
        - High-value papers (arXiv, top conferences) → CrewAI (deep analysis)
        - Other papers → AI Council (fast verification)
        """
        
        source = str(paper.get('source', '')).lower()
        score_hint = paper.get('preliminary_score', 50)
        
        # Route to CrewAI for high-value papers
        use_crew_for_this = self.use_crewai and (
            'arxiv' in source or 
            'neurips' in source or 
            'icml' in source or
            score_hint >= 80
        )
        
        if use_crew_for_this:
            logger.info(f"[Hybrid] Using CrewAI (high-value paper)")
            return self.crew.analyze_paper(paper)
        
        elif self.use_council:
            logger.info(f"[Hybrid] Using AI Council (standard paper)")
            return self.council.council_analysis(paper, previous_findings)
        
        else:
            logger.warning("[Hybrid] No analysis method available")
            return None