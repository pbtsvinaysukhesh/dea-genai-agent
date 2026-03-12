"""
Source Link Processor

Handles URL normalization, deduplication, pagination, and hyperlink creation
for PDF and PowerPoint presentations.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)


class SourceLinkProcessor:
    """
    Processes source links for inclusion in PDF and PPTX documents.

    Features:
    - URL normalization (add https://, validate format)
    - Deduplication (same URL from multiple papers)
    - Sorting (by relevance or alphabetically)
    - Pagination for large lists
    - Hyperlink creation support
    """

    # Configuration constants
    SOURCES_PER_PPTX_SLIDE = 20  # ~10 per column with 2 columns
    SOURCES_PER_PDF_PAGE = 40
    PPTX_COLUMNS = 2

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL to include https:// if missing.

        Args:
            url: Raw URL string

        Returns:
            Normalized URL with https:// prefix
        """
        if not url or not isinstance(url, str):
            return ""

        url = url.strip()

        # Already has protocol
        if url.startswith(("http://", "https://", "ftp://")):
            return url

        # Add https:// prefix
        return "https://" + url

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format (basic validation).

        Args:
            url: URL to validate

        Returns:
            True if URL format is valid
        """
        if not url:
            return False

        try:
            result = urlparse(url)
            # Check that we have both scheme and netloc
            return bool(result.scheme and result.netloc)
        except Exception:
            return False

    @classmethod
    def build_source_list(
        cls,
        papers: List[Dict[str, Any]],
        sort_by: str = "relevance",
        deduplicate: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Build deduplicated and sorted source list from papers.

        Args:
            papers: List of paper dictionaries
            sort_by: "relevance" (score descending) or "alphabetical" (title ascending)
            deduplicate: If True, remove duplicate URLs

        Returns:
            List of deduplicated source dictionaries
        """
        sources = []
        seen_urls = set()

        for idx, paper in enumerate(papers, 1):
            # Extract and normalize URL
            url = paper.get("link", "")
            if not url:
                continue

            url = cls.normalize_url(url)

            # Validate URL
            if not cls.validate_url(url):
                logger.warning(f"Invalid URL format: {url}")
                continue

            # Check for duplicates
            if deduplicate and url in seen_urls:
                logger.debug(f"Skipping duplicate URL: {url}")
                continue

            seen_urls.add(url)

            source = {
                "title": paper.get("title", "Unknown Title"),
                "url": url,
                "source_platform": paper.get("source", "Unknown"),
                "relevance_score": float(paper.get("relevance_score", 0)),
                "summary": paper.get("summary", ""),
            }
            sources.append(source)

        # Sort sources
        if sort_by == "relevance":
            sources.sort(
                key=lambda x: x["relevance_score"],
                reverse=True
            )
        elif sort_by == "alphabetical":
            sources.sort(key=lambda x: x["title"].lower())

        logger.info(
            f"Built source list: {len(sources)} sources "
            f"(deduped from {len(papers)} papers)"
        )

        return sources

    @classmethod
    def paginate_sources_for_pptx(
        cls,
        sources: List[Dict[str, Any]],
        sources_per_slide: int = SOURCES_PER_PPTX_SLIDE
    ) -> List[List[Dict[str, Any]]]:
        """
        Paginate sources for PowerPoint presentation.

        Args:
            sources: List of source dictionaries
            sources_per_slide: Number of sources per slide

        Returns:
            List of pages, each containing a list of sources
        """
        pages = []
        for i in range(0, len(sources), sources_per_slide):
            page = sources[i:i + sources_per_slide]
            pages.append(page)

        logger.info(
            f"Paginated {len(sources)} sources into {len(pages)} PPTX slides "
            f"({sources_per_slide} per slide)"
        )

        return pages

    @classmethod
    def paginate_sources_for_pdf(
        cls,
        sources: List[Dict[str, Any]],
        sources_per_page: int = SOURCES_PER_PDF_PAGE
    ) -> List[List[Dict[str, Any]]]:
        """
        Paginate sources for PDF document.

        Args:
            sources: List of source dictionaries
            sources_per_page: Number of sources per page

        Returns:
            List of pages, each containing a list of sources
        """
        pages = []
        for i in range(0, len(sources), sources_per_page):
            page = sources[i:i + sources_per_page]
            pages.append(page)

        logger.info(
            f"Paginated {len(sources)} sources into {len(pages)} PDF pages "
            f"({sources_per_page} per page)"
        )

        return pages

    @classmethod
    def create_pdf_sources_section(
        cls,
        sources: List[Dict[str, Any]]
    ) -> List[Tuple[str, List[str]]]:
        """
        Create reportlab story elements for PDF sources section.

        Returns list of (heading_text, source_entries) tuples that can be
        converted to Paragraph and Table elements by PDF generator.

        Args:
            sources: List of source dictionaries

        Returns:
            List of (heading, sources) tuples for each PDF page
        """
        pages = cls.paginate_sources_for_pdf(sources)
        pdf_sections = []

        for page_num, page_sources in enumerate(pages, 1):
            if page_num == 1:
                heading = "Sources"
            else:
                heading = f"Sources (continued - Page {page_num})"

            # Create source entry strings with URLs
            source_entries = []
            for idx, source in enumerate(page_sources, 1):
                entry = f"{idx}. {source['title']} ({source['source_platform']})\n{source['url']}"
                source_entries.append(entry)

            pdf_sections.append((heading, source_entries))

        logger.info(f"Created PDF sources section with {len(pdf_sections)} pages")
        return pdf_sections

    @classmethod
    def create_pptx_sources_slides_data(
        cls,
        sources: List[Dict[str, Any]],
        columns: int = PPTX_COLUMNS
    ) -> List[Dict[str, Any]]:
        """
        Create data structure for PPTX sources slides.

        Returns list of slide data dictionaries that can be used by
        PPTX generator to create slides with 2-column layout.

        Args:
            sources: List of source dictionaries
            columns: Number of columns per slide

        Returns:
            List of slide data dictionaries
        """
        pages = cls.paginate_sources_for_pptx(sources)
        slides_data = []

        for page_num, page_sources in enumerate(pages, 1):
            # Split sources into columns
            sources_per_column = (len(page_sources) + columns - 1) // columns
            columns_data = []

            for col in range(columns):
                start_idx = col * sources_per_column
                end_idx = start_idx + sources_per_column
                column_sources = page_sources[start_idx:end_idx]
                columns_data.append(column_sources)

            slide_data = {
                "page_number": page_num,
                "total_pages": len(pages),
                "columns": columns_data,
                "title": f"Sources (Page {page_num} of {len(pages)})" if len(pages) > 1 else "Sources"
            }
            slides_data.append(slide_data)

        logger.info(
            f"Created PPTX sources slide data: {len(slides_data)} slides "
            f"with {columns} columns"
        )
        return slides_data

    @staticmethod
    def extract_domain_from_url(url: str) -> str:
        """
        Extract domain name from URL.

        Args:
            url: Full URL

        Returns:
            Domain name (e.g., 'arxiv.org' from 'https://arxiv.org/abs/...')
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix if present
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return "unknown"

    @staticmethod
    def format_source_text(source: Dict[str, Any]) -> str:
        """
        Format source as readable text line.

        Args:
            source: Source dictionary

        Returns:
            Formatted source text
        """
        title = source.get("title", "Unknown Title")
        platform = source.get("source_platform", "Unknown")
        domain = SourceLinkProcessor.extract_domain_from_url(source.get("url", ""))

        return f"• {title} ({platform}/{domain})"

    @staticmethod
    def verify_sources(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify source list integrity.

        Args:
            sources: List of source dictionaries

        Returns:
            Verification report dictionary
        """
        report = {
            "total_sources": len(sources),
            "valid_urls": 0,
            "invalid_urls": 0,
            "invalid_entries": [],
        }

        for idx, source in enumerate(sources):
            url = source.get("url", "")
            if SourceLinkProcessor.validate_url(url):
                report["valid_urls"] += 1
            else:
                report["invalid_urls"] += 1
                report["invalid_entries"].append({
                    "index": idx,
                    "title": source.get("title", "Unknown"),
                    "url": url
                })

        logger.info(
            f"Source verification: {report['valid_urls']}/{report['total_sources']} valid URLs"
        )

        if report["invalid_entries"]:
            logger.warning(
                f"Found {report['invalid_urls']} invalid URLs in source list"
            )

        return report

    @staticmethod
    def create_source_index(sources: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Create index for quick source lookup by URL.

        Args:
            sources: List of source dictionaries

        Returns:
            Dictionary mapping URL to source list position
        """
        return {source["url"]: idx for idx, source in enumerate(sources)}
