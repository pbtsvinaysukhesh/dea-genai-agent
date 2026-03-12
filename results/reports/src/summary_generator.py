"""
JSON Summary Generator

Generates structured JSON summaries of research papers and insights.
Includes executive summary, actionable takeaways, confidence levels, and source tracking.
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Takeaway:
    """Represents a single actionable takeaway from research."""
    number: int
    text: str
    source: Optional[str] = None  # Paper title or reference
    confidence: str = "high"  # high, medium, low
    quote: Optional[str] = None  # Direct quote if available


@dataclass
class Source:
    """Represents a source/paper with metadata."""
    index: int
    title: str
    url: str
    source_platform: str
    relevance_score: float
    summary: Optional[str] = None
    quotes: List[str] = field(default_factory=list)
    authors: Optional[List[str]] = None


@dataclass
class JsonSummary:
    """Complete structured summary of insights."""
    session_id: str
    generated_at: str
    total_papers: int
    executive_summary: str
    confidence: str  # primary, inferred, mixed
    takeaways: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class JsonSummaryGenerator:
    """Generates structured JSON summaries from paper data."""

    def __init__(self):
        self.session_id = str(uuid.uuid4())

    def build_json_summary(
        self,
        papers: List[Dict[str, Any]],
        executive_summary: str,
        takeaways: Optional[List[str]] = None,
        confidence: str = "primary",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JsonSummary:
        """
        Build a structured JSON summary from papers and insights.

        Args:
            papers: List of paper dictionaries with title, link, source, etc.
            executive_summary: One-liner capturing core theme
            takeaways: List of actionable takeaway strings (3-5 recommended)
            confidence: "primary" (from sources), "inferred" (analyzed), or "mixed"
            metadata: Additional metadata to include

        Returns:
            JsonSummary object
        """
        # Build sources list
        sources = self._build_sources(papers)

        # Build structured takeaways
        structured_takeaways = self._build_takeaways(
            takeaways, papers, sources
        )

        # Create summary object
        summary = JsonSummary(
            session_id=self.session_id,
            generated_at=datetime.utcnow().isoformat() + "Z",
            total_papers=len(papers),
            executive_summary=executive_summary,
            confidence=confidence,
            takeaways=structured_takeaways,
            sources=[asdict(s) for s in sources],
            metadata=metadata or {}
        )

        logger.info(
            f"Generated JSON summary: {len(papers)} papers, "
            f"{len(structured_takeaways)} takeaways, confidence={confidence}"
        )

        return summary

    def _build_sources(
        self, papers: List[Dict[str, Any]]
    ) -> List[Source]:
        """
        Build structured Source list from papers.

        Args:
            papers: List of paper dictionaries

        Returns:
            List of Source objects
        """
        sources = []

        for idx, paper in enumerate(papers, 1):
            source = Source(
                index=idx,
                title=paper.get("title", "Unknown Title"),
                url=self._normalize_url(paper.get("link", "")),
                source_platform=paper.get("source", "Unknown"),
                relevance_score=float(paper.get("relevance_score", 0)),
                summary=paper.get("summary", "")[:200],  # First 200 chars
                quotes=paper.get("quotes", []) if isinstance(
                    paper.get("quotes"), list
                ) else [],
                authors=paper.get("authors", []) if isinstance(
                    paper.get("authors"), list
                ) else None
            )
            sources.append(source)

        return sources

    def _build_takeaways(
        self,
        takeaways: Optional[List[str]],
        papers: List[Dict[str, Any]],
        sources: List[Source]
    ) -> List[Dict[str, Any]]:
        """
        Build structured takeaways with metadata.

        Args:
            takeaways: List of takeaway strings
            papers: Original papers list
            sources: Processed sources list

        Returns:
            List of takeaway dictionaries with metadata
        """
        if not takeaways:
            return []

        structured = []

        for number, text in enumerate(takeaways, 1):
            # Try to find source paper for this takeaway
            source_ref = None
            confidence = "high"

            # Simple heuristic: if takeaway mentions a platform, flag confidence
            if any(word in text.lower() for word in ["inferred", "suggests", "may", "could"]):
                confidence = "medium"
            elif any(word in text.lower() for word in ["shows", "demonstrates", "proves"]):
                confidence = "high"

            # Find best matching paper
            if papers:
                # Use first paper (most relevant)
                source_ref = sources[0].title if sources else None

            takeaway_dict = {
                "number": number,
                "text": text,
                "source": source_ref,
                "confidence": confidence,
            }
            structured.append(takeaway_dict)

        return structured

    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Normalize URL to include https:// if missing.

        Args:
            url: URL string

        Returns:
            Normalized URL
        """
        if not url:
            return ""

        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        return url

    def create_summary_from_insights(
        self,
        insights: Dict[str, Any],
        papers: List[Dict[str, Any]]
    ) -> JsonSummary:
        """
        Create JSON summary from insight dictionary.

        Args:
            insights: Dictionary with 'summary' and 'takeaways' keys
            papers: List of paper objects

        Returns:
            JsonSummary object
        """
        executive_summary = insights.get(
            "summary",
            "AI research insights summary"
        )

        # Extract takeaways from insights
        takeaways = []
        if "takeaways" in insights:
            takeaways = insights["takeaways"]
        elif "key_findings" in insights:
            takeaways = insights["key_findings"]

        confidence = self._infer_confidence(insights)

        return self.build_json_summary(
            papers=papers,
            executive_summary=executive_summary,
            takeaways=takeaways if isinstance(takeaways, list) else [],
            confidence=confidence
        )

    @staticmethod
    def _infer_confidence(insights: Dict[str, Any]) -> str:
        """
        Infer confidence level from insights metadata.

        Args:
            insights: Insights dictionary

        Returns:
            "primary", "inferred", or "mixed"
        """
        # Check if insights has confidence metadata
        if "confidence" in insights:
            return insights["confidence"]

        # Default based on whether sources are directly cited
        if "sources_directly_cited" in insights:
            if insights["sources_directly_cited"]:
                return "primary"
            else:
                return "inferred"

        # Default to primary (most insights come from source analysis)
        return "primary"


# Utility function for easy access
def generate_json_summary(
    papers: List[Dict[str, Any]],
    executive_summary: str,
    takeaways: Optional[List[str]] = None,
    confidence: str = "primary"
) -> JsonSummary:
    """
    Convenience function to generate JSON summary.

    Args:
        papers: List of paper dictionaries
        executive_summary: One-liner executive summary
        takeaways: List of actionable takeaways
        confidence: Confidence level

    Returns:
        JsonSummary object
    """
    generator = JsonSummaryGenerator()
    return generator.build_json_summary(
        papers=papers,
        executive_summary=executive_summary,
        takeaways=takeaways,
        confidence=confidence
    )
