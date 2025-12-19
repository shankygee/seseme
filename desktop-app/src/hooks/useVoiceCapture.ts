import { useCallback, useRef, useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';

interface VoiceCaptureOptions {
  silenceThreshold?: number;
  silenceDuration?: number;
  maxRecordingDuration?: number;
  onSpeechStart?: () => void;
  onSpeechEnd?: (audioBlob: Blob) => void;
  onTranscription?: (text: string) => void;
}

export function useVoiceCapture(options: VoiceCaptureOptions = {}) {
  const {
    silenceThreshold = 0.01,
    silenceDuration = 1500,
    maxRecordingDuration = 30000,
    onSpeechStart,
    onSpeechEnd,
    onTranscription,
  } = options;

  const { isRecording, setIsRecording, apiConfig, setError } = useAppStore();

  const [audioLevel, setAudioLevel] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (recordingTimerRef.current) {
      clearTimeout(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    chunksRef.current = [];
  }, []);

  // Analyze audio levels
  const analyzeAudio = useCallback(() => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate average volume
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
    const normalizedLevel = average / 255;
    setAudioLevel(normalizedLevel);

    // Detect speech
    const speaking = normalizedLevel > silenceThreshold;

    if (speaking !== isSpeaking) {
      setIsSpeaking(speaking);

      if (speaking) {
        // Speech started
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        onSpeechStart?.();
      } else {
        // Silence detected - start timer
        if (!silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => {
            // Silence persisted, end recording
            if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
              mediaRecorderRef.current.stop();
            }
          }, silenceDuration);
        }
      }
    }

    animationFrameRef.current = requestAnimationFrame(analyzeAudio);
  }, [isSpeaking, silenceThreshold, silenceDuration, onSpeechStart]);

  // Start recording
  const startRecording = useCallback(async () => {
    try {
      cleanup();

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 24000, // Match CSM sample rate
        },
      });
      streamRef.current = stream;

      // Set up audio analysis
      audioContextRef.current = new AudioContext();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      source.connect(analyserRef.current);

      // Set up media recorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        chunksRef.current = [];

        if (blob.size > 0) {
          onSpeechEnd?.(blob);

          // Transcribe the audio
          if (onTranscription) {
            await transcribeAudio(blob);
          }
        }

        cleanup();
        setIsRecording(false);
      };

      // Start recording
      mediaRecorderRef.current.start(100);
      setIsRecording(true);

      // Start audio analysis
      analyzeAudio();

      // Set max recording duration
      recordingTimerRef.current = setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop();
        }
      }, maxRecordingDuration);
    } catch (e) {
      setError(`Microphone access denied: ${e}`);
      cleanup();
    }
  }, [cleanup, analyzeAudio, maxRecordingDuration, onSpeechEnd, onTranscription, setIsRecording, setError]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }, [setIsRecording]);

  // Transcribe audio using the configured STT provider
  const transcribeAudio = useCallback(async (blob: Blob) => {
    try {
      const arrayBuffer = await blob.arrayBuffer();
      const base64 = btoa(
        new Uint8Array(arrayBuffer).reduce(
          (data, byte) => data + String.fromCharCode(byte),
          ''
        )
      );

      // Use Whisper API (either OpenAI or Groq)
      let apiUrl: string;
      let apiKey: string | undefined;

      switch (apiConfig.stt_provider) {
        case 'Groq':
          apiUrl = 'https://api.groq.com/openai/v1/audio/transcriptions';
          apiKey = apiConfig.groq_api_key;
          break;
        case 'Whisper':
        default:
          apiUrl = 'https://api.openai.com/v1/audio/transcriptions';
          apiKey = apiConfig.openai_api_key;
          break;
      }

      if (!apiKey) {
        throw new Error('API key not configured for STT');
      }

      const formData = new FormData();
      formData.append('file', blob, 'audio.webm');
      formData.append('model', 'whisper-1');
      formData.append('response_format', 'json');

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`STT request failed: ${response.statusText}`);
      }

      const result = await response.json();
      const transcription = result.text?.trim();

      if (transcription) {
        onTranscription?.(transcription);
      }
    } catch (e) {
      setError(`Transcription failed: ${e}`);
    }
  }, [apiConfig, onTranscription, setError]);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    isRecording,
    audioLevel,
    isSpeaking,
    startRecording,
    stopRecording,
  };
}
