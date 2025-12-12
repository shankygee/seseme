"""
Research Engine - Handles web search, data retrieval, and source management
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re
import httpx
from urllib.parse import urlparse, quote_plus

from ..models import (
    Source,
    SourceType,
    ResearchTask,
    ResearchResult,
    ResearchDepth,
)
from ..config import settings

logger = logging.getLogger(__name__)


class ResearchEngine:
    """
    Research Engine with tool/function calling capabilities.

    Responsibilities:
    - Turn natural-language questions into structured research tasks
    - Call web search APIs and domain-specific APIs
    - Pull raw content from articles, PDFs, transcripts
    - Chunk, clean, dedupe, and tag content by source, date, reliability
    """

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self._search_providers = self._init_search_providers()

    def _init_search_providers(self) -> Dict[str, Any]:
        """Initialize available search providers based on API keys"""
        providers = {}

        if settings.serpapi_key:
            providers["serpapi"] = {
                "url": "https://serpapi.com/search",
                "key": settings.serpapi_key,
            }

        if settings.tavily_api_key:
            providers["tavily"] = {
                "url": "https://api.tavily.com/search",
                "key": settings.tavily_api_key,
            }

        # Always include a fallback mock provider for development
        providers["mock"] = {"url": None, "key": None}

        return providers

    async def create_research_task(
        self,
        query: str,
        depth: ResearchDepth = ResearchDepth.MEDIUM,
        source_types: Optional[List[SourceType]] = None,
        max_sources: int = 5,
    ) -> ResearchTask:
        """Create a structured research task from a query"""
        sub_questions = await self._decompose_query(query, depth)

        return ResearchTask(
            query=query,
            sub_questions=sub_questions,
            depth=depth,
            source_types=source_types or [SourceType.WEB],
            max_sources=max_sources,
            status="pending",
        )

    async def _decompose_query(
        self,
        query: str,
        depth: ResearchDepth,
    ) -> List[str]:
        """
        Decompose a complex query into sub-questions.

        For deeper research, we create more sub-questions to explore
        different angles of the topic.
        """
        # Number of sub-questions based on depth
        num_questions = {
            ResearchDepth.TWEET: 1,
            ResearchDepth.QUICK: 2,
            ResearchDepth.MEDIUM: 3,
            ResearchDepth.DEEP: 5,
        }

        # For now, generate basic sub-questions
        # In production, this would use an LLM to intelligently decompose
        base_questions = [query]

        if depth in [ResearchDepth.MEDIUM, ResearchDepth.DEEP]:
            # Add contextual questions
            if "best" in query.lower() or "top" in query.lower():
                base_questions.extend([
                    f"{query} pricing comparison",
                    f"{query} pros and cons",
                    f"{query} user reviews",
                ])
            elif "how" in query.lower():
                base_questions.extend([
                    f"{query} step by step",
                    f"{query} examples",
                    f"{query} common mistakes",
                ])
            else:
                base_questions.extend([
                    f"{query} overview",
                    f"{query} latest developments",
                ])

        return base_questions[:num_questions.get(depth, 3)]

    async def execute_research(self, task: ResearchTask) -> ResearchResult:
        """Execute a research task and gather sources"""
        task.status = "in_progress"
        all_sources: List[Source] = []

        try:
            # Execute searches for each sub-question
            search_tasks = [
                self._search(q, task.source_types, task.max_sources)
                for q in task.sub_questions
            ]
            results = await asyncio.gather(*search_tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_sources.extend(result)

            # Deduplicate sources by URL
            seen_urls = set()
            unique_sources = []
            for source in all_sources:
                if source.url not in seen_urls:
                    seen_urls.add(source.url)
                    unique_sources.append(source)

            # Limit to max_sources
            unique_sources = unique_sources[:task.max_sources]

            # Fetch and process content for each source
            content_tasks = [self._fetch_content(s) for s in unique_sources]
            processed_sources = await asyncio.gather(*content_tasks, return_exceptions=True)

            final_sources = [
                s for s in processed_sources
                if isinstance(s, Source) and s.content
            ]

            # Build raw content from all sources
            raw_content = self._compile_raw_content(final_sources)

            task.status = "completed"

            return ResearchResult(
                task_id=task.id,
                query=task.query,
                sources=final_sources,
                raw_content=raw_content,
                confidence_score=self._calculate_confidence(final_sources),
                citations=self._generate_citations(final_sources),
            )

        except Exception as e:
            logger.error(f"Research execution failed: {e}")
            task.status = "failed"
            return ResearchResult(
                task_id=task.id,
                query=task.query,
                sources=[],
                raw_content="",
                confidence_score=0.0,
            )

    async def _search(
        self,
        query: str,
        source_types: List[SourceType],
        max_results: int,
    ) -> List[Source]:
        """Execute search across available providers"""
        sources = []

        # Try Tavily first (best for research)
        if "tavily" in self._search_providers:
            try:
                tavily_results = await self._search_tavily(query, max_results)
                sources.extend(tavily_results)
            except Exception as e:
                logger.warning(f"Tavily search failed: {e}")

        # Fall back to SerpAPI
        if not sources and "serpapi" in self._search_providers:
            try:
                serp_results = await self._search_serpapi(query, max_results)
                sources.extend(serp_results)
            except Exception as e:
                logger.warning(f"SerpAPI search failed: {e}")

        # Use mock data if no real providers available
        if not sources:
            sources = self._mock_search(query, max_results)

        return sources

    async def _search_tavily(self, query: str, max_results: int) -> List[Source]:
        """Search using Tavily API"""
        provider = self._search_providers["tavily"]

        response = await self.http_client.post(
            provider["url"],
            json={
                "api_key": provider["key"],
                "query": query,
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": True,
            },
        )
        response.raise_for_status()
        data = response.json()

        sources = []
        for result in data.get("results", []):
            sources.append(Source(
                url=result.get("url", ""),
                title=result.get("title", ""),
                content=result.get("raw_content", result.get("content", "")),
                snippet=result.get("content", "")[:200],
                source_type=self._classify_source_type(result.get("url", "")),
                reliability_score=result.get("score", 0.5),
            ))

        return sources

    async def _search_serpapi(self, query: str, max_results: int) -> List[Source]:
        """Search using SerpAPI"""
        provider = self._search_providers["serpapi"]

        response = await self.http_client.get(
            provider["url"],
            params={
                "api_key": provider["key"],
                "q": query,
                "num": max_results,
                "engine": "google",
            },
        )
        response.raise_for_status()
        data = response.json()

        sources = []
        for result in data.get("organic_results", []):
            sources.append(Source(
                url=result.get("link", ""),
                title=result.get("title", ""),
                content="",  # Will be fetched separately
                snippet=result.get("snippet", ""),
                source_type=self._classify_source_type(result.get("link", "")),
                reliability_score=0.6,
            ))

        return sources

    def _mock_search(self, query: str, max_results: int) -> List[Source]:
        """Generate mock search results for development"""
        mock_results = [
            Source(
                url=f"https://example.com/article-{i}",
                title=f"Article about {query} - Result {i+1}",
                content=f"This is mock content about {query}. In a production environment, this would be real search results from web APIs.",
                snippet=f"Mock snippet for {query}...",
                source_type=SourceType.WEB,
                reliability_score=0.5,
            )
            for i in range(min(max_results, 3))
        ]
        return mock_results

    async def _fetch_content(self, source: Source) -> Source:
        """Fetch and process full content for a source"""
        if source.content and len(source.content) > 100:
            # Already has content
            source.content = self._clean_content(source.content)
            return source

        try:
            response = await self.http_client.get(
                source.url,
                follow_redirects=True,
                headers={"User-Agent": "CompanionResearcher/1.0"},
            )
            response.raise_for_status()

            html = response.text
            source.content = self._extract_text_from_html(html)
            source.content = self._clean_content(source.content)

        except Exception as e:
            logger.warning(f"Failed to fetch content from {source.url}: {e}")
            source.content = source.snippet

        return source

    def _extract_text_from_html(self, html: str) -> str:
        """Extract readable text from HTML"""
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)

        # Decode HTML entities
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;', '"', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _clean_content(self, content: str) -> str:
        """Clean and normalize content text"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)

        # Remove common boilerplate patterns
        boilerplate_patterns = [
            r'cookie\s*policy',
            r'privacy\s*policy',
            r'terms\s*of\s*service',
            r'subscribe\s*to\s*our\s*newsletter',
            r'sign\s*up\s*for\s*free',
            r'advertisement',
        ]
        for pattern in boilerplate_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)

        # Truncate if too long
        max_length = 5000
        if len(content) > max_length:
            content = content[:max_length] + "..."

        return content.strip()

    def _classify_source_type(self, url: str) -> SourceType:
        """Classify a URL into a source type"""
        domain = urlparse(url).netloc.lower()

        academic_domains = ['arxiv.org', 'scholar.google', 'pubmed', 'jstor.org', 'sciencedirect']
        news_domains = ['nytimes.com', 'bbc.com', 'reuters.com', 'cnn.com', 'theguardian.com']
        doc_domains = ['docs.', 'documentation', 'readthedocs', 'github.io', 'developer.']

        if any(d in domain for d in academic_domains):
            return SourceType.ACADEMIC
        elif any(d in domain for d in news_domains):
            return SourceType.NEWS
        elif any(d in domain for d in doc_domains):
            return SourceType.DOCUMENTATION
        elif 'youtube.com' in domain or 'vimeo.com' in domain:
            return SourceType.VIDEO
        elif url.endswith('.pdf'):
            return SourceType.PDF
        else:
            return SourceType.WEB

    def _compile_raw_content(self, sources: List[Source]) -> str:
        """Compile all source content into a single document"""
        sections = []
        for i, source in enumerate(sources, 1):
            sections.append(f"""
=== Source {i}: {source.title} ===
URL: {source.url}
Type: {source.source_type.value}
Reliability: {source.reliability_score:.2f}

{source.content}
""")
        return "\n".join(sections)

    def _calculate_confidence(self, sources: List[Source]) -> float:
        """Calculate overall confidence score based on sources"""
        if not sources:
            return 0.0

        # Average reliability weighted by source type
        type_weights = {
            SourceType.ACADEMIC: 1.0,
            SourceType.DOCUMENTATION: 0.9,
            SourceType.NEWS: 0.7,
            SourceType.WEB: 0.5,
            SourceType.VIDEO: 0.6,
            SourceType.PDF: 0.8,
            SourceType.LOCAL: 0.9,
        }

        total_weight = 0
        weighted_sum = 0
        for source in sources:
            weight = type_weights.get(source.source_type, 0.5)
            weighted_sum += source.reliability_score * weight
            total_weight += weight

        base_confidence = weighted_sum / total_weight if total_weight > 0 else 0.5

        # Boost confidence with more sources (up to 20%)
        source_bonus = min(len(sources) * 0.04, 0.2)

        return min(base_confidence + source_bonus, 1.0)

    def _generate_citations(self, sources: List[Source]) -> List[Dict[str, str]]:
        """Generate citation list from sources"""
        return [
            {
                "title": source.title,
                "url": source.url,
                "type": source.source_type.value,
                "accessed": source.timestamp.isoformat(),
            }
            for source in sources
        ]

    async def close(self):
        """Clean up resources"""
        await self.http_client.aclose()
