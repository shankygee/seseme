"""
Intent Parser - Determines user intent and routes appropriately
"""
import re
import logging
from typing import Tuple, Optional, Dict, Any, List
from enum import Enum

from ..models import ResearchDepth, Message, ConversationContext

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of user intent"""
    CASUAL_CHAT = "casual_chat"
    RESEARCH_REQUEST = "research_request"
    FOLLOWUP_QUESTION = "followup_question"
    CLARIFICATION = "clarification"
    COMMAND = "command"
    FEEDBACK = "feedback"


class IntentParser:
    """
    Parses user input to determine intent and extract relevant information.

    Responsibilities:
    - Detect if input is casual conversation or research request
    - Extract research parameters (depth, topics, constraints)
    - Identify follow-up questions vs new topics
    - Parse commands and special requests
    """

    # Research trigger phrases
    RESEARCH_TRIGGERS = [
        r'\bresearch\b',
        r'\bfind\s+(out|information|data)\b',
        r'\blook\s+up\b',
        r'\bsearch\s+for\b',
        r'\bwhat\s+(is|are|was|were)\b',
        r'\bhow\s+(do|does|did|to|can)\b',
        r'\bwhy\s+(is|are|do|does|did)\b',
        r'\bexplain\b',
        r'\bcompare\b',
        r'\banalyze\b',
        r'\bsummarize\b',
        r'\bwhat\'s\s+the\s+(best|top|latest)\b',
        r'\btell\s+me\s+about\b',
        r'\bcan\s+you\s+(find|look|search|research)\b',
        r'\bi\s+(want|need)\s+to\s+(know|learn|understand)\b',
    ]

    # Casual chat indicators
    CASUAL_INDICATORS = [
        r'^(hi|hello|hey|sup|yo|greetings)\b',
        r'^(good\s+)?(morning|afternoon|evening|night)\b',
        r'\bhow\s+are\s+you\b',
        r'\bthank(s| you)\b',
        r'\b(bye|goodbye|see you|later)\b',
        r'^(yes|no|yeah|nope|sure|okay|ok|yep)\b',
        r'\b(haha|lol|lmao|rofl)\b',
        r'\bthat\'s\s+(cool|nice|great|awesome|interesting)\b',
    ]

    # Depth indicators
    DEEP_INDICATORS = [
        r'\bdeep\s+dive\b',
        r'\bcomprehensive\b',
        r'\bthorough(ly)?\b',
        r'\bdetail(ed)?\b',
        r'\bexhaustive\b',
        r'\bin\s+depth\b',
        r'\bfull\s+(analysis|breakdown|report)\b',
    ]

    QUICK_INDICATORS = [
        r'\bquick(ly)?\b',
        r'\bbrief(ly)?\b',
        r'\bshort\b',
        r'\bsummary\b',
        r'\boverview\b',
        r'\btl;?dr\b',
        r'\bjust\s+the\s+(basics|gist|highlights)\b',
    ]

    # Command patterns
    COMMAND_PATTERNS = {
        "switch_personality": r'\bswitch\s+to\s+(\w+)\s*(mode|personality)?\b',
        "set_depth": r'\bset\s+depth\s+to\s+(\w+)\b',
        "list_sources": r'\b(show|list)\s+(my\s+)?sources\b',
        "save_session": r'\bsave\s+(this\s+)?(session|conversation)\b',
        "clear_context": r'\b(clear|reset)\s+(context|history|conversation)\b',
    }

    def __init__(self):
        # Compile patterns for efficiency
        self._research_patterns = [re.compile(p, re.IGNORECASE) for p in self.RESEARCH_TRIGGERS]
        self._casual_patterns = [re.compile(p, re.IGNORECASE) for p in self.CASUAL_INDICATORS]
        self._deep_patterns = [re.compile(p, re.IGNORECASE) for p in self.DEEP_INDICATORS]
        self._quick_patterns = [re.compile(p, re.IGNORECASE) for p in self.QUICK_INDICATORS]
        self._command_patterns = {k: re.compile(v, re.IGNORECASE) for k, v in self.COMMAND_PATTERNS.items()}

    def parse(
        self,
        user_input: str,
        context: Optional[ConversationContext] = None,
    ) -> Dict[str, Any]:
        """
        Parse user input and return intent analysis.

        Returns:
            Dictionary containing:
            - intent_type: IntentType enum value
            - confidence: float 0-1
            - research_depth: Optional[ResearchDepth]
            - extracted_query: str (cleaned query for research)
            - command: Optional[Dict] for command intents
            - is_followup: bool
            - metadata: Dict with additional context
        """
        user_input = user_input.strip()

        # Check for commands first
        command_result = self._check_commands(user_input)
        if command_result:
            return {
                "intent_type": IntentType.COMMAND,
                "confidence": 0.95,
                "command": command_result,
                "research_depth": None,
                "extracted_query": user_input,
                "is_followup": False,
                "metadata": {},
            }

        # Calculate intent scores
        research_score = self._calculate_research_score(user_input)
        casual_score = self._calculate_casual_score(user_input)

        # Check for follow-up indicators
        is_followup = self._is_followup(user_input, context)

        # Determine primary intent
        if casual_score > research_score and casual_score > 0.5:
            intent_type = IntentType.CASUAL_CHAT
            confidence = casual_score
        elif research_score > 0.3 or self._has_question_structure(user_input):
            intent_type = IntentType.RESEARCH_REQUEST
            confidence = max(research_score, 0.6)
        else:
            # Default to research for ambiguous queries
            intent_type = IntentType.RESEARCH_REQUEST if len(user_input) > 20 else IntentType.CASUAL_CHAT
            confidence = 0.5

        # Adjust for follow-ups
        if is_followup and intent_type == IntentType.RESEARCH_REQUEST:
            intent_type = IntentType.FOLLOWUP_QUESTION
            confidence = min(confidence + 0.1, 1.0)

        # Determine research depth
        research_depth = self._determine_depth(user_input)

        # Extract clean query
        extracted_query = self._extract_query(user_input)

        return {
            "intent_type": intent_type,
            "confidence": confidence,
            "research_depth": research_depth,
            "extracted_query": extracted_query,
            "is_followup": is_followup,
            "command": None,
            "metadata": {
                "research_score": research_score,
                "casual_score": casual_score,
                "word_count": len(user_input.split()),
                "has_question_mark": "?" in user_input,
            },
        }

    def _calculate_research_score(self, text: str) -> float:
        """Calculate how likely this is a research request"""
        matches = sum(1 for pattern in self._research_patterns if pattern.search(text))
        base_score = min(matches * 0.25, 0.8)

        # Boost for question marks
        if "?" in text:
            base_score += 0.15

        # Boost for longer queries (more specific)
        word_count = len(text.split())
        if word_count > 10:
            base_score += 0.1
        elif word_count > 5:
            base_score += 0.05

        return min(base_score, 1.0)

    def _calculate_casual_score(self, text: str) -> float:
        """Calculate how likely this is casual chat"""
        matches = sum(1 for pattern in self._casual_patterns if pattern.search(text))
        base_score = min(matches * 0.3, 0.9)

        # Short messages are more likely casual
        word_count = len(text.split())
        if word_count <= 3:
            base_score += 0.2
        elif word_count <= 5:
            base_score += 0.1

        return min(base_score, 1.0)

    def _has_question_structure(self, text: str) -> bool:
        """Check if text has question structure"""
        question_starters = ['what', 'why', 'how', 'when', 'where', 'who', 'which', 'can', 'could', 'would', 'should', 'is', 'are', 'do', 'does']
        first_word = text.lower().split()[0] if text.split() else ""
        return first_word in question_starters or text.endswith("?")

    def _is_followup(self, text: str, context: Optional[ConversationContext]) -> bool:
        """Determine if this is a follow-up to previous conversation"""
        if not context or not context.messages:
            return False

        followup_indicators = [
            r'^(and|also|additionally|furthermore)\b',
            r'^(what|how)\s+about\b',
            r'^(can you|could you)\s+(also|tell me more)\b',
            r'\bmore\s+(details?|info(rmation)?|about)\b',
            r'^(yes|yeah|sure),?\s+(and|but|so)\b',
            r'\b(that|this|it)\b',  # Pronouns referring to previous context
        ]

        for pattern in followup_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # Check if very short (likely a follow-up)
        if len(text.split()) <= 5 and context.messages:
            return True

        return False

    def _determine_depth(self, text: str) -> ResearchDepth:
        """Determine desired research depth from text"""
        # Check for explicit deep indicators
        for pattern in self._deep_patterns:
            if pattern.search(text):
                return ResearchDepth.DEEP

        # Check for quick indicators
        for pattern in self._quick_patterns:
            if pattern.search(text):
                return ResearchDepth.QUICK

        # Default based on query complexity
        word_count = len(text.split())
        if word_count > 20:
            return ResearchDepth.DEEP
        elif word_count < 8:
            return ResearchDepth.QUICK
        else:
            return ResearchDepth.MEDIUM

    def _extract_query(self, text: str) -> str:
        """Extract the core query from user input"""
        # Remove common prefixes
        prefixes_to_remove = [
            r'^(can you|could you|please|i want you to|i need you to)\s+',
            r'^(research|find|look up|search for|tell me about)\s+',
            r'^(what is|what are|what\'s)\s+',
        ]

        query = text
        for pattern in prefixes_to_remove:
            query = re.sub(pattern, '', query, flags=re.IGNORECASE)

        # Remove trailing punctuation except question marks
        query = re.sub(r'[.!,;:]+$', '', query)

        return query.strip()

    def _check_commands(self, text: str) -> Optional[Dict[str, Any]]:
        """Check if input is a command"""
        for command_name, pattern in self._command_patterns.items():
            match = pattern.search(text)
            if match:
                return {
                    "name": command_name,
                    "args": match.groups(),
                    "raw": text,
                }
        return None

    def get_intent_explanation(self, intent_result: Dict[str, Any]) -> str:
        """Generate human-readable explanation of intent parsing"""
        intent_type = intent_result["intent_type"]
        confidence = intent_result["confidence"]

        explanations = {
            IntentType.CASUAL_CHAT: "This appears to be casual conversation.",
            IntentType.RESEARCH_REQUEST: "This looks like a research question.",
            IntentType.FOLLOWUP_QUESTION: "This seems to be a follow-up to the previous discussion.",
            IntentType.CLARIFICATION: "You're asking for clarification.",
            IntentType.COMMAND: "This is a command.",
            IntentType.FEEDBACK: "You're providing feedback.",
        }

        base = explanations.get(intent_type, "Intent unclear.")
        return f"{base} (confidence: {confidence:.0%})"
