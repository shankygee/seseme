"""
Voice Engine - Integration with CSM speech synthesis model
"""
import logging
from pathlib import Path
from typing import Optional, List
import tempfile
import asyncio

logger = logging.getLogger(__name__)


class VoiceEngine:
    """
    Integrates with the CSM (Conversational Speech Model) for voice output.

    This provides text-to-speech capabilities using the existing CSM model
    from the parent project.
    """

    def __init__(
        self,
        device: str = "cuda",
        sample_rate: int = 24000,
        csm_path: Optional[Path] = None,
    ):
        self.device = device
        self.sample_rate = sample_rate
        self.csm_path = csm_path or Path(__file__).parent.parent.parent.parent

        self._generator = None
        self._loaded = False

    def _ensure_loaded(self):
        """Lazily load the CSM model"""
        if self._loaded:
            return

        try:
            import sys
            sys.path.insert(0, str(self.csm_path))

            from generator import load_csm_1b
            self._generator = load_csm_1b(device=self.device)
            self._loaded = True
            logger.info("CSM model loaded successfully")

        except ImportError as e:
            logger.warning(f"CSM model dependencies not available: {e}")
            raise RuntimeError(
                "CSM model not available. Install requirements from parent project."
            )
        except Exception as e:
            logger.error(f"Failed to load CSM model: {e}")
            raise

    async def generate_speech(
        self,
        text: str,
        speaker_id: int = 0,
        context: Optional[List] = None,
        max_length_ms: int = 30000,
    ) -> bytes:
        """
        Generate speech audio from text.

        Args:
            text: The text to synthesize
            speaker_id: Speaker voice to use (0-N)
            context: Optional conversation context for better synthesis
            max_length_ms: Maximum audio length in milliseconds

        Returns:
            WAV audio bytes
        """
        # Run in thread pool to avoid blocking
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._generate_speech_sync,
            text,
            speaker_id,
            context,
            max_length_ms,
        )

    def _generate_speech_sync(
        self,
        text: str,
        speaker_id: int,
        context: Optional[List],
        max_length_ms: int,
    ) -> bytes:
        """Synchronous speech generation"""
        self._ensure_loaded()

        import torch
        import torchaudio
        import io

        # Generate audio
        audio = self._generator.generate(
            text=text,
            speaker=speaker_id,
            context=context or [],
            max_audio_length_ms=max_length_ms,
        )

        # Convert to bytes
        buffer = io.BytesIO()
        torchaudio.save(
            buffer,
            audio.unsqueeze(0).cpu(),
            self.sample_rate,
            format="wav",
        )
        buffer.seek(0)

        return buffer.read()

    async def generate_speech_file(
        self,
        text: str,
        output_path: Path,
        speaker_id: int = 0,
        context: Optional[List] = None,
        max_length_ms: int = 30000,
    ) -> Path:
        """
        Generate speech and save to file.

        Args:
            text: Text to synthesize
            output_path: Where to save the audio file
            speaker_id: Speaker voice
            context: Conversation context
            max_length_ms: Maximum length

        Returns:
            Path to the generated audio file
        """
        audio_bytes = await self.generate_speech(
            text=text,
            speaker_id=speaker_id,
            context=context,
            max_length_ms=max_length_ms,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        return output_path

    def get_temp_audio_path(self) -> Path:
        """Get a temporary path for audio output"""
        return Path(tempfile.mktemp(suffix=".wav"))

    @property
    def is_available(self) -> bool:
        """Check if voice synthesis is available"""
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False


class ConversationVoiceContext:
    """
    Manages conversation context for more natural speech synthesis.

    The CSM model can use previous audio segments as context to maintain
    consistent speaker characteristics and conversation flow.
    """

    def __init__(self, max_segments: int = 5):
        self.max_segments = max_segments
        self._segments = []

    def add_segment(self, text: str, speaker_id: int, audio_tensor):
        """Add a segment to the context"""
        from dataclasses import dataclass

        @dataclass
        class Segment:
            text: str
            speaker: int
            audio: any

        segment = Segment(text=text, speaker=speaker_id, audio=audio_tensor)
        self._segments.append(segment)

        # Keep only recent segments
        if len(self._segments) > self.max_segments:
            self._segments = self._segments[-self.max_segments:]

    def get_context(self) -> List:
        """Get context segments for synthesis"""
        return self._segments.copy()

    def clear(self):
        """Clear the context"""
        self._segments = []
