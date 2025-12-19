// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod screen_capture;
mod input_control;
mod agent;
mod audio;
mod permissions;
mod state;

use state::AppState;
use std::sync::Arc;
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Arc::new(AppState::new()))
        .invoke_handler(tauri::generate_handler![
            // Screen capture commands
            screen_capture::start_screen_capture,
            screen_capture::stop_screen_capture,
            screen_capture::get_available_displays,
            screen_capture::capture_frame,

            // Input control commands
            input_control::move_mouse,
            input_control::click_mouse,
            input_control::scroll,
            input_control::type_text,
            input_control::press_key,
            input_control::release_control,
            input_control::is_agent_controlling,

            // Agent commands
            agent::send_to_agent,
            agent::interrupt_agent,
            agent::set_api_config,
            agent::get_agent_status,

            // Audio commands
            audio::start_audio_capture,
            audio::stop_audio_capture,
            audio::play_audio,
            audio::stop_audio,

            // Permission commands
            permissions::check_permissions,
            permissions::request_permissions,
        ])
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();

            // Set up window to be always on top but not steal focus
            #[cfg(target_os = "macos")]
            {
                window.set_always_on_top(true).ok();
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
