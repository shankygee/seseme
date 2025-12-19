use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicBool, Ordering};

/// API configuration for different services
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ApiConfig {
    pub openai_api_key: Option<String>,
    pub anthropic_api_key: Option<String>,
    pub groq_api_key: Option<String>,
    pub csm_server_url: Option<String>,  // For hosted CSM TTS
    pub stt_provider: SttProvider,
    pub llm_provider: LlmProvider,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub enum SttProvider {
    #[default]
    Whisper,  // OpenAI Whisper
    Groq,     // Groq's fast Whisper
    Deepgram,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub enum LlmProvider {
    #[default]
    Anthropic,  // Claude
    OpenAI,     // GPT-4
}

/// Agent status
#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub enum AgentStatus {
    #[default]
    Idle,
    Listening,
    Thinking,
    Speaking,
    Acting,
    Interrupted,
}

/// Safety state - tracks whether agent is allowed to control inputs
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SafetyState {
    pub control_allowed: bool,
    pub last_user_activity: i64,  // Unix timestamp
    pub control_timeout_ms: u64,
}

impl Default for SafetyState {
    fn default() -> Self {
        Self {
            control_allowed: false,
            last_user_activity: 0,
            control_timeout_ms: 100,  // Release control 100ms after user input
        }
    }
}

/// Screen capture state
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CaptureState {
    pub is_capturing: bool,
    pub display_id: u32,
    pub frame_rate: u32,
    pub last_frame_time: i64,
}

/// Audio state
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AudioState {
    pub is_recording: bool,
    pub is_playing: bool,
    pub volume: f32,
}

/// Main application state
pub struct AppState {
    pub api_config: RwLock<ApiConfig>,
    pub agent_status: RwLock<AgentStatus>,
    pub safety: RwLock<SafetyState>,
    pub capture: RwLock<CaptureState>,
    pub audio: RwLock<AudioState>,
    pub is_agent_controlling: AtomicBool,
    pub should_interrupt: AtomicBool,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            api_config: RwLock::new(ApiConfig::default()),
            agent_status: RwLock::new(AgentStatus::default()),
            safety: RwLock::new(SafetyState::default()),
            capture: RwLock::new(CaptureState::default()),
            audio: RwLock::new(AudioState { volume: 1.0, ..Default::default() }),
            is_agent_controlling: AtomicBool::new(false),
            should_interrupt: AtomicBool::new(false),
        }
    }

    /// Check if the agent should release control
    pub fn should_release_control(&self) -> bool {
        let safety = self.safety.read();
        if !safety.control_allowed {
            return true;
        }

        let now = chrono::Utc::now().timestamp_millis();
        let elapsed = (now - safety.last_user_activity) as u64;
        elapsed < safety.control_timeout_ms
    }

    /// Record user activity (mouse move, key press, etc.)
    pub fn record_user_activity(&self) {
        let mut safety = self.safety.write();
        safety.last_user_activity = chrono::Utc::now().timestamp_millis();

        // Immediately release agent control on user activity
        self.is_agent_controlling.store(false, Ordering::SeqCst);
    }

    /// Grant control to agent
    pub fn grant_control(&self) {
        let mut safety = self.safety.write();
        safety.control_allowed = true;
        self.is_agent_controlling.store(true, Ordering::SeqCst);
    }

    /// Revoke control from agent
    pub fn revoke_control(&self) {
        let mut safety = self.safety.write();
        safety.control_allowed = false;
        self.is_agent_controlling.store(false, Ordering::SeqCst);
    }

    /// Check if agent is currently allowed to control
    pub fn can_control(&self) -> bool {
        self.is_agent_controlling.load(Ordering::SeqCst)
            && self.safety.read().control_allowed
    }

    /// Request interrupt
    pub fn request_interrupt(&self) {
        self.should_interrupt.store(true, Ordering::SeqCst);
        self.revoke_control();
    }

    /// Clear interrupt flag
    pub fn clear_interrupt(&self) -> bool {
        self.should_interrupt.swap(false, Ordering::SeqCst)
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}
