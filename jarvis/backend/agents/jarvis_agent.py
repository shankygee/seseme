"""
Jarvis Agent - AI Brain with Tool Execution

The main AI agent that processes user requests, decides when to use tools,
and generates natural responses. Powered by Claude.
"""
import asyncio
import logging
from typing import AsyncIterator

import anthropic

from agents.tools import JARVIS_TOOLS, tool_executor

logger = logging.getLogger(__name__)

# System prompt that defines Jarvis's personality and capabilities
JARVIS_SYSTEM_PROMPT = """You are Jarvis, a sophisticated AI personal assistant inspired by the AI from Iron Man. You are helpful, witty, and highly capable.

## Personality
- Professional yet warm and personable
- Occasionally dry humor, but never at the user's expense
- Proactive in offering help and anticipating needs
- Concise in responses - you're speaking, not writing essays
- Confident but not arrogant

## Communication Style
- Speak naturally as if in conversation
- Keep responses brief and to the point (1-3 sentences typically)
- Use contractions (I'm, you're, it's)
- Address the user respectfully but not formally
- When executing tasks, briefly confirm what you're doing

## Capabilities
You can help with:
- Setting reminders and managing schedules
- Sending messages and emails
- Searching for information
- Controlling smart home devices
- Taking notes and managing tasks
- Playing music
- Getting weather and news
- Calculations and conversions
- General knowledge and advice

## Important Guidelines
1. Use tools when the user asks you to DO something (set reminder, send message, etc.)
2. Don't use tools for simple questions you can answer directly
3. Always confirm important actions before executing (sending messages, etc.)
4. If you're unsure what the user wants, ask for clarification
5. Be honest about limitations - say when you can't do something
6. Protect user privacy - never share or expose personal information

## Response Format
- Keep spoken responses SHORT and natural
- Avoid bullet points and formatting - you're speaking aloud
- Don't narrate your actions excessively
- Sound human, not like a computer reading a manual

Remember: Your responses will be converted to speech, so write as you would speak."""


class JarvisAgent:
    """
    The AI brain of the Jarvis assistant.

    Uses Claude API with tool use to:
    - Understand user requests
    - Execute tasks via tools
    - Generate natural responses
    """

    def __init__(self, settings):
        self.settings = settings
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_tokens = 1024

    async def process(
        self,
        user_message: str,
        conversation_history: list[dict],
    ) -> dict:
        """
        Process a user message and generate a response.

        Args:
            user_message: The user's message
            conversation_history: Previous messages in Claude format

        Returns:
            dict with 'text' (response) and 'tools_used' (list of tool names)
        """
        # Build messages list
        messages = conversation_history + [
            {"role": "user", "content": user_message}
        ]

        tools_used = []
        response_text = ""

        # Run in thread pool since anthropic client is sync
        loop = asyncio.get_event_loop()

        try:
            # Initial Claude call
            response = await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=JARVIS_SYSTEM_PROMPT,
                    tools=JARVIS_TOOLS,
                    messages=messages,
                )
            )

            # Handle tool use loop
            while response.stop_reason == "tool_use":
                # Extract tool calls
                tool_calls = [
                    block for block in response.content
                    if block.type == "tool_use"
                ]

                # Execute tools
                tool_results = []
                for tool_call in tool_calls:
                    logger.info(f"Executing tool: {tool_call.name}")
                    tools_used.append(tool_call.name)

                    result = await tool_executor.execute(
                        tool_call.name,
                        tool_call.input,
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": str(result.data) if result.success else f"Error: {result.error}",
                    })

                # Continue conversation with tool results
                messages = messages + [
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": tool_results},
                ]

                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        system=JARVIS_SYSTEM_PROMPT,
                        tools=JARVIS_TOOLS,
                        messages=messages,
                    )
                )

            # Extract final text response
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            return {
                "text": response_text,
                "tools_used": tools_used,
            }

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return {
                "text": "I'm having trouble connecting right now. Please try again in a moment.",
                "tools_used": [],
                "error": str(e),
            }

    async def process_stream(
        self,
        user_message: str,
        conversation_history: list[dict],
    ) -> AsyncIterator[str]:
        """
        Process a user message and stream the response.

        Yields text chunks as they're generated for lower latency.
        """
        messages = conversation_history + [
            {"role": "user", "content": user_message}
        ]

        loop = asyncio.get_event_loop()

        try:
            # Use streaming API
            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=JARVIS_SYSTEM_PROMPT,
                tools=JARVIS_TOOLS,
                messages=messages,
            ) as stream:
                current_tool_use = None

                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            current_tool_use = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input": "",
                            }

                    elif event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield event.delta.text
                        elif hasattr(event.delta, "partial_json"):
                            if current_tool_use:
                                current_tool_use["input"] += event.delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_tool_use:
                            # Execute the tool
                            import json
                            try:
                                tool_input = json.loads(current_tool_use["input"])
                            except json.JSONDecodeError:
                                tool_input = {}

                            result = await tool_executor.execute(
                                current_tool_use["name"],
                                tool_input,
                            )
                            # For streaming, we'd need to continue the conversation
                            # This is simplified - full implementation would loop back
                            current_tool_use = None

        except anthropic.APIError as e:
            logger.error(f"Streaming error: {e}")
            yield "I'm having trouble right now. Please try again."

    async def get_quick_response(self, user_message: str) -> str:
        """
        Get a quick response without tool use.
        Used for simple greetings and acknowledgments.
        """
        loop = asyncio.get_event_loop()

        response = await loop.run_in_executor(
            None,
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=256,
                system="You are Jarvis, a helpful AI assistant. Keep responses very brief (1 sentence).",
                messages=[{"role": "user", "content": user_message}],
            )
        )

        return response.content[0].text
