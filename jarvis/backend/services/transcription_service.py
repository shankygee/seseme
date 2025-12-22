"""
Transcription Service - Speech-to-Text using Whisper

Supports both OpenAI Whisper and faster-whisper for improved performance.
"""
import io
import asyncio
import logging
import tempfile
from typing import Optional
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Speech-to-text service using Whisper.

    Features:
    - Support for multiple audio formats
    - Language detection
    - Confidence scores
    - Optional faster-whisper backend for speed
    """

    def __init__(self, settings):
        self.settings = settings
        self.model_name = settings.whisper_model
        self.device = settings.device
        self.use_faster_whisper = settings.use_faster_whisper

        self._model = None
        self._initialize()

    def _initialize(self):
        """Load Whisper model."""
        try:
            if self.use_faster_whisper:
                self._initialize_faster_whisper()
            else:
                self._initialize_openai_whisper()
        except Exception as e:
            logger.error(f"Failed to initialize transcription service: {e}")
            self._model = None

    def _initialize_faster_whisper(self):
        """Initialize faster-whisper backend."""
        try:
            from faster_whisper import WhisperModel

            compute_type = "float16" if self.device == "cuda" else "int8"
            logger.info(f"Loading faster-whisper model: {self.model_name} on {self.device}")

            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=compute_type,
            )
            self._backend = "faster_whisper"
            logger.info("faster-whisper loaded successfully")

        except ImportError:
            logger.warning("faster-whisper not available, falling back to OpenAI Whisper")
            self._initialize_openai_whisper()

    def _initialize_openai_whisper(self):
        """Initialize OpenAI Whisper backend."""
        import whisper

        logger.info(f"Loading OpenAI Whisper model: {self.model_name}")
        self._model = whisper.load_model(self.model_name, device=self.device)
        self._backend = "openai_whisper"
        logger.info("OpenAI Whisper loaded successfully")

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
    ) -> dict:
        """
        Transcribe audio to text.

        Args:
            audio_bytes: Audio file bytes (wav, mp3, m4a, webm, ogg)
            language: Optional language code (e.g., 'en', 'es')

        Returns:
            dict with 'text', 'language', 'confidence', 'segments'
        """
        if self._model is None:
            raise RuntimeError("Transcription service not initialized")

        # Run transcription in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._transcribe_sync,
            audio_bytes,
            language,
        )
        return result

    def _transcribe_sync(
        self,
        audio_bytes: bytes,
        language: Optional[str],
    ) -> dict:
        """Synchronous transcription implementation."""
        # Write audio to temp file (Whisper requires file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            if self._backend == "faster_whisper":
                return self._transcribe_faster_whisper(temp_path, language)
            else:
                return self._transcribe_openai_whisper(temp_path, language)
        finally:
            # Cleanup temp file
            Path(temp_path).unlink(missing_ok=True)

    def _transcribe_faster_whisper(
        self,
        audio_path: str,
        language: Optional[str],
    ) -> dict:
        """Transcribe using faster-whisper."""
        segments, info = self._model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # Filter out silence
        )

        # Collect all segments
        segments_list = []
        full_text = ""
        total_confidence = 0.0
        segment_count = 0

        for segment in segments:
            segments_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": segment.avg_logprob,
            })
            full_text += segment.text
            total_confidence += segment.avg_logprob
            segment_count += 1

        avg_confidence = total_confidence / max(segment_count, 1)
        # Convert log prob to 0-1 confidence score
        confidence = min(1.0, max(0.0, 1.0 + avg_confidence / 5.0))

        return {
            "text": full_text.strip(),
            "language": info.language,
            "confidence": confidence,
            "segments": segments_list,
            "duration": info.duration,
        }

    def _transcribe_openai_whisper(
        self,
        audio_path: str,
        language: Optional[str],
    ) -> dict:
        """Transcribe using OpenAI Whisper."""
        import whisper

        options = {}
        if language:
            options["language"] = language

        result = self._model.transcribe(audio_path, **options)

        # Calculate average confidence from segments
        segments_list = []
        total_confidence = 0.0

        for segment in result.get("segments", []):
            seg_confidence = segment.get("avg_logprob", -1.0)
            segments_list.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip(),
                "confidence": seg_confidence,
            })
            total_confidence += seg_confidence

        num_segments = len(segments_list)
        avg_confidence = total_confidence / max(num_segments, 1)
        confidence = min(1.0, max(0.0, 1.0 + avg_confidence / 5.0))

        return {
            "text": result["text"].strip(),
            "language": result.get("language", "en"),
            "confidence": confidence,
            "segments": segments_list,
            "duration": segments_list[-1]["end"] if segments_list else 0.0,
        }

    async def transcribe_streaming(
        self,
        audio_stream,
        chunk_duration_ms: int = 3000,
    ):
        """
        Stream transcription for real-time use.

        Yields partial transcriptions as audio comes in.
        """
        # Buffer for accumulating audio
        buffer = io.BytesIO()
        sample_rate = 16000  # Whisper expects 16kHz
        chunk_samples = int(sample_rate * chunk_duration_ms / 1000)

        async for audio_chunk in audio_stream:
            buffer.write(audio_chunk)

            # Check if we have enough audio to transcribe
            buffer.seek(0)
            audio_data = buffer.read()

            if len(audio_data) >= chunk_samples * 2:  # 16-bit audio
                result = await self.transcribe(audio_data)
                yield result

                # Keep last bit of audio for context
                buffer = io.BytesIO()
                buffer.write(audio_data[-chunk_samples:])

        # Final transcription
        buffer.seek(0)
        final_audio = buffer.read()
        if final_audio:
            result = await self.transcribe(final_audio)
            yield result

    @property
    def is_ready(self) -> bool:
        """Check if the transcription service is ready."""
        return self._model is not None
