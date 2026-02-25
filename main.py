"""
ULTIMATE AGI RESEARCH SYSTEM
Combines:
- Playwright: Deep web scraping (full papers)
- CrewAI: Multi-agent intelligent analysis
- AI Council: Consensus verification
- Zero repetition guarantee
"""

# UTF-8 FIX
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import json
import yaml
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/ultimate_agi_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_config(path="config/config.yaml"):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_recent_findings(days: int = 7):
    """Load recent findings for duplicate prevention"""
    from src.history import HistoryManager
    history = HistoryManager()
    
    try:
        with open(history.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            item for item in data
            if 'date' in item and datetime.fromisoformat(item['date']) > cutoff
        ]
        
        logger.info(f"[History] Loaded {len(recent)} papers from last {days} days")
        return recent
        
    except:
        return []


def run_ultimate_agi():
    """
    Ultimate AGI Research Pipeline
    """
    logger.info("="*80)
    logger.info("ULTIMATE AGI RESEARCH SYSTEM")
    logger.info("Playwright + CrewAI + AI Council")
    logger.info("="*80)
    
    start_time = datetime.now()
    
    try:
        # Load config
        config = load_config()
        threshold = config['system']['relevance_threshold']
        
        # Check what's available
        use_playwright = config['system'].get('use_playwright', True)
        use_crewai = config['features'].get('use_crewai', True)  # Slower, optional
        
        logger.info(f"\nConfiguration:")
        logger.info(f"  Threshold: {threshold}")
        logger.info(f"  Playwright: {use_playwright}")
        logger.info(f"  CrewAI: {use_crewai}")
        
        # Import components
        from src.history import HistoryManager
        from src.formatter import ReportFormatter
        from src.mailer import Mailer
        from src.hitl_validator import HITLValidator
        from src.email_and_archive import EmailTracker, ResultsArchiver
        
        # Initialize history and formatter
        history = HistoryManager()
        formatter = ReportFormatter()
        
        # Initialize HITL validator
        hitl = HITLValidator(
            auto_approve_threshold=0.85,
            require_review_score=90
        )
        
        # Initialize email tracker
        email_tracker = EmailTracker()
        
        # Initialize results archiver
        archiver = ResultsArchiver()
        
        try:
            mailer = Mailer(config.get('email', {}))
        except:
            mailer = None
        
        # STAGE 1: Deep Collection with Playwright
        logger.info("\n" + "="*80)
        logger.info("STAGE 1: DEEP WEB SCRAPING")
        logger.info("="*80)
        
        if use_playwright:
            try:
                from src.deep_scraper import fetch_articles_deep
                articles = fetch_articles_deep(config, use_playwright=True)
                logger.info(f"[OK] Playwright scraping complete")
            except Exception as e:
                logger.warning(f"[FALLBACK] Playwright failed: {e}")
                logger.warning("Using basic collector")
                from src.collector import Collector, deduplicate_articles
                collector = Collector()
                articles = collector.fetch_all(config)
                articles = deduplicate_articles(articles)
        else:
            from src.collector import Collector, deduplicate_articles
            collector = Collector()
            articles = collector.fetch_all(config)
            articles = deduplicate_articles(articles)
        
        logger.info(f"Collected: {len(articles)} articles")
        
        if not articles:
            logger.warning("No articles collected")
            return
        
        # STAGE 2: Initialize Vector Store
        logger.info("\n" + "="*80)
        logger.info("STAGE 2: VECTOR STORE INITIALIZATION")
        logger.info("="*80)
        
        from src.qdrant_vector_store import VectorStoreManager
        vector_manager = VectorStoreManager(enabled=config['system'].get('use_vectors', True))
        
        # Also load historical context
        recent_findings = load_recent_findings(days=7)
        
        # STAGE 3: Intelligent Analysis
        logger.info("\n" + "="*80)
        logger.info("STAGE 3: AGI ANALYSIS")
        if use_crewai:
            logger.info("Using: CrewAI (high-value) + AI Council (others)")
        else:
            logger.info("Using: AI Council only")
        logger.info("="*80 + "\n")
        
        # Initialize hybrid system
        from src.crewai_agents import HybridAGISystem
        agi = HybridAGISystem(
            use_crewai=use_crewai,
            use_playwright=use_playwright,
            use_council=True
        )
        
        new_findings = []
        rejected = {'duplicate': 0, 'low_score': 0, 'failed': 0}
        
        for idx, article in enumerate(articles, 1):
            # Safe title
            title = article.get('title', 'Unknown')
            try:
                title_short = title[:60] + "..." if len(title) > 60 else title
            except:
                title_short = "Paper with special chars"
            
            logger.info(f"\n[{idx}/{len(articles)}] {title_short}")
            
            # Show if we have full text
            has_full = article.get('has_full_text', False)
            full_text_len = len(article.get('full_text', ''))
            if has_full:
                logger.info(f"  [Full Text] {full_text_len} chars extracted")
            
            try:
                # SEMANTIC DUPLICATE CHECK with Qdrant
                should_process, reason = vector_manager.check_and_add(article)
                
                if not should_process and reason == "duplicate":
                    rejected['duplicate'] += 1
                    logger.info(f"  [SEMANTIC DUPLICATE] Vector similarity >95%")
                    continue
                
                # Get vector context for better analysis
                vector_context = vector_manager.get_context(article)
                
                # Check for duplicate first
                try:
                    duplicate_found = any(
                        str(title).lower() == str(p.get('title', '')).lower()
                        for p in recent_findings
                    )
                    if duplicate_found:
                        rejected['duplicate'] += 1
                        logger.info(f"  [DUPLICATE] Already in history")
                        continue
                except:
                    pass
                
                # Analyze with AGI
                analysis = agi.analyze_paper(article, recent_findings)
                
                if not analysis:
                    rejected['failed'] += 1
                    logger.warning(f"  [FAILED] Analysis error")
                    continue
                
                # HITL VALIDATION
                hitl_status, hitl_reason, validated_analysis = hitl.validate_paper(article, analysis)
                
                if hitl_status == 'needs_review':
                    # Paper needs human review - skip for now
                    logger.info(f"  [HITL] {hitl_reason}")
                    continue
                
                analysis = validated_analysis  # Use validated version
                score = analysis.get('relevance_score', 0)
                
                # Check if from CrewAI
                if 'crew_metadata' in analysis:
                    logger.info(f"  [CrewAI] Multi-agent analysis")
                elif 'council_metadata' in analysis:
                    meta = analysis.get('council_metadata', {})
                    logger.info(f"  [Council] {meta.get('consensus_status', 'unknown')} consensus")
                
                if score >= threshold:
                    merged = {**article, **analysis}
                    new_findings.append(merged)
                    logger.info(f"  [ACCEPTED] Score: {score}")
                else:
                    rejected['low_score'] += 1
                    logger.info(f"  [REJECTED] Score: {score} (below {threshold})")
                    
            except Exception as e:
                logger.error(f"  [ERROR] {str(e)[:100]}")
                rejected['failed'] += 1
        
        # STAGE 4: Results & Report
        logger.info("\n" + "="*80)
        logger.info("STAGE 4: RESULTS")
        logger.info("="*80)
        
        logger.info(f"Total Analyzed: {len(articles)}")
        logger.info(f"New Findings: {len(new_findings)}")
        logger.info(f"Duplicates: {rejected['duplicate']}")
        logger.info(f"Below Threshold: {rejected['low_score']}")
        logger.info(f"Failed: {rejected['failed']}")
        
        if new_findings:
            # Save
            history.save_insights(new_findings)
            logger.info(f"\n[OK] Saved {len(new_findings)} new findings")
            
            # ARCHIVE ALL RESULTS
            logger.info("\n" + "="*80)
            logger.info("ARCHIVING RESULTS")
            logger.info("="*80)
            
            session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Compile session statistics
            session_stats = {
                'total_analyzed': len(articles),
                'new_findings': len(new_findings),
                'rejected': rejected,
                'vector_stats': vector_manager.get_stats(),
                'hitl_stats': hitl.get_statistics()
            }
            
            archive_file = archiver.archive_session_results(
                new_findings,
                session_stats,
                session_id
            )
            logger.info(f"[OK] Complete analysis archived: {archive_file}")
            
            # SMART EMAIL: Only send papers NOT yet emailed
            logger.info("\n" + "="*80)
            logger.info("EMAIL PREPARATION")
            logger.info("="*80)
            
            unsent_papers = email_tracker.filter_unsent_papers(new_findings)
            
            if unsent_papers:
                logger.info(f"Papers to email: {len(unsent_papers)} (skipping {len(new_findings) - len(unsent_papers)} already sent)")

                # MULTI-FORMAT REPORT GENERATION
                logger.info("\n" + "="*80)
                logger.info("MULTI-FORMAT REPORT GENERATION")
                logger.info("="*80)

                try:
                    from src.multiformat_integration import generate_multiformat_email_report

                    # Generate all formats (email, PDF, PowerPoint, Podcast, Transcript, Summary)
                    html_report, attachments, gen_results = generate_multiformat_email_report(unsent_papers)

                    logger.info(f"\n[MultiFormat] Generated {len(attachments)} attachments:")
                    for att in attachments:
                        logger.info(f"  - {os.path.basename(att)}")

                except Exception as e:
                    logger.warning(f"[MultiFormat] Generation failed, falling back to basic formatter: {e}")
                    html_report = formatter.build_html(unsent_papers)
                    attachments = []

                # Generate text summary for logging
                text_summary = formatter.build_text_summary(unsent_papers)
                logger.info(text_summary)

                # Send/Save
                if mailer:
                    if mailer.send(html_report, attachments=attachments if attachments else None):
                        logger.info("[OK] Email sent")

                        # Mark as sent ONLY after successful email
                        email_tracker.mark_as_sent(unsent_papers)
                        logger.info(f"[EmailTracker] Marked {len(unsent_papers)} papers as sent")
                    else:
                        logger.error("[FAIL] Email failed - papers NOT marked as sent")
                else:
                    os.makedirs("reports", exist_ok=True)
                    report_file = f"reports/ultimate_agi_{session_id}.html"
                    with open(report_file, 'w', encoding='utf-8') as f:
                        f.write(html_report)
                    logger.info(f"[OK] Report saved: {report_file}")

                    # Also save attachment list for reference
                    if attachments:
                        attachments_file = f"reports/ultimate_agi_{session_id}_attachments.txt"
                        with open(attachments_file, 'w', encoding='utf-8') as f:
                            f.write("Generated Report Files:\n")
                            f.write("="*50 + "\n")
                            for att in attachments:
                                f.write(f"{att}\n")
                        logger.info(f"[OK] Attachments list saved: {attachments_file}")

                    # Mark as sent even for file save
                    email_tracker.mark_as_sent(unsent_papers)
            else:
                logger.info("All papers already sent previously - no email needed")
        
        else:
            logger.info("\n[NO NEW FINDINGS]")
            logger.info("All papers were duplicates or below threshold")
        
        # Final stats
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("\n" + "="*80)
        logger.info("ULTIMATE AGI PIPELINE COMPLETE")
        logger.info("="*80)
        logger.info(f"Runtime: {duration:.1f}s ({duration/60:.1f} min)")
        logger.info(f"New Findings: {len(new_findings)}")
        logger.info(f"Duplicates Prevented: {rejected['duplicate']}")
        
        # Vector store stats
        vector_stats = vector_manager.get_stats()
        if vector_stats.get('enabled'):
            logger.info(f"\nVector Store:")
            logger.info(f"  Total Papers: {vector_stats.get('total_papers', 0)}")
            logger.info(f"  Semantic Duplicates Found: {vector_stats.get('duplicates', 0)}")
            logger.info(f"  Similarity Searches: {vector_stats.get('searches', 0)}")
        
        # HITL stats
        hitl_stats = hitl.get_statistics()
        logger.info(f"\nHITL Validation:")
        logger.info(f"  Total Checked: {hitl_stats.get('total_checked', 0)}")
        logger.info(f"  Auto-Approved: {hitl_stats.get('auto_approved', 0)} ({hitl_stats.get('auto_approve_rate', 0):.1f}%)")
        logger.info(f"  Pending Review: {hitl_stats.get('currently_pending', 0)}")
        logger.info(f"  Human Approved: {hitl_stats.get('human_approved', 0)}")
        logger.info(f"  Human Rejected: {hitl_stats.get('human_rejected', 0)}")
        
        # Email tracker stats
        email_stats = email_tracker.get_statistics()
        logger.info(f"\nEmail Tracker:")
        logger.info(f"  Total Papers Sent (lifetime): {email_stats.get('total_papers_sent', 0)}")
        
        # Archiver stats
        archive_stats = archiver.get_statistics()
        logger.info(f"\nResults Archive:")
        logger.info(f"  Archive Directory: {archive_stats.get('results_dir', 'N/A')}")
        logger.info(f"  Daily Sessions: {archive_stats.get('daily_sessions', 0)}")
        logger.info(f"  Monthly Archives: {archive_stats.get('monthly_archives', 0)}")
        
        logger.info("="*80)
        
    except KeyboardInterrupt:
        logger.warning("\n[INTERRUPTED]")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"\n[CRITICAL ERROR] {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "help":
        print("""
ULTIMATE AGI RESEARCH SYSTEM

Usage:
  python main_ultimate.py           Run full pipeline
  python main_ultimate.py help      Show help

Components:
  1. Playwright - Deep web scraping (full papers, not summaries)
  2. CrewAI - Multi-agent intelligent analysis (optional)
  3. AI Council - Multi-AI consensus verification
  
Features:
  - Full paper text extraction (not just abstracts)
  - 4 specialized AI agents (if CrewAI enabled)
  - 3-AI consensus verification (Groq/Ollama/Gemini)
  - Zero repetition guarantee
  - Beautiful modern reports (top 6)
  
Setup:
  pip install playwright crewai crewai-tools
  playwright install
        """)
    else:
        run_ultimate_agi()
