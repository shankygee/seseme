"""
FastAPI routes for Companion Researcher API
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from typing import List, Optional
import logging
import asyncio

from ..models import (
    ChatRequest,
    ChatResponse,
    ResearchRequest,
    ResearchResult,
    ResearchDepth,
    SourceType,
    Personality,
    PersonalityUpdateRequest,
    Session,
    SessionSummary,
)
from ..engines import DataPipeline, PersonalityEngine, ResearchEngine, SynthesisEngine

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize engines (in production, use dependency injection)
pipeline = DataPipeline()
personality_engine = pipeline.personality_engine
research_engine = pipeline.research_engine
synthesis_engine = pipeline.synthesis_engine


# ============ Chat Endpoints ============

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for conversation with the companion.

    This handles both casual conversation and research requests,
    automatically detecting intent and routing appropriately.
    """
    try:
        response = await pipeline.process_message(request)
        return response
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/chat/ws")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.

    Allows streaming responses and real-time updates during research.
    """
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            request = ChatRequest(**data)

            # Send processing status
            await websocket.send_json({
                "type": "status",
                "message": "Processing your request...",
            })

            response = await pipeline.process_message(request)

            await websocket.send_json({
                "type": "response",
                "data": response.model_dump(),
            })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })


# ============ Research Endpoints ============

@router.post("/research", response_model=ResearchResult)
async def research(request: ResearchRequest):
    """
    Explicit research endpoint for direct research queries.

    Use this when you want to bypass intent detection and
    directly execute a research task.
    """
    try:
        # Set personality for research preferences
        personality_engine.set_active_personality(request.personality_id)

        # Create and execute research task
        task = await research_engine.create_research_task(
            query=request.query,
            depth=request.depth,
            source_types=request.source_types,
            max_sources=request.max_sources,
        )

        result = await research_engine.execute_research(task)

        # Synthesize results
        output_format = synthesis_engine.get_output_format_for_depth(request.depth)
        result = await synthesis_engine.synthesize(result, output_format)

        return result

    except Exception as e:
        logger.error(f"Research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research/{task_id}", response_model=ResearchResult)
async def get_research_result(task_id: str):
    """Get a previously executed research result by task ID"""
    # In production, this would retrieve from storage
    raise HTTPException(status_code=404, detail="Research result not found")


# ============ Personality Endpoints ============

@router.get("/personalities", response_model=List[Personality])
async def list_personalities():
    """List all available personality profiles"""
    return personality_engine.list_personalities()


@router.get("/personalities/{personality_id}", response_model=Personality)
async def get_personality(personality_id: str):
    """Get a specific personality profile"""
    personality = personality_engine.get_personality(personality_id)
    if not personality:
        raise HTTPException(status_code=404, detail="Personality not found")
    return personality


@router.post("/personalities", response_model=Personality)
async def create_personality(personality: Personality):
    """Create a new personality profile"""
    try:
        return personality_engine.create_personality(
            personality_id=personality.id,
            name=personality.name,
            description=personality.description,
            system_prompt=personality.system_prompt,
            settings=personality.settings,
            voice=personality.voice,
            guardrails=personality.guardrails,
            research_preferences=personality.research_preferences,
        )
    except Exception as e:
        logger.error(f"Create personality error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/personalities/{personality_id}", response_model=Personality)
async def update_personality(personality_id: str, update: PersonalityUpdateRequest):
    """Update an existing personality profile"""
    personality = personality_engine.update_personality(
        personality_id=personality_id,
        settings=update.settings,
        guardrails=update.guardrails,
        research_preferences=update.research_preferences,
        system_prompt=update.system_prompt,
    )
    if not personality:
        raise HTTPException(status_code=404, detail="Personality not found")
    return personality


@router.delete("/personalities/{personality_id}")
async def delete_personality(personality_id: str):
    """Delete a personality profile"""
    if not personality_engine.delete_personality(personality_id):
        raise HTTPException(status_code=404, detail="Personality not found or cannot be deleted")
    return {"message": f"Personality '{personality_id}' deleted"}


@router.post("/personalities/{personality_id}/activate")
async def activate_personality(personality_id: str):
    """Set the active personality"""
    if not personality_engine.set_active_personality(personality_id):
        raise HTTPException(status_code=404, detail="Personality not found")
    return {"message": f"Activated personality: {personality_id}"}


@router.get("/personalities/active", response_model=Personality)
async def get_active_personality():
    """Get the currently active personality"""
    return personality_engine.get_active_personality()


# ============ Session Endpoints ============

@router.get("/sessions", response_model=List[SessionSummary])
async def list_sessions():
    """List all conversation sessions"""
    sessions = pipeline.list_sessions()
    return [
        SessionSummary(
            id=s.id,
            personality_id=s.personality_id,
            message_count=len(s.messages),
            preview=s.messages[0].content[:100] if s.messages else "",
            tags=s.tags,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """Get a specific session with full message history"""
    session = pipeline.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if not pipeline.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": f"Session '{session_id}' deleted"}


@router.post("/sessions/{session_id}/tags")
async def add_session_tag(session_id: str, tag: str):
    """Add a tag to a session"""
    session = pipeline.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if tag not in session.tags:
        session.tags.append(tag)
    return {"tags": session.tags}


# ============ Voice Endpoints ============

@router.post("/voice/generate")
async def generate_voice(text: str, speaker_id: int = 0):
    """
    Generate voice audio from text using CSM model.

    This integrates with the existing CSM speech model.
    """
    try:
        # Import CSM generator
        import sys
        sys.path.insert(0, str(pipeline.personality_engine.personalities_dir.parent.parent.parent))

        from generator import load_csm_1b, Segment

        # Load model (would be cached in production)
        generator = load_csm_1b(device="cuda")

        # Generate audio
        segment = Segment(text=text, speaker=speaker_id, audio=None)
        audio = generator.generate(
            text=text,
            speaker=speaker_id,
            context=[],
            max_audio_length_ms=30000,
        )

        # Save to temp file
        import torchaudio
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            torchaudio.save(f.name, audio.unsqueeze(0).cpu(), generator.sample_rate)
            return FileResponse(
                f.name,
                media_type="audio/wav",
                filename="response.wav",
            )

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Voice generation requires CSM model dependencies"
        )
    except Exception as e:
        logger.error(f"Voice generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Settings Endpoints ============

@router.get("/settings/sources")
async def get_source_settings():
    """Get available data sources and their settings"""
    return {
        "available_sources": [
            {"id": "web", "name": "Web Search", "enabled": True},
            {"id": "academic", "name": "Academic Papers", "enabled": True},
            {"id": "news", "name": "News Articles", "enabled": True},
            {"id": "youtube", "name": "YouTube Transcripts", "enabled": False},
            {"id": "local", "name": "Local Documents", "enabled": False},
        ],
        "source_weights": {
            "academic": 1.0,
            "news": 0.8,
            "web": 0.7,
            "blogs": 0.5,
        },
    }


@router.put("/settings/sources")
async def update_source_settings(settings: dict):
    """Update data source settings"""
    # In production, persist to database
    return {"message": "Source settings updated", "settings": settings}


# ============ Health & Info Endpoints ============

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@router.get("/info")
async def get_info():
    """Get API information"""
    return {
        "name": "Companion Researcher API",
        "version": "1.0.0",
        "description": "AI-powered research companion with configurable personalities",
        "features": [
            "Natural conversation with personality profiles",
            "Automated research and synthesis",
            "Multiple output depths (tweet to deep-dive)",
            "Session memory and context",
            "Voice output via CSM",
        ],
    }
