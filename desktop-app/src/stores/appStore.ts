import { create } from 'zustand';
import type {
  ApiConfig,
  AppStatus,
  ConversationTurn,
  PermissionStatus,
  CaptureFrame,
} from '../types';

interface AppState {
  // Status
  status: AppStatus;
  setStatus: (status: AppStatus) => void;

  // Permissions
  permissions: PermissionStatus | null;
  setPermissions: (permissions: PermissionStatus) => void;

  // Screen capture
  isCapturing: boolean;
  setIsCapturing: (capturing: boolean) => void;
  latestFrame: CaptureFrame | null;
  setLatestFrame: (frame: CaptureFrame | null) => void;

  // Audio
  isRecording: boolean;
  setIsRecording: (recording: boolean) => void;
  isSpeaking: boolean;
  setIsSpeaking: (speaking: boolean) => void;
  volume: number;
  setVolume: (volume: number) => void;

  // Agent control
  agentHasControl: boolean;
  setAgentHasControl: (hasControl: boolean) => void;

  // Conversation
  conversation: ConversationTurn[];
  addTurn: (turn: Omit<ConversationTurn, 'timestamp'>) => void;
  clearConversation: () => void;

  // API config
  apiConfig: ApiConfig;
  setApiConfig: (config: Partial<ApiConfig>) => void;

  // Settings UI
  showSettings: boolean;
  setShowSettings: (show: boolean) => void;

  // Error handling
  error: string | null;
  setError: (error: string | null) => void;
}

const defaultApiConfig: ApiConfig = {
  stt_provider: 'Whisper',
  llm_provider: 'Anthropic',
};

export const useAppStore = create<AppState>((set) => ({
  // Status
  status: 'idle',
  setStatus: (status) => set({ status }),

  // Permissions
  permissions: null,
  setPermissions: (permissions) => set({ permissions }),

  // Screen capture
  isCapturing: false,
  setIsCapturing: (isCapturing) => set({ isCapturing }),
  latestFrame: null,
  setLatestFrame: (latestFrame) => set({ latestFrame }),

  // Audio
  isRecording: false,
  setIsRecording: (isRecording) => set({ isRecording }),
  isSpeaking: false,
  setIsSpeaking: (isSpeaking) => set({ isSpeaking }),
  volume: 1.0,
  setVolume: (volume) => set({ volume }),

  // Agent control
  agentHasControl: false,
  setAgentHasControl: (agentHasControl) => set({ agentHasControl }),

  // Conversation
  conversation: [],
  addTurn: (turn) =>
    set((state) => ({
      conversation: [
        ...state.conversation,
        { ...turn, timestamp: Date.now() },
      ],
    })),
  clearConversation: () => set({ conversation: [] }),

  // API config
  apiConfig: defaultApiConfig,
  setApiConfig: (config) =>
    set((state) => ({
      apiConfig: { ...state.apiConfig, ...config },
    })),

  // Settings UI
  showSettings: false,
  setShowSettings: (showSettings) => set({ showSettings }),

  // Error handling
  error: null,
  setError: (error) => set({ error }),
}));
