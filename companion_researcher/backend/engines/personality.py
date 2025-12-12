"""
Personality Engine - Manages companion personality profiles and conversation style
"""
import json
from pathlib import Path
from typing import Dict, Optional, List
import logging

from ..models import (
    Personality,
    PersonalitySettings,
    VoiceSettings,
    Guardrails,
    ResearchPreferences,
    Message,
    ConversationContext,
)
from ..config import settings

logger = logging.getLogger(__name__)


class PersonalityEngine:
    """
    Manages personality profiles and applies them to conversations.

    Responsibilities:
    - Load/save personality configurations from JSON files
    - Hot-swap between different personality profiles
    - Generate system prompts based on personality settings
    - Transform responses to match personality style
    """

    def __init__(self, personalities_dir: Optional[Path] = None):
        self.personalities_dir = personalities_dir or settings.personalities_dir
        self._personalities: Dict[str, Personality] = {}
        self._active_personality_id: str = "default"
        self._load_all_personalities()

    def _load_all_personalities(self) -> None:
        """Load all personality profiles from the personalities directory"""
        self.personalities_dir.mkdir(parents=True, exist_ok=True)

        for json_file in self.personalities_dir.glob("*.json"):
            try:
                personality = self._load_personality_file(json_file)
                self._personalities[personality.id] = personality
                logger.info(f"Loaded personality: {personality.id}")
            except Exception as e:
                logger.error(f"Failed to load personality from {json_file}: {e}")

        if not self._personalities:
            logger.warning("No personalities found, creating default")
            self._create_default_personality()

    def _load_personality_file(self, file_path: Path) -> Personality:
        """Load a single personality from a JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)

        return Personality(
            id=data.get("id", file_path.stem),
            name=data.get("name", "Unnamed"),
            description=data.get("description", ""),
            system_prompt=data.get("system_prompt", ""),
            settings=PersonalitySettings(**data.get("settings", {})),
            voice=VoiceSettings(**data.get("voice", {})),
            guardrails=Guardrails(**data.get("guardrails", {})),
            research_preferences=ResearchPreferences(**data.get("research_preferences", {})),
        )

    def _create_default_personality(self) -> None:
        """Create a default personality if none exist"""
        default = Personality(
            id="default",
            name="Default Companion",
            description="A balanced, helpful research companion",
            system_prompt="You are a helpful research companion. You assist users with finding information, answering questions, and exploring ideas. You're knowledgeable, friendly, and thorough.",
            settings=PersonalitySettings(),
            voice=VoiceSettings(),
            guardrails=Guardrails(),
            research_preferences=ResearchPreferences(),
        )
        self._personalities["default"] = default
        self.save_personality(default)

    def get_personality(self, personality_id: str) -> Optional[Personality]:
        """Get a personality by ID"""
        return self._personalities.get(personality_id)

    def get_active_personality(self) -> Personality:
        """Get the currently active personality"""
        return self._personalities.get(self._active_personality_id,
                                       self._personalities.get("default"))

    def set_active_personality(self, personality_id: str) -> bool:
        """Set the active personality by ID"""
        if personality_id in self._personalities:
            self._active_personality_id = personality_id
            logger.info(f"Switched to personality: {personality_id}")
            return True
        logger.warning(f"Personality not found: {personality_id}")
        return False

    def list_personalities(self) -> List[Personality]:
        """List all available personalities"""
        return list(self._personalities.values())

    def save_personality(self, personality: Personality) -> None:
        """Save a personality to disk"""
        file_path = self.personalities_dir / f"{personality.id}.json"
        data = {
            "id": personality.id,
            "name": personality.name,
            "description": personality.description,
            "system_prompt": personality.system_prompt,
            "settings": personality.settings.model_dump(),
            "voice": personality.voice.model_dump(),
            "guardrails": personality.guardrails.model_dump(),
            "research_preferences": personality.research_preferences.model_dump(),
        }
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        self._personalities[personality.id] = personality
        logger.info(f"Saved personality: {personality.id}")

    def update_personality(
        self,
        personality_id: str,
        settings: Optional[PersonalitySettings] = None,
        guardrails: Optional[Guardrails] = None,
        research_preferences: Optional[ResearchPreferences] = None,
        system_prompt: Optional[str] = None,
    ) -> Optional[Personality]:
        """Update an existing personality's settings"""
        personality = self._personalities.get(personality_id)
        if not personality:
            return None

        if settings:
            personality.settings = settings
        if guardrails:
            personality.guardrails = guardrails
        if research_preferences:
            personality.research_preferences = research_preferences
        if system_prompt:
            personality.system_prompt = system_prompt

        self.save_personality(personality)
        return personality

    def generate_system_prompt(
        self,
        personality: Optional[Personality] = None,
        context: Optional[ConversationContext] = None,
    ) -> str:
        """
        Generate a complete system prompt based on personality settings.

        This combines the base system prompt with dynamic adjustments
        based on the personality settings sliders.
        """
        if personality is None:
            personality = self.get_active_personality()

        parts = [personality.system_prompt]

        # Add style guidance based on settings
        style_guidance = self._generate_style_guidance(personality.settings)
        if style_guidance:
            parts.append(f"\n\nCommunication style guidelines:\n{style_guidance}")

        # Add guardrails
        guardrail_text = self._generate_guardrails_text(personality.guardrails)
        if guardrail_text:
            parts.append(f"\n\nImportant guidelines:\n{guardrail_text}")

        # Add research preferences context
        if personality.research_preferences:
            research_text = self._generate_research_context(personality.research_preferences)
            parts.append(f"\n\nResearch approach:\n{research_text}")

        return "\n".join(parts)

    def _generate_style_guidance(self, settings: PersonalitySettings) -> str:
        """Generate style guidance based on personality settings"""
        guidance = []

        # Tone guidance
        if settings.tone_scale < 30:
            guidance.append("- Maintain a serious, professional tone")
        elif settings.tone_scale > 70:
            guidance.append("- Be playful and lighthearted in your responses")
        else:
            guidance.append("- Balance warmth with professionalism")

        # Depth guidance
        if settings.depth_scale < 30:
            guidance.append("- Keep responses brief and to the point")
        elif settings.depth_scale > 70:
            guidance.append("- Provide comprehensive, detailed explanations")
        else:
            guidance.append("- Provide moderate detail, expanding when helpful")

        # Critical vs Supportive
        if settings.critical_scale < 30:
            guidance.append("- Be analytical and point out potential issues or flaws")
        elif settings.critical_scale > 70:
            guidance.append("- Focus on encouragement and positive aspects")
        else:
            guidance.append("- Balance constructive feedback with support")

        # Speed/thoroughness
        if settings.speed_scale < 30:
            guidance.append("- Prioritize quick, actionable answers")
        elif settings.speed_scale > 70:
            guidance.append("- Take time to be thorough and comprehensive")

        # Verbosity
        verbosity_map = {
            "minimal": "- Use as few words as possible",
            "concise": "- Be concise but complete",
            "medium": "- Use moderate detail",
            "detailed": "- Provide rich, detailed responses",
            "comprehensive": "- Be exhaustive in your explanations",
        }
        if settings.verbosity in verbosity_map:
            guidance.append(verbosity_map[settings.verbosity])

        # Formality
        formality_map = {
            "formal": "- Use formal, professional language",
            "professional": "- Maintain professional but approachable language",
            "conversational": "- Use natural, conversational language",
            "casual": "- Be casual and relaxed in your communication",
            "warm": "- Be warm and empathetic in your tone",
        }
        if settings.formality in formality_map:
            guidance.append(formality_map[settings.formality])

        return "\n".join(guidance)

    def _generate_guardrails_text(self, guardrails: Guardrails) -> str:
        """Generate guardrails text for system prompt"""
        rules = []

        if guardrails.avoid_topics:
            topics = ", ".join(guardrails.avoid_topics)
            rules.append(f"- Avoid discussing these topics: {topics}")

        if guardrails.always_cite_sources:
            rules.append("- Always cite your sources when providing information")

        if guardrails.show_confidence:
            rules.append("- Indicate your confidence level for uncertain information")

        if guardrails.max_response_length:
            rules.append(f"- Keep responses under {guardrails.max_response_length} words")

        return "\n".join(rules)

    def _generate_research_context(self, prefs: ResearchPreferences) -> str:
        """Generate research context for system prompt"""
        lines = []

        if prefs.preferred_source_types:
            sources = ", ".join(prefs.preferred_source_types)
            lines.append(f"- Prefer these source types: {sources}")

        depth_map = {
            "quick": "quick overviews",
            "medium": "balanced depth",
            "deep": "comprehensive analysis",
        }
        if prefs.default_depth in depth_map:
            lines.append(f"- Default to {depth_map[prefs.default_depth]}")

        return "\n".join(lines)

    def apply_personality_to_response(
        self,
        response: str,
        personality: Optional[Personality] = None,
    ) -> str:
        """
        Post-process a response to ensure it matches personality style.

        This is a lightweight transformation - the main personality
        application happens in the system prompt.
        """
        if personality is None:
            personality = self.get_active_personality()

        # Apply max length if set
        if personality.guardrails.max_response_length:
            words = response.split()
            if len(words) > personality.guardrails.max_response_length:
                response = " ".join(words[:personality.guardrails.max_response_length]) + "..."

        return response

    def create_personality(
        self,
        personality_id: str,
        name: str,
        description: str,
        system_prompt: str,
        settings: Optional[PersonalitySettings] = None,
        voice: Optional[VoiceSettings] = None,
        guardrails: Optional[Guardrails] = None,
        research_preferences: Optional[ResearchPreferences] = None,
    ) -> Personality:
        """Create a new personality profile"""
        personality = Personality(
            id=personality_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            settings=settings or PersonalitySettings(),
            voice=voice or VoiceSettings(),
            guardrails=guardrails or Guardrails(),
            research_preferences=research_preferences or ResearchPreferences(),
        )
        self.save_personality(personality)
        return personality

    def delete_personality(self, personality_id: str) -> bool:
        """Delete a personality profile"""
        if personality_id == "default":
            logger.warning("Cannot delete default personality")
            return False

        if personality_id not in self._personalities:
            return False

        # Delete file
        file_path = self.personalities_dir / f"{personality_id}.json"
        if file_path.exists():
            file_path.unlink()

        # Remove from memory
        del self._personalities[personality_id]

        # Reset active if deleted
        if self._active_personality_id == personality_id:
            self._active_personality_id = "default"

        logger.info(f"Deleted personality: {personality_id}")
        return True
