use crate::state::{AgentStatus, ApiConfig, AppState, LlmProvider, SttProvider};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::{Emitter, State, Window};

/// Message from user to agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserMessage {
    pub text: Option<String>,
    pub audio_base64: Option<String>,
    pub screen_frame: Option<String>,  // Base64 encoded screenshot
    pub cursor_position: Option<(i32, i32)>,
    pub active_window: Option<String>,
}

/// Action the agent wants to perform
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum AgentAction {
    Speak { text: String },
    MoveMouse { x: i32, y: i32 },
    Click { button: String, double: bool },
    Scroll { direction: String, amount: i32 },
    Type { text: String },
    PressKey { key: String, modifiers: Vec<String> },
    AskPermission { action: String },
    RequestControl,
    ReleaseControl,
    Wait { ms: u64 },
}

/// Response from agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResponse {
    pub thoughts: String,
    pub speech: Option<String>,
    pub actions: Vec<AgentAction>,
    pub needs_permission: bool,
}

/// Status response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStatusResponse {
    pub status: String,
    pub has_control: bool,
    pub is_speaking: bool,
    pub can_be_interrupted: bool,
}

/// Set API configuration
#[tauri::command]
pub async fn set_api_config(
    state: State<'_, Arc<AppState>>,
    config: ApiConfig,
) -> Result<(), String> {
    let mut api_config = state.api_config.write();
    *api_config = config;
    Ok(())
}

/// Get current agent status
#[tauri::command]
pub async fn get_agent_status(state: State<'_, Arc<AppState>>) -> Result<AgentStatusResponse, String> {
    let status = state.agent_status.read();
    let has_control = state.can_control();

    Ok(AgentStatusResponse {
        status: format!("{:?}", *status),
        has_control,
        is_speaking: *status == AgentStatus::Speaking,
        can_be_interrupted: *status != AgentStatus::Idle,
    })
}

/// Interrupt the agent
#[tauri::command]
pub async fn interrupt_agent(state: State<'_, Arc<AppState>>) -> Result<(), String> {
    state.request_interrupt();

    let mut status = state.agent_status.write();
    *status = AgentStatus::Interrupted;

    Ok(())
}

/// Send message to agent and get response
#[tauri::command]
pub async fn send_to_agent(
    state: State<'_, Arc<AppState>>,
    window: Window,
    message: UserMessage,
) -> Result<AgentResponse, String> {
    // Update status to thinking
    {
        let mut status = state.agent_status.write();
        *status = AgentStatus::Thinking;
    }
    window.emit("agent-status", "thinking").ok();

    // Get API config
    let api_config = state.api_config.read().clone();

    // Build the prompt for the LLM
    let response = match api_config.llm_provider {
        LlmProvider::Anthropic => {
            call_claude(&api_config, &message).await?
        }
        LlmProvider::OpenAI => {
            call_openai(&api_config, &message).await?
        }
    };

    // Update status
    {
        let mut status = state.agent_status.write();
        *status = if response.speech.is_some() {
            AgentStatus::Speaking
        } else {
            AgentStatus::Idle
        };
    }
    window.emit("agent-response", &response).ok();

    Ok(response)
}

async fn call_claude(config: &ApiConfig, message: &UserMessage) -> Result<AgentResponse, String> {
    let api_key = config.anthropic_api_key.as_ref()
        .ok_or("Anthropic API key not configured")?;

    let client = reqwest::Client::new();

    // Build messages with vision support
    let mut content = Vec::new();

    // Add screenshot if available
    if let Some(ref frame) = message.screen_frame {
        content.push(serde_json::json!({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": frame
            }
        }));
    }

    // Add context about cursor and window
    let mut context_text = String::new();
    if let Some((x, y)) = message.cursor_position {
        context_text.push_str(&format!("Cursor position: ({}, {})\n", x, y));
    }
    if let Some(ref window) = message.active_window {
        context_text.push_str(&format!("Active window: {}\n", window));
    }

    // Add user's text or transcription
    if let Some(ref text) = message.text {
        context_text.push_str(&format!("\nUser says: {}", text));
    }

    content.push(serde_json::json!({
        "type": "text",
        "text": context_text
    }));

    let system_prompt = build_system_prompt();

    let request_body = serde_json::json!({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": [{
            "role": "user",
            "content": content
        }]
    });

    let response = client
        .post("https://api.anthropic.com/v1/messages")
        .header("x-api-key", api_key)
        .header("anthropic-version", "2023-06-01")
        .header("content-type", "application/json")
        .json(&request_body)
        .send()
        .await
        .map_err(|e| format!("Failed to call Claude: {}", e))?;

    let response_text = response.text().await
        .map_err(|e| format!("Failed to read response: {}", e))?;

    let response_json: serde_json::Value = serde_json::from_str(&response_text)
        .map_err(|e| format!("Failed to parse response: {} - {}", e, response_text))?;

    // Extract the assistant's response
    let assistant_text = response_json["content"][0]["text"]
        .as_str()
        .ok_or("No text in response")?;

    // Parse the structured response
    parse_agent_response(assistant_text)
}

async fn call_openai(config: &ApiConfig, message: &UserMessage) -> Result<AgentResponse, String> {
    let api_key = config.openai_api_key.as_ref()
        .ok_or("OpenAI API key not configured")?;

    let client = reqwest::Client::new();

    // Build messages with vision support
    let mut content = Vec::new();

    // Add screenshot if available
    if let Some(ref frame) = message.screen_frame {
        content.push(serde_json::json!({
            "type": "image_url",
            "image_url": {
                "url": format!("data:image/jpeg;base64,{}", frame),
                "detail": "high"
            }
        }));
    }

    // Add context
    let mut context_text = String::new();
    if let Some((x, y)) = message.cursor_position {
        context_text.push_str(&format!("Cursor position: ({}, {})\n", x, y));
    }
    if let Some(ref window) = message.active_window {
        context_text.push_str(&format!("Active window: {}\n", window));
    }
    if let Some(ref text) = message.text {
        context_text.push_str(&format!("\nUser says: {}", text));
    }

    content.push(serde_json::json!({
        "type": "text",
        "text": context_text
    }));

    let system_prompt = build_system_prompt();

    let request_body = serde_json::json!({
        "model": "gpt-4o",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": content
            }
        ]
    });

    let response = client
        .post("https://api.openai.com/v1/chat/completions")
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Content-Type", "application/json")
        .json(&request_body)
        .send()
        .await
        .map_err(|e| format!("Failed to call OpenAI: {}", e))?;

    let response_json: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    let assistant_text = response_json["choices"][0]["message"]["content"]
        .as_str()
        .ok_or("No text in response")?;

    parse_agent_response(assistant_text)
}

fn build_system_prompt() -> String {
    r#"You are a helpful AI assistant that can see the user's screen and control their computer when permitted.
You are calm, confident, and slightly conversational. Never say "as an AI" or apologize excessively.

CAPABILITIES:
- You can see screenshots of the user's screen
- You can move the mouse, click, scroll, and type
- You can execute keyboard shortcuts
- You must always explain what you're doing

IMPORTANT RULES:
1. ALWAYS explain what you see and what you're about to do
2. Ask permission before taking control for the first time in a session
3. If the task is complex, explain your plan first
4. If something looks wrong or unexpected, stop and ask the user
5. Be concise but informative in your speech
6. Talk while acting, not after

RESPONSE FORMAT:
You must respond in this exact JSON format:
{
  "thoughts": "Your internal reasoning about what you see and what to do",
  "speech": "What you say out loud to the user (conversational, not robotic)",
  "actions": [
    // Array of actions to perform, in order
    {"type": "Speak", "text": "What to say"},
    {"type": "MoveMouse", "x": 100, "y": 200},
    {"type": "Click", "button": "left", "double": false},
    {"type": "Type", "text": "text to type"},
    {"type": "PressKey", "key": "return", "modifiers": ["command"]},
    {"type": "Scroll", "direction": "down", "amount": 3},
    {"type": "RequestControl"},
    {"type": "ReleaseControl"},
    {"type": "Wait", "ms": 500}
  ],
  "needs_permission": false
}

Available actions:
- Speak: Say something to the user
- MoveMouse: Move cursor to x,y coordinates
- Click: Click mouse (button: "left", "right", "middle")
- Type: Type text
- PressKey: Press a key with optional modifiers (command, shift, control, option)
- Scroll: Scroll in a direction (up, down, left, right)
- RequestControl: Ask for permission to control the computer
- ReleaseControl: Give up control
- Wait: Wait for specified milliseconds

Remember: Be helpful, be clear, and always prioritize the user's safety and control."#.to_string()
}

fn parse_agent_response(text: &str) -> Result<AgentResponse, String> {
    // Try to find JSON in the response
    let json_start = text.find('{');
    let json_end = text.rfind('}');

    let json_str = match (json_start, json_end) {
        (Some(start), Some(end)) => &text[start..=end],
        _ => return Err("No JSON found in response".to_string()),
    };

    let parsed: serde_json::Value = serde_json::from_str(json_str)
        .map_err(|e| format!("Failed to parse JSON: {}", e))?;

    let thoughts = parsed["thoughts"].as_str().unwrap_or("").to_string();
    let speech = parsed["speech"].as_str().map(|s| s.to_string());
    let needs_permission = parsed["needs_permission"].as_bool().unwrap_or(false);

    let mut actions = Vec::new();
    if let Some(action_array) = parsed["actions"].as_array() {
        for action in action_array {
            if let Some(action_type) = action["type"].as_str() {
                let parsed_action = match action_type {
                    "Speak" => {
                        Some(AgentAction::Speak {
                            text: action["text"].as_str().unwrap_or("").to_string(),
                        })
                    }
                    "MoveMouse" => {
                        Some(AgentAction::MoveMouse {
                            x: action["x"].as_i64().unwrap_or(0) as i32,
                            y: action["y"].as_i64().unwrap_or(0) as i32,
                        })
                    }
                    "Click" => {
                        Some(AgentAction::Click {
                            button: action["button"].as_str().unwrap_or("left").to_string(),
                            double: action["double"].as_bool().unwrap_or(false),
                        })
                    }
                    "Type" => {
                        Some(AgentAction::Type {
                            text: action["text"].as_str().unwrap_or("").to_string(),
                        })
                    }
                    "PressKey" => {
                        let modifiers = action["modifiers"]
                            .as_array()
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                                    .collect()
                            })
                            .unwrap_or_default();
                        Some(AgentAction::PressKey {
                            key: action["key"].as_str().unwrap_or("").to_string(),
                            modifiers,
                        })
                    }
                    "Scroll" => {
                        Some(AgentAction::Scroll {
                            direction: action["direction"].as_str().unwrap_or("down").to_string(),
                            amount: action["amount"].as_i64().unwrap_or(3) as i32,
                        })
                    }
                    "RequestControl" => Some(AgentAction::RequestControl),
                    "ReleaseControl" => Some(AgentAction::ReleaseControl),
                    "Wait" => {
                        Some(AgentAction::Wait {
                            ms: action["ms"].as_u64().unwrap_or(500),
                        })
                    }
                    _ => None,
                };

                if let Some(a) = parsed_action {
                    actions.push(a);
                }
            }
        }
    }

    Ok(AgentResponse {
        thoughts,
        speech,
        actions,
        needs_permission,
    })
}
