use crate::state::AppState;
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::{Emitter, State, Window};

/// Audio capture configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioConfig {
    pub sample_rate: u32,
    pub channels: u16,
}

impl Default for AudioConfig {
    fn default() -> Self {
        Self {
            sample_rate: 24000,  // Match CSM's sample rate
            channels: 1,
        }
    }
}

/// STT request to transcribe audio
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranscriptionRequest {
    pub audio_base64: String,
    pub language: Option<String>,
}

/// STT response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranscriptionResponse {
    pub text: String,
    pub confidence: f32,
}

/// TTS request to generate speech
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpeechRequest {
    pub text: String,
    pub speaker_id: Option<i32>,
}

/// Start audio capture (microphone)
#[tauri::command]
pub async fn start_audio_capture(
    state: State<'_, Arc<AppState>>,
    _window: Window,
    _config: Option<AudioConfig>,
) -> Result<(), String> {
    let mut audio = state.audio.write();
    audio.is_recording = true;

    // Note: Actual audio capture implementation would use platform-specific APIs
    // For now, this sets up the state for the frontend to handle via Web APIs

    Ok(())
}

/// Stop audio capture
#[tauri::command]
pub async fn stop_audio_capture(state: State<'_, Arc<AppState>>) -> Result<(), String> {
    let mut audio = state.audio.write();
    audio.is_recording = false;
    Ok(())
}

/// Play audio (TTS output)
#[tauri::command]
pub async fn play_audio(
    state: State<'_, Arc<AppState>>,
    window: Window,
    text: String,
    speaker_id: Option<i32>,
) -> Result<String, String> {
    let api_config = state.api_config.read().clone();

    // Update state
    {
        let mut audio = state.audio.write();
        audio.is_playing = true;
    }

    window.emit("audio-playing", true).ok();

    // Call CSM server for TTS
    let audio_base64 = if let Some(ref csm_url) = api_config.csm_server_url {
        call_csm_server(csm_url, &text, speaker_id.unwrap_or(0)).await?
    } else {
        // Fallback: Use browser TTS via event
        window.emit("tts-fallback", &text).ok();
        return Ok("".to_string());
    };

    // Update state
    {
        let mut audio = state.audio.write();
        audio.is_playing = false;
    }

    window.emit("audio-playing", false).ok();

    Ok(audio_base64)
}

/// Stop audio playback
#[tauri::command]
pub async fn stop_audio(
    state: State<'_, Arc<AppState>>,
    window: Window,
) -> Result<(), String> {
    let mut audio = state.audio.write();
    audio.is_playing = false;

    window.emit("audio-stop", true).ok();

    Ok(())
}

/// Transcribe audio using STT service
pub async fn transcribe_audio(
    config: &crate::state::ApiConfig,
    audio_base64: &str,
) -> Result<TranscriptionResponse, String> {
    match config.stt_provider {
        crate::state::SttProvider::Whisper => {
            transcribe_with_openai_whisper(config, audio_base64).await
        }
        crate::state::SttProvider::Groq => {
            transcribe_with_groq(config, audio_base64).await
        }
        crate::state::SttProvider::Deepgram => {
            transcribe_with_deepgram(config, audio_base64).await
        }
    }
}

async fn transcribe_with_openai_whisper(
    config: &crate::state::ApiConfig,
    audio_base64: &str,
) -> Result<TranscriptionResponse, String> {
    let api_key = config.openai_api_key.as_ref()
        .ok_or("OpenAI API key not configured")?;

    let audio_bytes = BASE64.decode(audio_base64)
        .map_err(|e| format!("Failed to decode audio: {}", e))?;

    let client = reqwest::Client::new();

    // Create multipart form
    let part = reqwest::multipart::Part::bytes(audio_bytes)
        .file_name("audio.webm")
        .mime_str("audio/webm")
        .map_err(|e| format!("Failed to create form part: {}", e))?;

    let form = reqwest::multipart::Form::new()
        .part("file", part)
        .text("model", "whisper-1")
        .text("response_format", "json");

    let response = client
        .post("https://api.openai.com/v1/audio/transcriptions")
        .header("Authorization", format!("Bearer {}", api_key))
        .multipart(form)
        .send()
        .await
        .map_err(|e| format!("Failed to call Whisper: {}", e))?;

    let response_json: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    let text = response_json["text"]
        .as_str()
        .ok_or("No text in transcription response")?
        .to_string();

    Ok(TranscriptionResponse {
        text,
        confidence: 1.0,
    })
}

async fn transcribe_with_groq(
    config: &crate::state::ApiConfig,
    audio_base64: &str,
) -> Result<TranscriptionResponse, String> {
    let api_key = config.groq_api_key.as_ref()
        .ok_or("Groq API key not configured")?;

    let audio_bytes = BASE64.decode(audio_base64)
        .map_err(|e| format!("Failed to decode audio: {}", e))?;

    let client = reqwest::Client::new();

    let part = reqwest::multipart::Part::bytes(audio_bytes)
        .file_name("audio.webm")
        .mime_str("audio/webm")
        .map_err(|e| format!("Failed to create form part: {}", e))?;

    let form = reqwest::multipart::Form::new()
        .part("file", part)
        .text("model", "whisper-large-v3")
        .text("response_format", "json");

    let response = client
        .post("https://api.groq.com/openai/v1/audio/transcriptions")
        .header("Authorization", format!("Bearer {}", api_key))
        .multipart(form)
        .send()
        .await
        .map_err(|e| format!("Failed to call Groq: {}", e))?;

    let response_json: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    let text = response_json["text"]
        .as_str()
        .ok_or("No text in transcription response")?
        .to_string();

    Ok(TranscriptionResponse {
        text,
        confidence: 1.0,
    })
}

async fn transcribe_with_deepgram(
    _config: &crate::state::ApiConfig,
    _audio_base64: &str,
) -> Result<TranscriptionResponse, String> {
    // Deepgram implementation placeholder
    Err("Deepgram not yet implemented".to_string())
}

/// Call the CSM server for TTS
async fn call_csm_server(
    server_url: &str,
    text: &str,
    speaker_id: i32,
) -> Result<String, String> {
    let client = reqwest::Client::new();

    let request_body = serde_json::json!({
        "text": text,
        "speaker_id": speaker_id,
        "max_audio_length_ms": 30000
    });

    let response = client
        .post(format!("{}/generate", server_url))
        .header("Content-Type", "application/json")
        .json(&request_body)
        .send()
        .await
        .map_err(|e| format!("Failed to call CSM server: {}", e))?;

    if !response.status().is_success() {
        let error_text = response.text().await.unwrap_or_default();
        return Err(format!("CSM server error: {}", error_text));
    }

    let response_json: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse CSM response: {}", e))?;

    let audio_base64 = response_json["audio"]
        .as_str()
        .ok_or("No audio in CSM response")?
        .to_string();

    Ok(audio_base64)
}
