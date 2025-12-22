"""
Jarvis AI Assistant - Main FastAPI Application
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings, Settings
from services.voice_service import VoiceService
from services.transcription_service import TranscriptionService
from services.conversation_service import ConversationService
from agents.jarvis_agent import JarvisAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instances
voice_service: Optional[VoiceService] = None
transcription_service: Optional[TranscriptionService] = None
conversation_service: Optional[ConversationService] = None
jarvis_agent: Optional[JarvisAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - loads models on startup."""
    global voice_service, transcription_service, conversation_service, jarvis_agent

    settings = get_settings()
    logger.info("Starting Jarvis AI Assistant...")

    # Initialize services
    logger.info("Loading transcription service (Whisper)...")
    transcription_service = TranscriptionService(settings)

    logger.info("Loading voice service (CSM)...")
    voice_service = VoiceService(settings)

    logger.info("Initializing conversation service...")
    conversation_service = ConversationService(settings)

    logger.info("Initializing Jarvis agent...")
    jarvis_agent = JarvisAgent(settings)

    logger.info("All services loaded successfully!")

    yield

    # Cleanup
    logger.info("Shutting down Jarvis...")


# Create FastAPI app
app = FastAPI(
    title="Jarvis AI Assistant API",
    description="Voice-enabled AI personal assistant with task execution capabilities",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Pydantic Models ==============

class TextRequest(BaseModel):
    """Text message request."""
    text: str
    user_id: str
    conversation_id: Optional[str] = None


class VoiceResponse(BaseModel):
    """Response containing text and audio URL."""
    text: str
    audio_base64: str
    conversation_id: str
    tools_used: list[str] = []


class TranscriptionResponse(BaseModel):
    """Speech-to-text response."""
    text: str
    confidence: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    services: dict[str, bool]


# ============== API Endpoints ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check the health of all services."""
    return HealthResponse(
        status="healthy",
        services={
            "voice_service": voice_service is not None,
            "transcription_service": transcription_service is not None,
            "conversation_service": conversation_service is not None,
            "jarvis_agent": jarvis_agent is not None,
        }
    )


@app.post("/api/v1/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
):
    """
    Transcribe audio to text using Whisper.
    Supports: wav, mp3, m4a, webm, ogg
    """
    if transcription_service is None:
        raise HTTPException(status_code=503, detail="Transcription service not ready")

    try:
        audio_bytes = await audio.read()
        result = await transcription_service.transcribe(audio_bytes)
        return TranscriptionResponse(text=result["text"], confidence=result["confidence"])
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/synthesize")
async def synthesize_speech(
    text: str = Form(..., description="Text to synthesize"),
):
    """
    Synthesize text to speech using CSM.
    Returns audio as a streaming response.
    """
    if voice_service is None:
        raise HTTPException(status_code=503, detail="Voice service not ready")

    try:
        audio_bytes = await voice_service.synthesize(text)
        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=response.wav"}
        )
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat/voice", response_model=VoiceResponse)
async def voice_chat(
    audio: UploadFile = File(..., description="Voice message audio"),
    user_id: str = Form(..., description="User identifier"),
    conversation_id: Optional[str] = Form(None, description="Conversation ID for context"),
):
    """
    Complete voice chat pipeline:
    1. Transcribe user audio (Whisper)
    2. Process with AI agent (Claude)
    3. Generate voice response (CSM)
    """
    if not all([transcription_service, jarvis_agent, voice_service, conversation_service]):
        raise HTTPException(status_code=503, detail="Services not ready")

    try:
        # 1. Transcribe audio
        audio_bytes = await audio.read()
        transcription = await transcription_service.transcribe(audio_bytes)
        user_text = transcription["text"]
        logger.info(f"User said: {user_text}")

        # 2. Get or create conversation
        conv_id = conversation_id or await conversation_service.create_conversation(user_id)
        history = await conversation_service.get_history(conv_id)

        # 3. Process with Jarvis agent
        agent_response = await jarvis_agent.process(user_text, history)
        response_text = agent_response["text"]
        tools_used = agent_response.get("tools_used", [])
        logger.info(f"Jarvis response: {response_text}")

        # 4. Update conversation history
        await conversation_service.add_message(conv_id, "user", user_text)
        await conversation_service.add_message(conv_id, "assistant", response_text)

        # 5. Synthesize voice response
        audio_response = await voice_service.synthesize(response_text)
        import base64
        audio_base64 = base64.b64encode(audio_response).decode("utf-8")

        return VoiceResponse(
            text=response_text,
            audio_base64=audio_base64,
            conversation_id=conv_id,
            tools_used=tools_used,
        )

    except Exception as e:
        logger.error(f"Voice chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat/text", response_model=VoiceResponse)
async def text_chat(request: TextRequest):
    """
    Text chat with optional voice response.
    """
    if not all([jarvis_agent, voice_service, conversation_service]):
        raise HTTPException(status_code=503, detail="Services not ready")

    try:
        # Get or create conversation
        conv_id = request.conversation_id or await conversation_service.create_conversation(request.user_id)
        history = await conversation_service.get_history(conv_id)

        # Process with Jarvis agent
        agent_response = await jarvis_agent.process(request.text, history)
        response_text = agent_response["text"]
        tools_used = agent_response.get("tools_used", [])

        # Update conversation history
        await conversation_service.add_message(conv_id, "user", request.text)
        await conversation_service.add_message(conv_id, "assistant", response_text)

        # Synthesize voice response
        audio_response = await voice_service.synthesize(response_text)
        import base64
        audio_base64 = base64.b64encode(audio_response).decode("utf-8")

        return VoiceResponse(
            text=response_text,
            audio_base64=audio_base64,
            conversation_id=conv_id,
            tools_used=tools_used,
        )

    except Exception as e:
        logger.error(f"Text chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== WebSocket for Streaming ==============

@app.websocket("/ws/chat/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time voice chat.
    Enables streaming responses for lower latency.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: {user_id}")

    conv_id = await conversation_service.create_conversation(user_id)

    try:
        while True:
            # Receive audio data
            data = await websocket.receive_bytes()

            # Transcribe
            transcription = await transcription_service.transcribe(data)
            user_text = transcription["text"]

            # Send transcription back
            await websocket.send_json({
                "type": "transcription",
                "text": user_text
            })

            # Get conversation history
            history = await conversation_service.get_history(conv_id)

            # Process with agent (stream tokens)
            response_text = ""
            async for chunk in jarvis_agent.process_stream(user_text, history):
                response_text += chunk
                await websocket.send_json({
                    "type": "text_chunk",
                    "text": chunk
                })

            # Update history
            await conversation_service.add_message(conv_id, "user", user_text)
            await conversation_service.add_message(conv_id, "assistant", response_text)

            # Generate and send audio
            audio_bytes = await voice_service.synthesize(response_text)
            await websocket.send_bytes(audio_bytes)

            await websocket.send_json({
                "type": "complete"
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason=str(e))


# ============== Run Server ==============

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
