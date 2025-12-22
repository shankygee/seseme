"""
Voice Service - CSM Text-to-Speech Integration

This service wraps the Sesame CSM model for generating natural,
conversational speech for the Jarvis assistant.
"""
import io
import asyncio
import logging
from typing import Optional
from pathlib import Path

import torch
import torchaudio

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Voice synthesis service using Sesame CSM.

    Features:
    - Consistent assistant voice across conversations
    - Context-aware speech generation
    - Audio watermarking for transparency
    """

    def __init__(self, settings):
        self.settings = settings
        self.device = settings.device
        self.sample_rate = settings.sample_rate
        self.max_audio_length_ms = settings.csm_max_audio_length_ms

        # Lazy load to avoid blocking startup
        self._generator = None
        self._assistant_voice_context = None

        # Initialize synchronously during startup
        self._initialize()

    def _initialize(self):
        """Load CSM model and assistant voice."""
        try:
            # Import CSM from parent directory
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
            from generator import load_csm_1b, Segment
            self.Segment = Segment

            logger.info(f"Loading CSM model on {self.device}...")
            self._generator = load_csm_1b(device=self.device)
            logger.info("CSM model loaded successfully")

            # Load or create assistant voice context
            self._setup_assistant_voice()

        except Exception as e:
            logger.error(f"Failed to initialize voice service: {e}")
            # Continue without voice service - will error on use
            self._generator = None

    def _setup_assistant_voice(self):
        """
        Set up a consistent voice for the assistant.
        Uses a reference audio clip to define voice characteristics.
        """
        voice_sample_path = Path(__file__).parent / "jarvis_voice.wav"

        if voice_sample_path.exists():
            # Load existing voice sample
            audio, sr = torchaudio.load(str(voice_sample_path))
            if sr != self.sample_rate:
                audio = torchaudio.functional.resample(audio, sr, self.sample_rate)

            self._assistant_voice_context = [
                self.Segment(
                    speaker=0,
                    text="Hello, I'm Jarvis, your personal AI assistant. How can I help you today?",
                    audio=audio.squeeze()
                )
            ]
            logger.info("Loaded custom assistant voice")
        else:
            # Use default voice (will be generated fresh each time)
            self._assistant_voice_context = []
            logger.info("Using default CSM voice (no custom voice sample found)")

    async def synthesize(
        self,
        text: str,
        context: Optional[list] = None,
        speaker_id: int = 0,
    ) -> bytes:
        """
        Synthesize speech from text.

        Args:
            text: Text to convert to speech
            context: Optional conversation context for voice consistency
            speaker_id: Speaker identifier (default 0 for assistant)

        Returns:
            WAV audio bytes
        """
        if self._generator is None:
            raise RuntimeError("Voice service not initialized")

        # Run synthesis in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        audio_bytes = await loop.run_in_executor(
            None,
            self._synthesize_sync,
            text,
            context,
            speaker_id,
        )
        return audio_bytes

    def _synthesize_sync(
        self,
        text: str,
        context: Optional[list],
        speaker_id: int,
    ) -> bytes:
        """Synchronous synthesis implementation."""
        # Use assistant voice context if no custom context provided
        ctx = context if context is not None else self._assistant_voice_context

        # Generate audio
        with torch.inference_mode():
            audio = self._generator.generate(
                text=text,
                speaker=speaker_id,
                context=ctx,
                max_audio_length_ms=self.max_audio_length_ms,
            )

        # Convert to WAV bytes
        audio_bytes = self._audio_to_wav_bytes(audio)
        return audio_bytes

    def _audio_to_wav_bytes(self, audio: torch.Tensor) -> bytes:
        """Convert audio tensor to WAV bytes."""
        # Ensure audio is 2D [channels, samples]
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)

        # Move to CPU if needed
        audio = audio.cpu()

        # Write to bytes buffer
        buffer = io.BytesIO()
        torchaudio.save(
            buffer,
            audio,
            self.sample_rate,
            format="wav",
        )
        buffer.seek(0)
        return buffer.read()

    async def synthesize_streaming(
        self,
        text: str,
        chunk_size_chars: int = 100,
    ):
        """
        Stream audio synthesis for lower latency.

        Splits text into chunks and generates audio progressively.
        Yields audio chunks as they're generated.
        """
        if self._generator is None:
            raise RuntimeError("Voice service not initialized")

        # Split text into sentences or chunks
        chunks = self._split_text(text, chunk_size_chars)

        for chunk in chunks:
            if chunk.strip():
                audio_bytes = await self.synthesize(chunk)
                yield audio_bytes

    def _split_text(self, text: str, max_chars: int) -> list[str]:
        """Split text into speakable chunks at sentence boundaries."""
        import re

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def set_voice(self, audio_path: str, reference_text: str):
        """
        Set a custom voice for the assistant.

        Args:
            audio_path: Path to reference audio file
            reference_text: Transcription of the reference audio
        """
        audio, sr = torchaudio.load(audio_path)
        if sr != self.sample_rate:
            audio = torchaudio.functional.resample(audio, sr, self.sample_rate)

        self._assistant_voice_context = [
            self.Segment(
                speaker=0,
                text=reference_text,
                audio=audio.squeeze()
            )
        ]
        logger.info(f"Updated assistant voice from {audio_path}")

    @property
    def is_ready(self) -> bool:
        """Check if the voice service is ready."""
        return self._generator is not None
