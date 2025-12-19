use crate::state::AppState;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::State;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MousePosition {
    pub x: i32,
    pub y: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MouseButton {
    Left,
    Right,
    Middle,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ScrollDirection {
    Up,
    Down,
    Left,
    Right,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeyModifiers {
    pub shift: bool,
    pub control: bool,
    pub alt: bool,
    pub command: bool,  // macOS specific
}

impl Default for KeyModifiers {
    fn default() -> Self {
        Self {
            shift: false,
            control: false,
            alt: false,
            command: false,
        }
    }
}

/// Check if agent is currently controlling input
#[tauri::command]
pub async fn is_agent_controlling(state: State<'_, Arc<AppState>>) -> Result<bool, String> {
    Ok(state.can_control())
}

/// Release agent control
#[tauri::command]
pub async fn release_control(state: State<'_, Arc<AppState>>) -> Result<(), String> {
    state.revoke_control();
    Ok(())
}

/// Move mouse to position
#[tauri::command]
pub async fn move_mouse(
    state: State<'_, Arc<AppState>>,
    x: i32,
    y: i32,
    smooth: Option<bool>,
) -> Result<(), String> {
    // Safety check
    if !state.can_control() {
        return Err("Agent does not have control permission".to_string());
    }

    // Check for interrupt
    if state.should_interrupt.load(std::sync::atomic::Ordering::SeqCst) {
        return Err("Operation interrupted by user".to_string());
    }

    #[cfg(target_os = "macos")]
    {
        use core_graphics::event::{CGEvent, CGEventTapLocation, CGMouseButton};
        use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
        use core_graphics::geometry::CGPoint;

        let smooth = smooth.unwrap_or(true);

        if smooth {
            // Get current position and animate
            let (current_x, current_y) = get_current_mouse_position();
            let steps = 20;
            let delay_ms = 10;

            for i in 1..=steps {
                let progress = i as f64 / steps as f64;
                // Ease-out curve for natural movement
                let eased = 1.0 - (1.0 - progress).powi(2);

                let new_x = current_x + ((x - current_x) as f64 * eased) as i32;
                let new_y = current_y + ((y - current_y) as f64 * eased) as i32;

                set_mouse_position(new_x, new_y)?;
                std::thread::sleep(std::time::Duration::from_millis(delay_ms));

                // Check for interrupt during animation
                if state.should_interrupt.load(std::sync::atomic::Ordering::SeqCst) {
                    return Err("Operation interrupted by user".to_string());
                }
            }
        } else {
            set_mouse_position(x, y)?;
        }

        Ok(())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Input control is only supported on macOS".to_string())
    }
}

/// Click mouse button
#[tauri::command]
pub async fn click_mouse(
    state: State<'_, Arc<AppState>>,
    button: MouseButton,
    double_click: Option<bool>,
) -> Result<(), String> {
    if !state.can_control() {
        return Err("Agent does not have control permission".to_string());
    }

    #[cfg(target_os = "macos")]
    {
        use core_graphics::event::{
            CGEvent, CGEventTapLocation, CGEventType, CGMouseButton as CGButton,
        };
        use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
        use core_graphics::geometry::CGPoint;

        let (x, y) = get_current_mouse_position();
        let point = CGPoint::new(x as f64, y as f64);

        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState)
            .map_err(|_| "Failed to create event source")?;

        let (cg_button, down_type, up_type) = match button {
            MouseButton::Left => (
                CGButton::Left,
                CGEventType::LeftMouseDown,
                CGEventType::LeftMouseUp,
            ),
            MouseButton::Right => (
                CGButton::Right,
                CGEventType::RightMouseDown,
                CGEventType::RightMouseUp,
            ),
            MouseButton::Middle => (
                CGButton::Center,
                CGEventType::OtherMouseDown,
                CGEventType::OtherMouseUp,
            ),
        };

        let click_count = if double_click.unwrap_or(false) { 2 } else { 1 };

        for _ in 0..click_count {
            let down_event = CGEvent::new_mouse_event(source.clone(), down_type, point, cg_button)
                .map_err(|_| "Failed to create mouse down event")?;
            down_event.post(CGEventTapLocation::HID);

            std::thread::sleep(std::time::Duration::from_millis(50));

            let up_event = CGEvent::new_mouse_event(source.clone(), up_type, point, cg_button)
                .map_err(|_| "Failed to create mouse up event")?;
            up_event.post(CGEventTapLocation::HID);

            if click_count > 1 {
                std::thread::sleep(std::time::Duration::from_millis(100));
            }
        }

        Ok(())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Input control is only supported on macOS".to_string())
    }
}

/// Scroll in a direction
#[tauri::command]
pub async fn scroll(
    state: State<'_, Arc<AppState>>,
    direction: ScrollDirection,
    amount: Option<i32>,
) -> Result<(), String> {
    if !state.can_control() {
        return Err("Agent does not have control permission".to_string());
    }

    #[cfg(target_os = "macos")]
    {
        use core_graphics::event::{CGEvent, CGEventTapLocation, CGScrollEventUnit};
        use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};

        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState)
            .map_err(|_| "Failed to create event source")?;

        let amount = amount.unwrap_or(3);
        let (dx, dy) = match direction {
            ScrollDirection::Up => (0, amount),
            ScrollDirection::Down => (0, -amount),
            ScrollDirection::Left => (-amount, 0),
            ScrollDirection::Right => (amount, 0),
        };

        let event = CGEvent::new_scroll_event(source, CGScrollEventUnit::LINE, 2, dy, dx, 0)
            .map_err(|_| "Failed to create scroll event")?;
        event.post(CGEventTapLocation::HID);

        Ok(())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Input control is only supported on macOS".to_string())
    }
}

/// Type text
#[tauri::command]
pub async fn type_text(
    state: State<'_, Arc<AppState>>,
    text: String,
    delay_ms: Option<u64>,
) -> Result<(), String> {
    if !state.can_control() {
        return Err("Agent does not have control permission".to_string());
    }

    #[cfg(target_os = "macos")]
    {
        use core_graphics::event::{CGEvent, CGEventTapLocation, CGKeyCode};
        use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};

        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState)
            .map_err(|_| "Failed to create event source")?;

        let delay = std::time::Duration::from_millis(delay_ms.unwrap_or(30));

        for c in text.chars() {
            // Check for interrupt
            if state.should_interrupt.load(std::sync::atomic::Ordering::SeqCst) {
                return Err("Operation interrupted by user".to_string());
            }

            // Use CGEvent's string-based input for proper Unicode support
            let char_string = c.to_string();

            // Create a key down event and set the unicode string
            if let Some(keycode) = char_to_keycode(c) {
                let needs_shift = c.is_uppercase() || is_shifted_char(c);

                if needs_shift {
                    // Press shift
                    let shift_down = CGEvent::new_keyboard_event(source.clone(), 56, true)
                        .map_err(|_| "Failed to create shift down event")?;
                    shift_down.post(CGEventTapLocation::HID);
                }

                let key_down = CGEvent::new_keyboard_event(source.clone(), keycode, true)
                    .map_err(|_| "Failed to create key down event")?;
                key_down.post(CGEventTapLocation::HID);

                std::thread::sleep(std::time::Duration::from_millis(10));

                let key_up = CGEvent::new_keyboard_event(source.clone(), keycode, false)
                    .map_err(|_| "Failed to create key up event")?;
                key_up.post(CGEventTapLocation::HID);

                if needs_shift {
                    // Release shift
                    let shift_up = CGEvent::new_keyboard_event(source.clone(), 56, false)
                        .map_err(|_| "Failed to create shift up event")?;
                    shift_up.post(CGEventTapLocation::HID);
                }
            }

            std::thread::sleep(delay);
        }

        Ok(())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Input control is only supported on macOS".to_string())
    }
}

/// Press a keyboard shortcut or special key
#[tauri::command]
pub async fn press_key(
    state: State<'_, Arc<AppState>>,
    key: String,
    modifiers: Option<KeyModifiers>,
) -> Result<(), String> {
    if !state.can_control() {
        return Err("Agent does not have control permission".to_string());
    }

    #[cfg(target_os = "macos")]
    {
        use core_graphics::event::{CGEvent, CGEventFlags, CGEventTapLocation};
        use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};

        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState)
            .map_err(|_| "Failed to create event source")?;

        let modifiers = modifiers.unwrap_or_default();
        let keycode = key_name_to_keycode(&key).ok_or("Unknown key")?;

        // Build modifier flags
        let mut flags = CGEventFlags::empty();
        if modifiers.shift {
            flags |= CGEventFlags::CGEventFlagShift;
        }
        if modifiers.control {
            flags |= CGEventFlags::CGEventFlagControl;
        }
        if modifiers.alt {
            flags |= CGEventFlags::CGEventFlagAlternate;
        }
        if modifiers.command {
            flags |= CGEventFlags::CGEventFlagCommand;
        }

        // Key down
        let key_down = CGEvent::new_keyboard_event(source.clone(), keycode, true)
            .map_err(|_| "Failed to create key down event")?;
        key_down.set_flags(flags);
        key_down.post(CGEventTapLocation::HID);

        std::thread::sleep(std::time::Duration::from_millis(50));

        // Key up
        let key_up = CGEvent::new_keyboard_event(source.clone(), keycode, false)
            .map_err(|_| "Failed to create key up event")?;
        key_up.set_flags(flags);
        key_up.post(CGEventTapLocation::HID);

        Ok(())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Input control is only supported on macOS".to_string())
    }
}

#[cfg(target_os = "macos")]
fn get_current_mouse_position() -> (i32, i32) {
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
fn set_mouse_position(x: i32, y: i32) -> Result<(), String> {
    use core_graphics::event::{CGEvent, CGEventTapLocation, CGEventType, CGMouseButton};
    use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
    use core_graphics::geometry::CGPoint;

    let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState)
        .map_err(|_| "Failed to create event source")?;

    let point = CGPoint::new(x as f64, y as f64);
    let event = CGEvent::new_mouse_event(source, CGEventType::MouseMoved, point, CGMouseButton::Left)
        .map_err(|_| "Failed to create mouse move event")?;

    event.post(CGEventTapLocation::HID);
    Ok(())
}

#[cfg(target_os = "macos")]
fn char_to_keycode(c: char) -> Option<u16> {
    // macOS keycodes for common characters
    match c.to_ascii_lowercase() {
        'a' => Some(0),
        's' => Some(1),
        'd' => Some(2),
        'f' => Some(3),
        'h' => Some(4),
        'g' => Some(5),
        'z' => Some(6),
        'x' => Some(7),
        'c' => Some(8),
        'v' => Some(9),
        'b' => Some(11),
        'q' => Some(12),
        'w' => Some(13),
        'e' => Some(14),
        'r' => Some(15),
        'y' => Some(16),
        't' => Some(17),
        '1' | '!' => Some(18),
        '2' | '@' => Some(19),
        '3' | '#' => Some(20),
        '4' | '$' => Some(21),
        '6' | '^' => Some(22),
        '5' | '%' => Some(23),
        '=' | '+' => Some(24),
        '9' | '(' => Some(25),
        '7' | '&' => Some(26),
        '-' | '_' => Some(27),
        '8' | '*' => Some(28),
        '0' | ')' => Some(29),
        ']' | '}' => Some(30),
        'o' => Some(31),
        'u' => Some(32),
        '[' | '{' => Some(33),
        'i' => Some(34),
        'p' => Some(35),
        'l' => Some(37),
        'j' => Some(38),
        '\'' | '"' => Some(39),
        'k' => Some(40),
        ';' | ':' => Some(41),
        '\\' | '|' => Some(42),
        ',' | '<' => Some(43),
        '/' | '?' => Some(44),
        'n' => Some(45),
        'm' => Some(46),
        '.' | '>' => Some(47),
        '`' | '~' => Some(50),
        ' ' => Some(49),
        _ => None,
    }
}

#[cfg(target_os = "macos")]
fn is_shifted_char(c: char) -> bool {
    matches!(
        c,
        '!' | '@' | '#' | '$' | '%' | '^' | '&' | '*' | '(' | ')' | '_' | '+' | '{' | '}' | '|'
            | ':' | '"' | '<' | '>' | '?' | '~'
    )
}

#[cfg(target_os = "macos")]
fn key_name_to_keycode(name: &str) -> Option<u16> {
    match name.to_lowercase().as_str() {
        "return" | "enter" => Some(36),
        "tab" => Some(48),
        "space" => Some(49),
        "delete" | "backspace" => Some(51),
        "escape" | "esc" => Some(53),
        "command" | "cmd" => Some(55),
        "shift" => Some(56),
        "capslock" => Some(57),
        "option" | "alt" => Some(58),
        "control" | "ctrl" => Some(59),
        "left" => Some(123),
        "right" => Some(124),
        "down" => Some(125),
        "up" => Some(126),
        "f1" => Some(122),
        "f2" => Some(120),
        "f3" => Some(99),
        "f4" => Some(118),
        "f5" => Some(96),
        "f6" => Some(97),
        "f7" => Some(98),
        "f8" => Some(100),
        "f9" => Some(101),
        "f10" => Some(109),
        "f11" => Some(103),
        "f12" => Some(111),
        "home" => Some(115),
        "end" => Some(119),
        "pageup" => Some(116),
        "pagedown" => Some(121),
        _ => {
            // Try single character
            if name.len() == 1 {
                char_to_keycode(name.chars().next()?)
            } else {
                None
            }
        }
    }
}
