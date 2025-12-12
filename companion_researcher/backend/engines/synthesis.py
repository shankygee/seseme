"""
Synthesis Engine - Summarizes and synthesizes research results
"""
import logging
from typing import List, Dict, Any, Optional
from enum import Enum

from ..models import (
    Source,
    ResearchResult,
    ResearchDepth,
)
from ..config import settings

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """Output format types"""
    TWEET = "tweet"  # ~280 chars
    ONE_PAGER = "one_pager"  # ~500 words
    DEEP_DIVE = "deep_dive"  # Comprehensive
    BULLET_POINTS = "bullet_points"
    COMPARISON = "comparison"
    TIMELINE = "timeline"


class SynthesisEngine:
    """
    Summarization and Synthesis Module.

    Takes structured research results and:
    - Summarizes each source
    - Builds synthesis answers (pros/cons, comparisons, timelines)
    - Generates citations and confidence scores
    - Outputs at different depths (tweet, 1-pager, deep dive)
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def synthesize(
        self,
        research_result: ResearchResult,
        output_format: OutputFormat = OutputFormat.ONE_PAGER,
        user_context: Optional[str] = None,
    ) -> ResearchResult:
        """
        Synthesize research results into a coherent response.

        Args:
            research_result: The raw research result to synthesize
            output_format: Desired output format
            user_context: Additional context about why user needs this

        Returns:
            Updated ResearchResult with summary and synthesis
        """
        if not research_result.sources:
            research_result.summary = "No sources were found for this query."
            research_result.synthesis = ""
            return research_result

        # Generate source summaries
        source_summaries = await self._summarize_sources(research_result.sources)

        # Build synthesis based on format
        if output_format == OutputFormat.TWEET:
            synthesis = await self._generate_tweet_synthesis(
                research_result.query,
                source_summaries,
            )
        elif output_format == OutputFormat.BULLET_POINTS:
            synthesis = await self._generate_bullet_synthesis(
                research_result.query,
                source_summaries,
            )
        elif output_format == OutputFormat.COMPARISON:
            synthesis = await self._generate_comparison_synthesis(
                research_result.query,
                source_summaries,
            )
        elif output_format == OutputFormat.DEEP_DIVE:
            synthesis = await self._generate_deep_synthesis(
                research_result.query,
                source_summaries,
                user_context,
            )
        else:  # ONE_PAGER default
            synthesis = await self._generate_standard_synthesis(
                research_result.query,
                source_summaries,
                user_context,
            )

        # Create overall summary
        summary = await self._create_summary(research_result.query, synthesis)

        research_result.summary = summary
        research_result.synthesis = synthesis

        return research_result

    async def _summarize_sources(self, sources: List[Source]) -> List[Dict[str, Any]]:
        """Generate summaries for each source"""
        summaries = []

        for source in sources:
            summary = await self._summarize_single_source(source)
            summaries.append({
                "title": source.title,
                "url": source.url,
                "type": source.source_type.value,
                "reliability": source.reliability_score,
                "summary": summary,
                "key_points": self._extract_key_points(source.content),
            })

        return summaries

    async def _summarize_single_source(self, source: Source) -> str:
        """Summarize a single source"""
        if self.llm_client:
            # Use LLM for summarization
            prompt = f"""Summarize the following content in 2-3 sentences:

Title: {source.title}
Content: {source.content[:2000]}

Summary:"""
            return await self._call_llm(prompt, max_tokens=150)

        # Fallback: Extract first meaningful sentences
        return self._extractive_summary(source.content, num_sentences=3)

    def _extract_key_points(self, content: str, max_points: int = 5) -> List[str]:
        """Extract key points from content"""
        # Split into sentences
        sentences = content.replace('\n', ' ').split('.')
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        # Score sentences by relevance signals
        scored = []
        for sentence in sentences:
            score = 0
            # Contains numbers/statistics
            if any(c.isdigit() for c in sentence):
                score += 2
            # Contains key phrases
            key_phrases = ['important', 'key', 'main', 'significant', 'notable', 'best', 'top', 'first']
            if any(phrase in sentence.lower() for phrase in key_phrases):
                score += 2
            # Not too short or too long
            words = len(sentence.split())
            if 10 < words < 30:
                score += 1
            scored.append((score, sentence))

        # Sort by score and return top points
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] + '.' for s in scored[:max_points]]

    def _extractive_summary(self, content: str, num_sentences: int = 3) -> str:
        """Simple extractive summarization"""
        sentences = content.replace('\n', ' ').split('.')
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

        if not sentences:
            return content[:200] + "..."

        # Take first sentences (usually most informative)
        return '. '.join(sentences[:num_sentences]) + '.'

    async def _generate_tweet_synthesis(
        self,
        query: str,
        source_summaries: List[Dict[str, Any]],
    ) -> str:
        """Generate tweet-length synthesis (~280 chars)"""
        if self.llm_client:
            prompt = f"""Create a single tweet (under 280 characters) answering: {query}

Based on these sources:
{self._format_summaries_for_prompt(source_summaries)}

Tweet:"""
            return await self._call_llm(prompt, max_tokens=100)

        # Fallback: Combine key points into short response
        key_info = []
        for summary in source_summaries[:2]:
            if summary['key_points']:
                key_info.append(summary['key_points'][0][:100])

        synthesis = f"Re: {query[:50]} - " + " ".join(key_info)
        return synthesis[:280]

    async def _generate_bullet_synthesis(
        self,
        query: str,
        source_summaries: List[Dict[str, Any]],
    ) -> str:
        """Generate bullet point synthesis"""
        if self.llm_client:
            prompt = f"""Create a bullet-point summary answering: {query}

Based on these sources:
{self._format_summaries_for_prompt(source_summaries)}

Format as:
• Key point 1
• Key point 2
...

Bullet points:"""
            return await self._call_llm(prompt, max_tokens=500)

        # Fallback: Compile key points
        bullets = [f"**{query}**\n"]
        for summary in source_summaries:
            for point in summary['key_points'][:2]:
                bullets.append(f"• {point}")
            bullets.append(f"  _(Source: {summary['title'][:50]})_\n")

        return "\n".join(bullets)

    async def _generate_comparison_synthesis(
        self,
        query: str,
        source_summaries: List[Dict[str, Any]],
    ) -> str:
        """Generate comparison-style synthesis"""
        if self.llm_client:
            prompt = f"""Create a comparison analysis for: {query}

Based on these sources:
{self._format_summaries_for_prompt(source_summaries)}

Include:
- Similarities
- Differences
- Pros and cons
- Recommendation

Comparison:"""
            return await self._call_llm(prompt, max_tokens=800)

        # Fallback: Basic comparison structure
        comparison = f"## Comparison: {query}\n\n"

        comparison += "### Options Found:\n"
        for i, summary in enumerate(source_summaries, 1):
            comparison += f"\n**{i}. {summary['title']}**\n"
            for point in summary['key_points'][:3]:
                comparison += f"- {point}\n"

        comparison += "\n### Key Considerations:\n"
        comparison += "- Review each option based on your specific needs\n"
        comparison += "- Consider reliability scores when making decisions\n"

        return comparison

    async def _generate_deep_synthesis(
        self,
        query: str,
        source_summaries: List[Dict[str, Any]],
        user_context: Optional[str],
    ) -> str:
        """Generate comprehensive deep-dive synthesis"""
        if self.llm_client:
            context_note = f"\nUser context: {user_context}" if user_context else ""
            prompt = f"""Create a comprehensive analysis for: {query}{context_note}

Based on these sources:
{self._format_summaries_for_prompt(source_summaries)}

Include:
1. Executive Summary
2. Background/Context
3. Key Findings
4. Detailed Analysis
5. Different Perspectives
6. Implications
7. Recommendations
8. Sources

Deep dive:"""
            return await self._call_llm(prompt, max_tokens=2000)

        # Fallback: Structured comprehensive response
        synthesis = f"# Deep Dive: {query}\n\n"

        synthesis += "## Executive Summary\n"
        synthesis += f"Analysis based on {len(source_summaries)} sources.\n\n"

        synthesis += "## Key Findings\n"
        for summary in source_summaries:
            synthesis += f"\n### {summary['title']}\n"
            synthesis += f"*Reliability: {summary['reliability']:.0%}*\n\n"
            synthesis += f"{summary['summary']}\n\n"
            synthesis += "**Key Points:**\n"
            for point in summary['key_points']:
                synthesis += f"- {point}\n"

        synthesis += "\n## Sources\n"
        for i, summary in enumerate(source_summaries, 1):
            synthesis += f"{i}. [{summary['title']}]({summary['url']})\n"

        if user_context:
            synthesis += f"\n## For Your Context\n{user_context}\n"

        return synthesis

    async def _generate_standard_synthesis(
        self,
        query: str,
        source_summaries: List[Dict[str, Any]],
        user_context: Optional[str],
    ) -> str:
        """Generate standard one-pager synthesis"""
        if self.llm_client:
            context_note = f"\nUser context: {user_context}" if user_context else ""
            prompt = f"""Create a clear, concise answer for: {query}{context_note}

Based on these sources:
{self._format_summaries_for_prompt(source_summaries)}

Include:
- Direct answer to the question
- Key supporting points
- Brief source citations

Answer:"""
            return await self._call_llm(prompt, max_tokens=1000)

        # Fallback: Balanced synthesis
        synthesis = f"## {query}\n\n"

        # Combine summaries
        synthesis += "### Summary\n"
        for summary in source_summaries[:3]:
            synthesis += f"{summary['summary']}\n\n"

        # Key takeaways
        synthesis += "### Key Points\n"
        all_points = []
        for summary in source_summaries:
            all_points.extend(summary['key_points'][:2])
        for point in all_points[:5]:
            synthesis += f"- {point}\n"

        # Citations
        synthesis += "\n### Sources\n"
        for i, summary in enumerate(source_summaries, 1):
            synthesis += f"{i}. {summary['title']} ({summary['type']})\n"

        return synthesis

    async def _create_summary(self, query: str, synthesis: str) -> str:
        """Create a brief summary of the synthesis"""
        if self.llm_client:
            prompt = f"""Create a 1-2 sentence summary of this research result:

Query: {query}
Result: {synthesis[:1000]}

Summary:"""
            return await self._call_llm(prompt, max_tokens=100)

        # Fallback: First ~150 chars of synthesis
        clean_synthesis = synthesis.replace('#', '').replace('*', '').strip()
        if len(clean_synthesis) > 150:
            return clean_synthesis[:147] + "..."
        return clean_synthesis

    def _format_summaries_for_prompt(self, summaries: List[Dict[str, Any]]) -> str:
        """Format source summaries for LLM prompt"""
        formatted = []
        for i, s in enumerate(summaries, 1):
            formatted.append(f"""
Source {i}: {s['title']}
Type: {s['type']} | Reliability: {s['reliability']:.0%}
Summary: {s['summary']}
Key points: {', '.join(s['key_points'][:3])}
""")
        return "\n".join(formatted)

    async def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """Call LLM for synthesis (placeholder for actual implementation)"""
        if self.llm_client:
            try:
                response = await self.llm_client.complete(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                return response
            except Exception as e:
                logger.error(f"LLM call failed: {e}")

        # Return prompt indication if no LLM
        return f"[LLM synthesis would process: {prompt[:100]}...]"

    def format_for_personality(
        self,
        synthesis: str,
        personality_style: Dict[str, Any],
    ) -> str:
        """Adjust synthesis formatting for personality style"""
        # This would be expanded based on personality settings
        # For now, return as-is
        return synthesis

    def get_output_format_for_depth(self, depth: ResearchDepth) -> OutputFormat:
        """Map research depth to output format"""
        mapping = {
            ResearchDepth.TWEET: OutputFormat.TWEET,
            ResearchDepth.QUICK: OutputFormat.BULLET_POINTS,
            ResearchDepth.MEDIUM: OutputFormat.ONE_PAGER,
            ResearchDepth.DEEP: OutputFormat.DEEP_DIVE,
        }
        return mapping.get(depth, OutputFormat.ONE_PAGER)
