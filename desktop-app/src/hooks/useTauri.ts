import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { useCallback, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import type {
  PermissionStatus,
  DisplayInfo,
  CaptureFrame,
  CaptureConfig,
  UserMessage,
  AgentResponse,
  AgentStatusResponse,
  ApiConfig,
  MouseButton,
  ScrollDirection,
  KeyModifiers,
} from '../types';

// Permission hooks
export function usePermissions() {
  const { setPermissions, setError } = useAppStore();

  const checkPermissions = useCallback(async () => {
    try {
      const status = await invoke<PermissionStatus>('check_permissions');
      setPermissions(status);
      return status;
    } catch (e) {
      setError(`Failed to check permissions: ${e}`);
      return null;
    }
  }, [setPermissions, setError]);

  const requestPermission = useCallback(async (type: string) => {
    try {
      await invoke('request_permissions', { permissionType: type });
      // Re-check permissions after request
      setTimeout(checkPermissions, 1000);
    } catch (e) {
      setError(`Failed to request permission: ${e}`);
    }
  }, [checkPermissions, setError]);

  return { checkPermissions, requestPermission };
}

// Screen capture hooks
export function useScreenCapture() {
  const { setIsCapturing, setLatestFrame, setError } = useAppStore();

  const getDisplays = useCallback(async () => {
    try {
      return await invoke<DisplayInfo[]>('get_available_displays');
    } catch (e) {
      setError(`Failed to get displays: ${e}`);
      return [];
    }
  }, [setError]);

  const startCapture = useCallback(async (config?: Partial<CaptureConfig>) => {
    try {
      await invoke('start_screen_capture', { config });
      setIsCapturing(true);
    } catch (e) {
      setError(`Failed to start capture: ${e}`);
    }
  }, [setIsCapturing, setError]);

  const stopCapture = useCallback(async () => {
    try {
      await invoke('stop_screen_capture');
      setIsCapturing(false);
    } catch (e) {
      setError(`Failed to stop capture: ${e}`);
    }
  }, [setIsCapturing, setError]);

  const captureFrame = useCallback(async (scale?: number, quality?: number) => {
    try {
      const frame = await invoke<CaptureFrame>('capture_frame', { scale, quality });
      setLatestFrame(frame);
      return frame;
    } catch (e) {
      setError(`Failed to capture frame: ${e}`);
      return null;
    }
  }, [setLatestFrame, setError]);

  return { getDisplays, startCapture, stopCapture, captureFrame };
}

// Agent hooks
export function useAgent() {
  const {
    setStatus,
    setAgentHasControl,
    addTurn,
    setError,
    apiConfig,
    setApiConfig,
  } = useAppStore();

  const setApiConfiguration = useCallback(async (config: Partial<ApiConfig>) => {
    const newConfig = { ...apiConfig, ...config };
    try {
      await invoke('set_api_config', { config: newConfig });
      setApiConfig(config);
    } catch (e) {
      setError(`Failed to set API config: ${e}`);
    }
  }, [apiConfig, setApiConfig, setError]);

  const sendMessage = useCallback(async (message: UserMessage) => {
    try {
      setStatus('thinking');
      const response = await invoke<AgentResponse>('send_to_agent', { message });

      if (response.speech) {
        addTurn({ role: 'agent', text: response.speech });
      }

      return response;
    } catch (e) {
      setError(`Agent error: ${e}`);
      setStatus('error');
      return null;
    }
  }, [setStatus, addTurn, setError]);

  const interrupt = useCallback(async () => {
    try {
      await invoke('interrupt_agent');
      setStatus('idle');
      setAgentHasControl(false);
    } catch (e) {
      setError(`Failed to interrupt: ${e}`);
    }
  }, [setStatus, setAgentHasControl, setError]);

  const getStatus = useCallback(async () => {
    try {
      return await invoke<AgentStatusResponse>('get_agent_status');
    } catch (e) {
      setError(`Failed to get status: ${e}`);
      return null;
    }
  }, [setError]);

  return { sendMessage, interrupt, getStatus, setApiConfiguration };
}

// Input control hooks
export function useInputControl() {
  const { setAgentHasControl, setError } = useAppStore();

  const moveMouse = useCallback(async (x: number, y: number, smooth?: boolean) => {
    try {
      await invoke('move_mouse', { x, y, smooth });
    } catch (e) {
      setError(`Failed to move mouse: ${e}`);
    }
  }, [setError]);

  const clickMouse = useCallback(async (button: MouseButton, doubleClick?: boolean) => {
    try {
      await invoke('click_mouse', { button, doubleClick });
    } catch (e) {
      setError(`Failed to click: ${e}`);
    }
  }, [setError]);

  const scroll = useCallback(async (direction: ScrollDirection, amount?: number) => {
    try {
      await invoke('scroll', { direction, amount });
    } catch (e) {
      setError(`Failed to scroll: ${e}`);
    }
  }, [setError]);

  const typeText = useCallback(async (text: string, delayMs?: number) => {
    try {
      await invoke('type_text', { text, delayMs });
    } catch (e) {
      setError(`Failed to type: ${e}`);
    }
  }, [setError]);

  const pressKey = useCallback(async (key: string, modifiers?: Partial<KeyModifiers>) => {
    try {
      await invoke('press_key', { key, modifiers });
    } catch (e) {
      setError(`Failed to press key: ${e}`);
    }
  }, [setError]);

  const releaseControl = useCallback(async () => {
    try {
      await invoke('release_control');
      setAgentHasControl(false);
    } catch (e) {
      setError(`Failed to release control: ${e}`);
    }
  }, [setAgentHasControl, setError]);

  const checkControl = useCallback(async () => {
    try {
      const controlling = await invoke<boolean>('is_agent_controlling');
      setAgentHasControl(controlling);
      return controlling;
    } catch (e) {
      setError(`Failed to check control: ${e}`);
      return false;
    }
  }, [setAgentHasControl, setError]);

  return {
    moveMouse,
    clickMouse,
    scroll,
    typeText,
    pressKey,
    releaseControl,
    checkControl,
  };
}

// Audio hooks
export function useAudio() {
  const { setIsRecording, setIsSpeaking, setError } = useAppStore();

  const startRecording = useCallback(async () => {
    try {
      await invoke('start_audio_capture', { config: null });
      setIsRecording(true);
    } catch (e) {
      setError(`Failed to start recording: ${e}`);
    }
  }, [setIsRecording, setError]);

  const stopRecording = useCallback(async () => {
    try {
      await invoke('stop_audio_capture');
      setIsRecording(false);
    } catch (e) {
      setError(`Failed to stop recording: ${e}`);
    }
  }, [setIsRecording, setError]);

  const playAudio = useCallback(async (text: string, speakerId?: number) => {
    try {
      setIsSpeaking(true);
      await invoke('play_audio', { text, speakerId });
    } catch (e) {
      setError(`Failed to play audio: ${e}`);
    } finally {
      setIsSpeaking(false);
    }
  }, [setIsSpeaking, setError]);

  const stopAudio = useCallback(async () => {
    try {
      await invoke('stop_audio');
      setIsSpeaking(false);
    } catch (e) {
      setError(`Failed to stop audio: ${e}`);
    }
  }, [setIsSpeaking, setError]);

  return { startRecording, stopRecording, playAudio, stopAudio };
}

// Event listener hook
export function useTauriEvents() {
  const { setStatus, setIsSpeaking, setAgentHasControl } = useAppStore();

  useEffect(() => {
    const unlisteners: (() => void)[] = [];

    const setupListeners = async () => {
      // Agent status events
      unlisteners.push(
        await listen<string>('agent-status', (event) => {
          const status = event.payload as any;
          setStatus(status);
        })
      );

      // Audio events
      unlisteners.push(
        await listen<boolean>('audio-playing', (event) => {
          setIsSpeaking(event.payload);
        })
      );

      // TTS fallback (use browser speech synthesis)
      unlisteners.push(
        await listen<string>('tts-fallback', (event) => {
          const text = event.payload;
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.rate = 1.0;
          utterance.pitch = 1.0;
          speechSynthesis.speak(utterance);
        })
      );

      // Audio stop
      unlisteners.push(
        await listen<boolean>('audio-stop', () => {
          speechSynthesis.cancel();
          setIsSpeaking(false);
        })
      );
    };

    setupListeners();

    return () => {
      unlisteners.forEach((unlisten) => unlisten());
    };
  }, [setStatus, setIsSpeaking, setAgentHasControl]);
}
