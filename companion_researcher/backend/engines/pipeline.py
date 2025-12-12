"""
Data Pipeline - Orchestrates the full research and conversation flow
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from .personality import PersonalityEngine
from .research import ResearchEngine
from .synthesis import SynthesisEngine, OutputFormat
from .intent import IntentParser, IntentType
from ..models import (
    Message,
    MessageRole,
    ConversationContext,
    ResearchResult,
    ResearchDepth,
    ChatRequest,
    ChatResponse,
    Session,
)
from ..config import settings

logger = logging.getLogger(__name__)


class DataPipeline:
    """
    Main orchestration pipeline that coordinates all engines.

    Flow:
    1. User input → Intent parsing
    2. If research → Task planning → Retrieval → Processing → Synthesis
    3. Apply personality to response
    4. Deliver to user
    """

    def __init__(
        self,
        personality_engine: Optional[PersonalityEngine] = None,
        research_engine: Optional[ResearchEngine] = None,
        synthesis_engine: Optional[SynthesisEngine] = None,
        intent_parser: Optional[IntentParser] = None,
    ):
        self.personality_engine = personality_engine or PersonalityEngine()
        self.research_engine = research_engine or ResearchEngine()
        self.synthesis_engine = synthesis_engine or SynthesisEngine()
        self.intent_parser = intent_parser or IntentParser()

        # Session storage (in-memory for now, would use DB in production)
        self._sessions: Dict[str, Session] = {}
        self._llm_client = None  # Would be initialized with actual LLM

    async def process_message(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        """
        Main entry point for processing user messages.

        This orchestrates the full pipeline from input to response.
        """
        # Get or create session
        session = self._get_or_create_session(
            request.session_id,
            request.personality_id,
        )

        # Set active personality
        self.personality_engine.set_active_personality(request.personality_id)
        personality = self.personality_engine.get_active_personality()

        # Create conversation context
        context = ConversationContext(
            messages=session.messages,
            personality_id=request.personality_id,
            session_id=session.id,
        )

        # Add user message to session
        user_message = Message(
            role=MessageRole.USER,
            content=request.message,
        )
        session.messages.append(user_message)

        # Step 1: Parse intent
        intent_result = self.intent_parser.parse(request.message, context)
        logger.info(f"Intent parsed: {intent_result['intent_type'].value} "
                   f"(confidence: {intent_result['confidence']:.2f})")

        # Step 2: Route based on intent
        response_content = ""
        research_result = None
        is_research = False

        if intent_result["intent_type"] == IntentType.COMMAND:
            response_content = await self._handle_command(
                intent_result["command"],
                session,
            )

        elif intent_result["intent_type"] in [
            IntentType.RESEARCH_REQUEST,
            IntentType.FOLLOWUP_QUESTION,
        ]:
            # Research path
            is_research = True
            research_result = await self._execute_research_pipeline(
                query=intent_result["extracted_query"],
                depth=request.research_depth or intent_result["research_depth"],
                context=context,
                personality=personality,
            )
            response_content = self._format_research_response(
                research_result,
                personality,
            )

        else:
            # Casual chat path
            response_content = await self._generate_casual_response(
                request.message,
                context,
                personality,
            )

        # Step 3: Apply personality styling
        response_content = self.personality_engine.apply_personality_to_response(
            response_content,
            personality,
        )

        # Step 4: Create assistant message
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response_content,
            metadata={
                "is_research": is_research,
                "intent": intent_result["intent_type"].value,
                "confidence": intent_result["confidence"],
            },
        )
        session.messages.append(assistant_message)
        session.updated_at = datetime.utcnow()

        # Build response
        return ChatResponse(
            response=response_content,
            session_id=session.id,
            message_id=assistant_message.id,
            is_research_response=is_research,
            research_result=research_result,
            metadata={
                "personality": personality.id,
                "intent": intent_result["intent_type"].value,
            },
        )

    async def _execute_research_pipeline(
        self,
        query: str,
        depth: ResearchDepth,
        context: ConversationContext,
        personality,
    ) -> ResearchResult:
        """Execute the full research pipeline"""
        logger.info(f"Starting research pipeline for: {query} (depth: {depth.value})")

        # Step 1: Create research task
        task = await self.research_engine.create_research_task(
            query=query,
            depth=depth,
            source_types=None,  # Use defaults from personality
            max_sources=settings.max_sources_per_query,
        )

        # Step 2: Execute research
        result = await self.research_engine.execute_research(task)

        # Step 3: Synthesize results
        output_format = self.synthesis_engine.get_output_format_for_depth(depth)

        # Add user context from conversation
        user_context = self._extract_user_context(context)

        result = await self.synthesis_engine.synthesize(
            research_result=result,
            output_format=output_format,
            user_context=user_context,
        )

        return result

    def _format_research_response(
        self,
        result: ResearchResult,
        personality,
    ) -> str:
        """Format research result for delivery"""
        parts = []

        # Main synthesis
        if result.synthesis:
            parts.append(result.synthesis)

        # Confidence indicator (if personality shows it)
        if personality.guardrails.show_confidence:
            confidence_pct = result.confidence_score * 100
            if confidence_pct >= 80:
                confidence_label = "High confidence"
            elif confidence_pct >= 50:
                confidence_label = "Moderate confidence"
            else:
                confidence_label = "Lower confidence - consider additional research"
            parts.append(f"\n*{confidence_label} ({confidence_pct:.0f}%)*")

        # Citations (if personality shows them)
        if personality.guardrails.always_cite_sources and result.citations:
            parts.append("\n---\n**Sources:**")
            for i, citation in enumerate(result.citations[:5], 1):
                parts.append(f"{i}. [{citation['title']}]({citation['url']})")

        return "\n".join(parts)

    async def _generate_casual_response(
        self,
        message: str,
        context: ConversationContext,
        personality,
    ) -> str:
        """Generate a casual conversation response"""
        # Build system prompt
        system_prompt = self.personality_engine.generate_system_prompt(
            personality,
            context,
        )

        # In production, this would call an LLM
        # For now, return a template response
        if self._llm_client:
            messages = [{"role": "system", "content": system_prompt}]
            for msg in context.messages[-10:]:  # Last 10 messages for context
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })
            messages.append({"role": "user", "content": message})

            response = await self._llm_client.chat(messages)
            return response

        # Fallback response
        return self._generate_fallback_response(message, personality)

    def _generate_fallback_response(self, message: str, personality) -> str:
        """Generate a fallback response when LLM is unavailable"""
        message_lower = message.lower()

        if any(g in message_lower for g in ['hi', 'hello', 'hey']):
            if personality.settings.tone_scale > 60:
                return "Hey there! Great to see you. What's on your mind today?"
            else:
                return "Hello. How can I assist you today?"

        if 'thank' in message_lower:
            if personality.settings.tone_scale > 60:
                return "You're welcome! Happy to help anytime."
            else:
                return "You're welcome. Let me know if you need anything else."

        if any(q in message_lower for q in ['how are you', "how's it going"]):
            return "I'm doing well, thanks for asking! Ready to help you with whatever you need."

        # Default
        return ("I'm here to help! You can ask me research questions, and I'll search "
                "for information and synthesize it for you. Or we can just chat - "
                "whatever works for you.")

    async def _handle_command(
        self,
        command: Dict[str, Any],
        session: Session,
    ) -> str:
        """Handle system commands"""
        command_name = command["name"]
        args = command.get("args", ())

        if command_name == "switch_personality":
            personality_id = args[0] if args else "default"
            if self.personality_engine.set_active_personality(personality_id):
                personality = self.personality_engine.get_active_personality()
                session.personality_id = personality_id
                return f"Switched to {personality.name} mode. {personality.description}"
            else:
                available = [p.id for p in self.personality_engine.list_personalities()]
                return f"Personality '{personality_id}' not found. Available: {', '.join(available)}"

        elif command_name == "set_depth":
            depth = args[0] if args else "medium"
            return f"Research depth set to: {depth}"

        elif command_name == "list_sources":
            return "Source listing would show recent research sources here."

        elif command_name == "save_session":
            return f"Session saved: {session.id}"

        elif command_name == "clear_context":
            session.messages = []
            return "Conversation context cleared. Starting fresh!"

        return f"Unknown command: {command_name}"

    def _extract_user_context(self, context: ConversationContext) -> Optional[str]:
        """Extract relevant user context from conversation history"""
        if not context.messages:
            return None

        # Look for context clues in recent messages
        recent_messages = context.messages[-5:]
        context_clues = []

        for msg in recent_messages:
            if msg.role == MessageRole.USER:
                # Look for self-identification or project mentions
                content_lower = msg.content.lower()
                if any(phrase in content_lower for phrase in ['i am a', "i'm a", 'my project', 'i work']):
                    context_clues.append(msg.content)

        if context_clues:
            return "User context: " + " | ".join(context_clues[-2:])
        return None

    def _get_or_create_session(
        self,
        session_id: Optional[str],
        personality_id: str,
    ) -> Session:
        """Get existing session or create new one"""
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        new_session = Session(
            id=session_id or str(uuid.uuid4()),
            personality_id=personality_id,
        )
        self._sessions[new_session.id] = new_session
        return new_session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[Session]:
        """List all sessions"""
        return list(self._sessions.values())

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def close(self):
        """Clean up resources"""
        await self.research_engine.close()
