"""
Sesame CSM TTS Server

A FastAPI server that provides real-time text-to-speech using the Sesame CSM model.
This server is designed to work with the Live Agent Screen Companion desktop app.
"""

import asyncio
import base64
import io
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional, List

import torch
import torchaudio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path to import CSM modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator import load_csm_1b, Segment

# Global generator instance
generator = None


class GenerateRequest(BaseModel):
    """Request body for text-to-speech generation."""
    text: str
    speaker_id: int = 0
    max_audio_length_ms: float = 30000
    temperature: float = 0.9
    topk: int = 50


class GenerateResponse(BaseModel):
    """Response body containing generated audio."""
    audio: str  # Base64 encoded WAV
    sample_rate: int
    duration_ms: float


class ConversationTurn(BaseModel):
    """A single turn in a conversation for context."""
    speaker_id: int
    text: str
    audio_base64: Optional[str] = None  # Optional audio for context


class ConversationalGenerateRequest(BaseModel):
    """Request body for conversational generation with context."""
    text: str
    speaker_id: int = 0
    context: List[ConversationTurn] = []
    max_audio_length_ms: float = 30000
    temperature: float = 0.9
    topk: int = 50


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    device: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the CSM model on startup."""
    global generator

    print("Loading Sesame CSM model...")

    # Determine device
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    print(f"Using device: {device}")

    try:
        generator = load_csm_1b(device=device)
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Failed to load model: {e}")
        print("The server will start but generation will fail.")

    yield

    # Cleanup
    generator = None
    print("Server shutting down.")


app = FastAPI(
    title="Sesame CSM TTS Server",
    description="Real-time text-to-speech using Sesame CSM",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for desktop app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check server health and model status."""
    device = "unknown"
    if generator is not None:
        device = str(next(generator._model.parameters()).device)

    return HealthResponse(
        status="healthy",
        model_loaded=generator is not None,
        device=device,
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate_speech(request: GenerateRequest):
    """
    Generate speech from text.

    Args:
        request: The generation request containing text and parameters.

    Returns:
        GenerateResponse with base64-encoded WAV audio.
    """
    if generator is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        # Run generation in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,
            lambda: generator.generate(
                text=request.text,
                speaker=request.speaker_id,
                context=[],
                max_audio_length_ms=request.max_audio_length_ms,
                temperature=request.temperature,
                topk=request.topk,
            )
        )

        # Convert to WAV bytes
        audio_bytes = audio_tensor_to_wav_bytes(audio, generator.sample_rate)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        # Calculate duration
        duration_ms = (len(audio) / generator.sample_rate) * 1000

        return GenerateResponse(
            audio=audio_base64,
            sample_rate=generator.sample_rate,
            duration_ms=duration_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/generate/conversational", response_model=GenerateResponse)
async def generate_conversational_speech(request: ConversationalGenerateRequest):
    """
    Generate speech with conversational context.

    This endpoint allows you to provide previous conversation turns
    to generate more contextually appropriate speech.

    Args:
        request: The generation request with text, speaker, and context.

    Returns:
        GenerateResponse with base64-encoded WAV audio.
    """
    if generator is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        # Build context segments
        context_segments = []
        for turn in request.context:
            if turn.audio_base64:
                # Decode audio from base64
                audio_bytes = base64.b64decode(turn.audio_base64)
                audio_tensor = wav_bytes_to_audio_tensor(audio_bytes, generator.sample_rate)
            else:
                # No audio provided - skip this context turn
                continue

            context_segments.append(Segment(
                speaker=turn.speaker_id,
                text=turn.text,
                audio=audio_tensor,
            ))

        # Run generation
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,
            lambda: generator.generate(
                text=request.text,
                speaker=request.speaker_id,
                context=context_segments,
                max_audio_length_ms=request.max_audio_length_ms,
                temperature=request.temperature,
                topk=request.topk,
            )
        )

        # Convert to WAV bytes
        audio_bytes = audio_tensor_to_wav_bytes(audio, generator.sample_rate)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        duration_ms = (len(audio) / generator.sample_rate) * 1000

        return GenerateResponse(
            audio=audio_base64,
            sample_rate=generator.sample_rate,
            duration_ms=duration_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


def audio_tensor_to_wav_bytes(audio: torch.Tensor, sample_rate: int) -> bytes:
    """Convert an audio tensor to WAV bytes."""
    # Ensure audio is on CPU and has correct shape
    if audio.device.type != "cpu":
        audio = audio.cpu()

    # Add channel dimension if needed
    if audio.dim() == 1:
        audio = audio.unsqueeze(0)

    # Create buffer
    buffer = io.BytesIO()
    torchaudio.save(buffer, audio, sample_rate, format="wav")
    buffer.seek(0)

    return buffer.read()


def wav_bytes_to_audio_tensor(wav_bytes: bytes, target_sample_rate: int) -> torch.Tensor:
    """Convert WAV bytes to an audio tensor."""
    buffer = io.BytesIO(wav_bytes)
    audio, sample_rate = torchaudio.load(buffer)

    # Convert to mono if stereo
    if audio.shape[0] > 1:
        audio = audio.mean(dim=0, keepdim=True)

    # Resample if needed
    if sample_rate != target_sample_rate:
        resampler = torchaudio.transforms.Resample(sample_rate, target_sample_rate)
        audio = resampler(audio)

    # Remove channel dimension
    audio = audio.squeeze(0)

    return audio


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"Starting CSM TTS server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
