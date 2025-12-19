use crate::state::AppState;
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::State;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DisplayInfo {
    pub id: u32,
    pub name: String,
    pub width: u32,
    pub height: u32,
    pub is_primary: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CaptureFrame {
    pub data: String,  // Base64 encoded image
    pub width: u32,
    pub height: u32,
    pub timestamp: i64,
    pub cursor_x: i32,
    pub cursor_y: i32,
    pub active_window: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CaptureConfig {
    pub display_id: u32,
    pub frame_rate: u32,
    pub scale: f32,  // 0.5 = half resolution
    pub quality: u32,  // JPEG quality 0-100
}

impl Default for CaptureConfig {
    fn default() -> Self {
        Self {
            display_id: 0,
            frame_rate: 5,  // 5 FPS for low latency
            scale: 0.5,
            quality: 70,
        }
    }
}

/// Get list of available displays
#[tauri::command]
pub async fn get_available_displays() -> Result<Vec<DisplayInfo>, String> {
    #[cfg(target_os = "macos")]
    {
        use core_graphics::display::CGDisplay;

        let displays = CGDisplay::active_displays()
            .map_err(|e| format!("Failed to get displays: {:?}", e))?;

        let mut result = Vec::new();
        for (i, display_id) in displays.iter().enumerate() {
            let display = CGDisplay::new(*display_id);
            let bounds = display.bounds();

            result.push(DisplayInfo {
                id: *display_id,
                name: format!("Display {}", i + 1),
                width: bounds.size.width as u32,
                height: bounds.size.height as u32,
                is_primary: display.is_main(),
            });
        }

        Ok(result)
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Screen capture is only supported on macOS".to_string())
    }
}

/// Start continuous screen capture
#[tauri::command]
pub async fn start_screen_capture(
    state: State<'_, Arc<AppState>>,
    config: Option<CaptureConfig>,
) -> Result<(), String> {
    let config = config.unwrap_or_default();

    let mut capture = state.capture.write();
    capture.is_capturing = true;
    capture.display_id = config.display_id;
    capture.frame_rate = config.frame_rate;

    Ok(())
}

/// Stop screen capture
#[tauri::command]
pub async fn stop_screen_capture(state: State<'_, Arc<AppState>>) -> Result<(), String> {
    let mut capture = state.capture.write();
    capture.is_capturing = false;

    Ok(())
}

/// Capture a single frame
#[tauri::command]
pub async fn capture_frame(
    state: State<'_, Arc<AppState>>,
    scale: Option<f32>,
    quality: Option<u32>,
) -> Result<CaptureFrame, String> {
    let capture = state.capture.read();
    let display_id = capture.display_id;
    drop(capture);

    let scale = scale.unwrap_or(0.5);
    let quality = quality.unwrap_or(70);

    #[cfg(target_os = "macos")]
    {
        use core_graphics::display::{CGDisplay, CGPoint};
        use core_graphics::event::{CGEvent, CGEventType};
        use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
        use image::{ImageBuffer, Rgba};

        let display = CGDisplay::new(display_id);
        let bounds = display.bounds();

        // Capture the screen
        let image = match display.image() {
            Some(img) => img,
            None => return Err("Failed to capture screen".to_string()),
        };

        let width = image.width() as u32;
        let height = image.height() as u32;
        let bytes_per_row = image.bytes_per_row();
        let data = image.data();
        let bytes = data.bytes();

        // Scale down the image
        let new_width = (width as f32 * scale) as u32;
        let new_height = (height as f32 * scale) as u32;

        // Convert to image buffer
        let mut img_buffer: ImageBuffer<Rgba<u8>, Vec<u8>> = ImageBuffer::new(width, height);
        for y in 0..height {
            for x in 0..width {
                let offset = (y as usize * bytes_per_row) + (x as usize * 4);
                if offset + 3 < bytes.len() {
                    let b = bytes[offset];
                    let g = bytes[offset + 1];
                    let r = bytes[offset + 2];
                    let a = bytes[offset + 3];
                    img_buffer.put_pixel(x, y, Rgba([r, g, b, a]));
                }
            }
        }

        // Resize
        let resized = image::imageops::resize(
            &img_buffer,
            new_width,
            new_height,
            image::imageops::FilterType::Triangle,
        );

        // Convert to JPEG
        let mut jpeg_data = Vec::new();
        let mut cursor = std::io::Cursor::new(&mut jpeg_data);

        image::codecs::jpeg::JpegEncoder::new_with_quality(&mut cursor, quality as u8)
            .encode(
                resized.as_raw(),
                new_width,
                new_height,
                image::ExtendedColorType::Rgba8,
            )
            .map_err(|e| format!("Failed to encode image: {}", e))?;

        // Get cursor position
        let (cursor_x, cursor_y) = get_cursor_position();

        // Get active window name
        let active_window = get_active_window_name();

        Ok(CaptureFrame {
            data: BASE64.encode(&jpeg_data),
            width: new_width,
            height: new_height,
            timestamp: chrono::Utc::now().timestamp_millis(),
            cursor_x,
            cursor_y,
            active_window,
        })
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Screen capture is only supported on macOS".to_string())
    }
}

#[cfg(target_os = "macos")]
fn get_cursor_position() -> (i32, i32) {
    use core_graphics::event::{CGEvent, CGEventType};
    use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};

    let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState).ok();
    if let Some(src) = source {
        if let Ok(event) = CGEvent::new(src) {
            let location = event.location();
            return (location.x as i32, location.y as i32);
        }
    }
    (0, 0)
}

#[cfg(target_os = "macos")]
fn get_active_window_name() -> Option<String> {
    // This requires accessibility permissions
    // For now, return None - we'll implement with proper accessibility API
    None
}

#[cfg(not(target_os = "macos"))]
fn get_cursor_position() -> (i32, i32) {
    (0, 0)
}

#[cfg(not(target_os = "macos"))]
fn get_active_window_name() -> Option<String> {
    None
}
