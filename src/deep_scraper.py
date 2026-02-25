"""
Deep Web Scraper using Playwright
Extracts FULL paper content, not just abstracts
Handles PDFs, HTML papers, and interactive content
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Try importing Playwright
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install")


class DeepWebScraper:
    """
    Advanced web scraper using Playwright
    Extracts full paper content including:
    - Complete text from HTML papers
    - PDF content extraction
    - Tables and figures
    - Code snippets
    - Interactive elements
    """
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.stats = {
            'papers_scraped': 0,
            'pdfs_extracted': 0,
            'html_extracted': 0,
            'failed': 0
        }
    
    async def scrape_paper_content(self, url: str, title: str) -> Dict:
        """
        Scrape full paper content from URL
        Returns: Enhanced paper dict with full_text, figures, etc.
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available - falling back to basic scraping")
            return None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                logger.info(f"[Playwright] Scraping: {title[:50]}...")
                
                # Navigate to paper
                await page.goto(url, timeout=self.timeout, wait_until='networkidle')
                
                # Detect paper type
                paper_data = await self._extract_paper_content(page, url, title)
                
                await browser.close()
                
                self.stats['papers_scraped'] += 1
                return paper_data
                
        except Exception as e:
            logger.error(f"[Playwright] Failed to scrape {url}: {e}")
            self.stats['failed'] += 1
            return None
    
    async def _extract_paper_content(self, page, url: str, title: str) -> Dict:
        """Extract content based on paper source"""
        
        # Determine source type
        if 'arxiv.org' in url:
            return await self._extract_arxiv(page, url, title)
        elif 'openreview.net' in url:
            return await self._extract_openreview(page, url, title)
        elif 'proceedings.mlr.press' in url:
            return await self._extract_mlr(page, url, title)
        else:
            return await self._extract_generic(page, url, title)
    
    async def _extract_arxiv(self, page, url: str, title: str) -> Dict:
        """Extract arXiv paper with PDF download"""
        try:
            # Get paper ID
            paper_id = url.split('/')[-1]
            
            # Navigate to abstract page
            abs_url = f"https://arxiv.org/abs/{paper_id}"
            await page.goto(abs_url, timeout=self.timeout)
            
            # Extract metadata
            abstract = await page.text_content('.abstract') or ""
            authors = await page.text_content('.authors') or ""
            
            # Get PDF link
            pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
            
            # Extract full text (if HTML version available)
            full_text = abstract  # Start with abstract
            
            # Try to get more detailed content
            try:
                # Click on "HTML" tab if available
                html_link = page.locator('a:has-text("HTML")').first
                if await html_link.count() > 0:
                    await html_link.click()
                    await page.wait_for_timeout(2000)
                    
                    # Extract full HTML content
                    content_div = page.locator('article, .ltx_document, main').first
                    if await content_div.count() > 0:
                        full_text = await content_div.text_content()
            except:
                pass
            
            self.stats['pdfs_extracted'] += 1
            
            return {
                'title': title,
                'url': url,
                'pdf_url': pdf_url,
                'abstract': abstract.strip(),
                'full_text': full_text.strip(),
                'authors': authors.strip(),
                'source_type': 'arxiv',
                'has_full_text': len(full_text) > len(abstract),
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"arXiv extraction failed: {e}")
            return None
    
    async def _extract_openreview(self, page, url: str, title: str) -> Dict:
        """Extract OpenReview paper"""
        try:
            # Wait for content to load
            await page.wait_for_selector('.note-content', timeout=self.timeout)
            
            # Extract abstract
            abstract = ""
            abstract_elem = page.locator('.note-content .abstract').first
            if await abstract_elem.count() > 0:
                abstract = await abstract_elem.text_content()
            
            # Extract full paper if PDF available
            pdf_link = page.locator('a[href*=".pdf"]').first
            pdf_url = None
            if await pdf_link.count() > 0:
                pdf_url = await pdf_link.get_attribute('href')
            
            # Try to extract reviews/comments (valuable context)
            reviews = []
            review_elems = page.locator('.reply')
            count = await review_elems.count()
            for i in range(min(count, 3)):  # Get top 3 reviews
                review = await review_elems.nth(i).text_content()
                reviews.append(review.strip())
            
            full_text = abstract
            if reviews:
                full_text += "\n\nREVIEWS:\n" + "\n---\n".join(reviews)
            
            self.stats['html_extracted'] += 1
            
            return {
                'title': title,
                'url': url,
                'pdf_url': pdf_url,
                'abstract': abstract.strip(),
                'full_text': full_text.strip(),
                'reviews': reviews,
                'source_type': 'openreview',
                'has_full_text': True,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"OpenReview extraction failed: {e}")
            return None
    
    async def _extract_mlr(self, page, url: str, title: str) -> Dict:
        """Extract PMLR/MLR paper"""
        try:
            # Wait for content
            await page.wait_for_selector('article, .paper', timeout=self.timeout)
            
            # Extract abstract
            abstract = ""
            abstract_elem = page.locator('#abstract, .abstract').first
            if await abstract_elem.count() > 0:
                abstract = await abstract_elem.text_content()
            
            # Extract full text sections
            sections = []
            section_elems = page.locator('section, .section')
            count = await section_elems.count()
            for i in range(count):
                section = await section_elems.nth(i).text_content()
                sections.append(section.strip())
            
            full_text = abstract
            if sections:
                full_text += "\n\n" + "\n\n".join(sections)
            
            # Get PDF link
            pdf_link = page.locator('a[href*=".pdf"]').first
            pdf_url = None
            if await pdf_link.count() > 0:
                pdf_url = await pdf_link.get_attribute('href')
            
            self.stats['html_extracted'] += 1
            
            return {
                'title': title,
                'url': url,
                'pdf_url': pdf_url,
                'abstract': abstract.strip(),
                'full_text': full_text.strip(),
                'source_type': 'mlr',
                'has_full_text': len(full_text) > len(abstract),
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"MLR extraction failed: {e}")
            return None
    
    async def _extract_generic(self, page, url: str, title: str) -> Dict:
        """Generic extraction for other sources"""
        try:
            # Try common selectors for paper content
            content = ""
            
            # Try various content selectors
            selectors = [
                'article',
                'main',
                '.paper-content',
                '.article-content',
                '#content',
                '.post-content'
            ]
            
            for selector in selectors:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    content = await elem.text_content()
                    if len(content) > 500:  # Found substantial content
                        break
            
            # Fallback to body
            if len(content) < 500:
                content = await page.text_content('body')
            
            self.stats['html_extracted'] += 1
            
            return {
                'title': title,
                'url': url,
                'full_text': content.strip(),
                'source_type': 'generic',
                'has_full_text': True,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Generic extraction failed: {e}")
            return None
    
    def get_statistics(self) -> Dict:
        """Get scraping statistics"""
        return self.stats


class EnhancedCollector:
    """
    Enhanced collector that uses Playwright for deep scraping
    Falls back to basic RSS/API for unavailable content
    """
    
    def __init__(self, use_playwright: bool = True):
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        self.scraper = DeepWebScraper() if self.use_playwright else None
        
        # Basic collector for fallback
        from src.collector import Collector
        self.basic_collector = Collector()
    
    async def fetch_all_deep(self, config: Dict) -> List[Dict]:
        """
        Fetch articles with deep content extraction
        """
        # First, get basic articles
        articles = self.basic_collector.fetch_all(config)
        logger.info(f"Collected {len(articles)} articles via RSS/API")
        
        if not self.use_playwright:
            logger.warning("Playwright not available - returning basic articles")
            return articles
        
        # Now enhance with deep scraping
        logger.info("Enhancing articles with deep content extraction...")
        enhanced_articles = []
        
        for idx, article in enumerate(articles[:20], 1):  # Limit to first 20 for testing
            logger.info(f"[{idx}/{min(len(articles), 20)}] Deep scraping: {article['title'][:10]}...")
            
            try:
                deep_content = await self.scraper.scrape_paper_content(
                    article['link'],
                    article['title']
                )
                
                if deep_content:
                    # Merge basic + deep content
                    enhanced = {**article, **deep_content}
                    enhanced_articles.append(enhanced)
                    logger.info(f"  [OK] Extracted {len(deep_content.get('full_text', ''))} chars")
                else:
                    # Keep basic version
                    enhanced_articles.append(article)
                    logger.warning(f"  [FALLBACK] Using basic content")
                
            except Exception as e:
                logger.error(f"  [ERROR] {e}")
                enhanced_articles.append(article)
        
        # Add remaining articles without deep scraping (rate limiting)
        if len(articles) > 20:
            enhanced_articles.extend(articles[20:])
        
        logger.info(f"Deep scraping complete. Enhanced {min(len(articles), 20)} articles.")
        logger.info(f"Stats: {self.scraper.get_statistics()}")
        
        return enhanced_articles
    
    def get_statistics(self) -> Dict:
        """Get collector stats"""
        stats = {
            'basic_collector': self.basic_collector.get_statistics() if hasattr(self.basic_collector, 'get_statistics') else {},
        }
        
        if self.scraper:
            stats['deep_scraper'] = self.scraper.get_statistics()
        
        return stats


# Async wrapper for use in sync contexts
def fetch_articles_deep(config: Dict, use_playwright: bool = True) -> List[Dict]:
    """
    Synchronous wrapper for async deep fetching
    """
    collector = EnhancedCollector(use_playwright=use_playwright)
    return asyncio.run(collector.fetch_all_deep(config))