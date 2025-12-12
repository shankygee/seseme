"""
Pydantic models for API schemas and data structures
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import uuid


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ResearchDepth(str, Enum):
    TWEET = "tweet"  # Very short, 1-2 sentences
    QUICK = "quick"  # Fast scan, key points only
    MEDIUM = "medium"  # Balanced depth
    DEEP = "deep"  # Comprehensive research


class SourceType(str, Enum):
    WEB = "web"
    ACADEMIC = "academic"
    NEWS = "news"
    DOCUMENTATION = "documentation"
    VIDEO = "video"
    PDF = "pdf"
    LOCAL = "local"


# ============ Personality Models ============

class PersonalitySettings(BaseModel):
    """Settings for personality behavior"""
    tone: str = "balanced"
    tone_scale: int = Field(50, ge=0, le=100)
    depth: str = "medium"
    depth_scale: int = Field(50, ge=0, le=100)
    critical_vs_supportive: str = "balanced"
    critical_scale: int = Field(50, ge=0, le=100)
    speed: str = "balanced"
    speed_scale: int = Field(50, ge=0, le=100)
    verbosity: str = "medium"
    formality: str = "conversational"
    humor: str = "occasional"


class VoiceSettings(BaseModel):
    """Voice output settings"""
    enabled: bool = True
    speaker_id: int = 0


class Guardrails(BaseModel):
    """Safety and boundary settings"""
    avoid_topics: List[str] = []
    always_cite_sources: bool = True
    show_confidence: bool = True
    max_response_length: Optional[int] = None


class ResearchPreferences(BaseModel):
    """Research behavior preferences"""
    preferred_source_types: List[str] = ["academic", "news", "documentation"]
    source_weights: Dict[str, float] = {
        "academic": 1.0,
        "news": 0.8,
        "blogs": 0.6,
        "forums": 0.4
    }
    default_depth: str = "medium"


class Personality(BaseModel):
    """Complete personality profile"""
    id: str
    name: str
    description: str
    system_prompt: str
    settings: PersonalitySettings
    voice: VoiceSettings
    guardrails: Guardrails
    research_preferences: ResearchPreferences


# ============ Message Models ============

class Message(BaseModel):
    """A single conversation message"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}


class ConversationContext(BaseModel):
    """Context for a conversation including history"""
    messages: List[Message] = []
    personality_id: str = "default"
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


# ============ Research Models ============

class Source(BaseModel):
    """A research source"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    title: str
    content: str
    snippet: str
    source_type: SourceType
    reliability_score: float = Field(0.5, ge=0, le=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}


class ResearchTask(BaseModel):
    """A research task to be executed"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    sub_questions: List[str] = []
    depth: ResearchDepth = ResearchDepth.MEDIUM
    source_types: List[SourceType] = [SourceType.WEB]
    max_sources: int = 5
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ResearchResult(BaseModel):
    """Result from research engine"""
    task_id: str
    query: str
    sources: List[Source] = []
    raw_content: str = ""
    summary: str = ""
    synthesis: str = ""
    confidence_score: float = Field(0.5, ge=0, le=1)
    citations: List[Dict[str, str]] = []
    metadata: Dict[str, Any] = {}
    completed_at: datetime = Field(default_factory=datetime.utcnow)


# ============ API Request/Response Models ============

class ChatRequest(BaseModel):
    """Request for chat endpoint"""
    message: str
    personality_id: str = "default"
    session_id: Optional[str] = None
    include_voice: bool = False
    research_depth: Optional[ResearchDepth] = None


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    response: str
    session_id: str
    message_id: str
    is_research_response: bool = False
    research_result: Optional[ResearchResult] = None
    audio_url: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ResearchRequest(BaseModel):
    """Request for explicit research"""
    query: str
    depth: ResearchDepth = ResearchDepth.MEDIUM
    source_types: List[SourceType] = [SourceType.WEB]
    max_sources: int = 5
    personality_id: str = "default"


class PersonalityUpdateRequest(BaseModel):
    """Request to update personality settings"""
    settings: Optional[PersonalitySettings] = None
    guardrails: Optional[Guardrails] = None
    research_preferences: Optional[ResearchPreferences] = None
    system_prompt: Optional[str] = None


# ============ Session Models ============

class Session(BaseModel):
    """A conversation session"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    personality_id: str = "default"
    messages: List[Message] = []
    tags: List[str] = []
    project: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}


class SessionSummary(BaseModel):
    """Summary view of a session"""
    id: str
    personality_id: str
    message_count: int
    preview: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
