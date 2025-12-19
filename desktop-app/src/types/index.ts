// Permission states
export type PermissionState = 'Granted' | 'Denied' | 'NotDetermined' | 'Restricted';

export interface PermissionStatus {
  screen_capture: PermissionState;
  accessibility: PermissionState;
  microphone: PermissionState;
}

// Display info
export interface DisplayInfo {
  id: number;
  name: string;
  width: number;
  height: number;
  is_primary: boolean;
}

// Screen capture
export interface CaptureFrame {
  data: string;  // Base64 encoded image
  width: number;
  height: number;
  timestamp: number;
  cursor_x: number;
  cursor_y: number;
  active_window: string | null;
}

export interface CaptureConfig {
  display_id: number;
  frame_rate: number;
  scale: number;
  quality: number;
}

// Agent messages
export interface UserMessage {
  text?: string;
  audio_base64?: string;
  screen_frame?: string;
  cursor_position?: [number, number];
  active_window?: string;
}

export type AgentAction =
  | { type: 'Speak'; text: string }
  | { type: 'MoveMouse'; x: number; y: number }
  | { type: 'Click'; button: string; double: boolean }
  | { type: 'Scroll'; direction: string; amount: number }
  | { type: 'Type'; text: string }
  | { type: 'PressKey'; key: string; modifiers: string[] }
  | { type: 'RequestControl' }
  | { type: 'ReleaseControl' }
  | { type: 'Wait'; ms: number };

export interface AgentResponse {
  thoughts: string;
  speech: string | null;
  actions: AgentAction[];
  needs_permission: boolean;
}

export interface AgentStatusResponse {
  status: string;
  has_control: boolean;
  is_speaking: boolean;
  can_be_interrupted: boolean;
}

// API config
export type SttProvider = 'Whisper' | 'Groq' | 'Deepgram';
export type LlmProvider = 'Anthropic' | 'OpenAI';

export interface ApiConfig {
  openai_api_key?: string;
  anthropic_api_key?: string;
  groq_api_key?: string;
  csm_server_url?: string;
  stt_provider: SttProvider;
  llm_provider: LlmProvider;
}

// Mouse/keyboard types
export type MouseButton = 'Left' | 'Right' | 'Middle';
export type ScrollDirection = 'Up' | 'Down' | 'Left' | 'Right';

export interface KeyModifiers {
  shift: boolean;
  control: boolean;
  alt: boolean;
  command: boolean;
}

// App state
export type AppStatus =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'acting'
  | 'error';

export interface ConversationTurn {
  role: 'user' | 'agent';
  text: string;
  timestamp: number;
}
