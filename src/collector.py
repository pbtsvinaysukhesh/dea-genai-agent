"""
Universal Collector for On-Device AI Memory Intelligence Agent
Hybrid Engine: RSS Parsing + HTML Web Scraping Fallback
"""

import feedparser
import requests
import datetime
import time
import logging
import re
from typing import List, Dict
from urllib.parse import quote
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class CollectorConfig:
    """Configuration for Collector"""
    MAX_RESULTS_PER_QUERY = 50
    REQUEST_TIMEOUT = 20
    RETRY_ATTEMPTS = 2
    RETRY_DELAY = 2
    RATE_LIMIT_DELAY = 1
    # Mimic a real browser to avoid blocking
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


class Collector:
    """
    Enhanced collector for gathering AI research articles from multiple sources
    """
    
    def __init__(self, config: CollectorConfig = None):
        self.config = config or CollectorConfig()
        self.stats = {'total': 0, 'rss': 0, 'scraped': 0, 'failed': 0}
    
    def fetch_all(self, config: Dict) -> List[Dict]:
        """Main entry point to fetch from all configured sources"""
        all_articles = []
        
        # 1. arXiv (API)
        if 'arxiv_queries' in config.get('sources', {}):
            all_articles.extend(self.fetch_arxiv(config['sources']['arxiv_queries']))
            
        # 2. RSS & Web Scraping
        if 'rss_feeds' in config.get('sources', {}):
            all_articles.extend(self.fetch_universal(config['sources']['rss_feeds']))
            
        return all_articles

    def fetch_arxiv(self, queries: List[str]) -> List[Dict]:
        base_url = "http://export.arxiv.org/api/query"
        articles = []
        logger.info(f"Fetching {len(queries)} arXiv queries...")
        
        for query in queries:
            try:
                params = f"search_query={quote(query)}&max_results={self.config.MAX_RESULTS_PER_QUERY}&sortBy=submittedDate&sortOrder=descending"
                response = self._make_request(f"{base_url}?{params}")
                if not response: continue
                
                feed = feedparser.parse(response.content)
                for entry in feed.entries:
                    articles.append({
                        "title": entry.title.replace('\n', ' ').strip(),
                        "link": entry.link,
                        "summary": entry.summary.replace('\n', ' ').strip(),
                        "source": "arXiv",
                        "published": entry.published[:10] if hasattr(entry, 'published') else str(datetime.date.today()),
                        "collected_at": datetime.datetime.now().isoformat()
                    })
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"arXiv error: {e}")
        
        self.stats['total'] += len(articles)
        return articles

    def fetch_universal(self, urls: List[str]) -> List[Dict]:
        """
        Hybrid Fetcher: Tries RSS first, falls back to HTML Scraping
        """
        articles = []
        logger.info(f"Processing {len(urls)} web sources...")
        
        for url in urls:
            try:
                response = self._make_request(url)
                if not response: continue
                
                # Strategy 1: Try as RSS/Atom Feed
                feed = feedparser.parse(response.content)
                
                if feed.entries:
                    # It's a valid RSS feed
                    logger.info(f"[RSS] Found {len(feed.entries)} items in {url}")
                    source_name = self._extract_source_name(url)
                    
                    for entry in feed.entries:
                        parsed = self._parse_rss_entry(entry, source_name)
                        if parsed:
                            articles.append(parsed)
                    
                    self.stats['rss'] += len(feed.entries)
                
                else:
                    # Strategy 2: Fallback to HTML Scraping
                    logger.info(f"[HTML] RSS empty, attempting scrape: {url}")
                    scraped_data = self._scrape_html(url, response.content)
                    
                    if scraped_data:
                        if isinstance(scraped_data, list):
                            articles.extend(scraped_data)
                            self.stats['scraped'] += len(scraped_data)
                        elif isinstance(scraped_data, dict):
                            articles.append(scraped_data)
                            self.stats['scraped'] += 1
                    else:
                        logger.warning(f"[-] Could not extract content from: {url}")

                time.sleep(self.config.RATE_LIMIT_DELAY)
                
            except Exception as e:
                logger.error(f"Source error {url}: {e}")
                self.stats['failed'] += 1
                
        self.stats['total'] += len(articles)
        return articles

    def _scrape_html(self, url: str, html_content: bytes) -> List[Dict]:
        """Uses BeautifulSoup to extract content from non-RSS pages"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            source_name = self._extract_source_name(url)
            results = []

            # Case A: Blog Index
            articles = soup.find_all('article') or \
                       soup.find_all('div', class_=re.compile(r'post|card|article|blog-item'))
            
            if len(articles) > 1:
                for art in articles[:5]:
                    title_tag = art.find(['h1', 'h2', 'h3', 'h4'])
                    if not title_tag: continue
                    
                    link_tag = art.find('a')
                    if not link_tag: continue
                    link = link_tag.get('href')
                    if link and not link.startswith('http'):
                        base = '/'.join(url.split('/')[:3])
                        link = base + link

                    results.append({
                        "title": title_tag.get_text(strip=True),
                        "link": link or url,
                        "summary": art.get_text(strip=True)[:500],
                        "source": f"{source_name} (Scraped)",
                        "published": str(datetime.date.today()),
                        "collected_at": datetime.datetime.now().isoformat()
                    })
                return results

            # Case B: Single Article
            title = soup.find('h1')
            if title:
                content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                summary = content.get_text(strip=True)[:2000] if content else ""
                
                return {
                    "title": title.get_text(strip=True),
                    "link": url,
                    "summary": summary,
                    "source": f"{source_name} (Scraped)",
                    "published": str(datetime.date.today()),
                    "collected_at": datetime.datetime.now().isoformat()
                }
            return None
        except Exception as e:
            logger.debug(f"Scraping failed: {e}")
            return None

    def _make_request(self, url: str):
        for attempt in range(self.config.RETRY_ATTEMPTS):
            try:
                response = requests.get(
                    url, 
                    timeout=self.config.REQUEST_TIMEOUT,
                    headers={'User-Agent': self.config.USER_AGENT}
                )
                if response.status_code == 200: return response
                
                # Do not retry 400/403/404
                if response.status_code in [400, 401, 403, 404]:
                    logger.warning(f"Dead Link ({response.status_code}): {url}")
                    return None
            except: pass
            time.sleep(self.config.RETRY_DELAY)
        return None

    def _parse_rss_entry(self, entry, source) -> Dict:
        try:
            title = entry.title
            if "GitHub" in source and "v" in title and len(title) < 10:
                title = f"{source}: {title}"

            summary = ""
            if hasattr(entry, 'content'): summary = entry.content[0].value
            elif hasattr(entry, 'summary'): summary = entry.summary
            elif hasattr(entry, 'description'): summary = entry.description

            summary = re.sub(r'<[^>]+>', '', summary)[:2500]

            return {
                "title": title,
                "link": entry.link,
                "summary": summary,
                "source": source,
                "published": getattr(entry, 'published', getattr(entry, 'updated', str(datetime.date.today()))),
                "collected_at": datetime.datetime.now().isoformat()
            }
        except AttributeError as e:
            logger.debug(f"Missing attribute in RSS entry: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error parsing RSS entry: {e}")
            return None

    def _extract_source_name(self, url: str) -> str:
        if "github.com" in url:
            parts = url.split('/')
            if len(parts) >= 5: return f"GitHub ({parts[4]})"
            return "GitHub"
        try: return url.split('/')[2].replace('www.', '').capitalize()
        except: return "Web"

    def get_statistics(self) -> Dict:
        return {**self.stats}


# --- MISSING FUNCTION ADDED HERE ---
def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """
    Remove duplicate articles based on title similarity
    """
    seen_titles = set()
    unique_articles = []
    
    for article in articles:
        # Normalize title for comparison
        title = article.get('title', '').lower().strip()
        
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_articles.append(article)
    
    removed = len(articles) - len(unique_articles)
    if removed > 0:
        logger.info(f"Removed {removed} duplicate articles")
    
    return unique_articles
