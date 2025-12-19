use serde::{Deserialize, Serialize};

/// Permission status for each required capability
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionStatus {
    pub screen_capture: PermissionState,
    pub accessibility: PermissionState,
    pub microphone: PermissionState,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PermissionState {
    Granted,
    Denied,
    NotDetermined,
    Restricted,
}

/// Check all required permissions
#[tauri::command]
pub async fn check_permissions() -> Result<PermissionStatus, String> {
    #[cfg(target_os = "macos")]
    {
        Ok(PermissionStatus {
            screen_capture: check_screen_capture_permission(),
            accessibility: check_accessibility_permission(),
            microphone: check_microphone_permission(),
        })
    }

    #[cfg(not(target_os = "macos"))]
    {
        Ok(PermissionStatus {
            screen_capture: PermissionState::Granted,
            accessibility: PermissionState::Granted,
            microphone: PermissionState::Granted,
        })
    }
}

/// Request permissions (opens system preferences)
#[tauri::command]
pub async fn request_permissions(permission_type: String) -> Result<bool, String> {
    #[cfg(target_os = "macos")]
    {
        match permission_type.as_str() {
            "screen_capture" => request_screen_capture_permission(),
            "accessibility" => request_accessibility_permission(),
            "microphone" => request_microphone_permission(),
            _ => Err(format!("Unknown permission type: {}", permission_type)),
        }
    }

    #[cfg(not(target_os = "macos"))]
    {
        Ok(true)
    }
}

#[cfg(target_os = "macos")]
fn check_screen_capture_permission() -> PermissionState {
    use core_graphics::display::CGDisplay;

    // Try to capture - if it works, we have permission
    let displays = CGDisplay::active_displays();
    match displays {
        Ok(list) if !list.is_empty() => {
            let display = CGDisplay::new(list[0]);
            if display.image().is_some() {
                PermissionState::Granted
            } else {
                PermissionState::Denied
            }
        }
        _ => PermissionState::NotDetermined,
    }
}

#[cfg(target_os = "macos")]
fn check_accessibility_permission() -> PermissionState {
    // Use objc to check AXIsProcessTrusted
    use std::process::Command;

    let output = Command::new("osascript")
        .args(["-e", r#"tell application "System Events" to return true"#])
        .output();

    match output {
        Ok(out) if out.status.success() => PermissionState::Granted,
        _ => PermissionState::NotDetermined,
    }
}

#[cfg(target_os = "macos")]
fn check_microphone_permission() -> PermissionState {
    // Check via AVFoundation would be ideal, but for now use a simpler check
    use std::process::Command;

    let output = Command::new("osascript")
        .args(["-e", r#"
            use framework "AVFoundation"
            set authStatus to current application's AVCaptureDevice's authorizationStatusForMediaType:(current application's AVMediaTypeAudio)
            if authStatus is 0 then
                return "not_determined"
            else if authStatus is 1 then
                return "restricted"
            else if authStatus is 2 then
                return "denied"
            else
                return "granted"
            end if
        "#])
        .output();

    match output {
        Ok(out) => {
            let status = String::from_utf8_lossy(&out.stdout).trim().to_string();
            match status.as_str() {
                "granted" => PermissionState::Granted,
                "denied" => PermissionState::Denied,
                "restricted" => PermissionState::Restricted,
                _ => PermissionState::NotDetermined,
            }
        }
        _ => PermissionState::NotDetermined,
    }
}

#[cfg(target_os = "macos")]
fn request_screen_capture_permission() -> Result<bool, String> {
    use std::process::Command;

    // Open System Preferences to Screen Recording
    Command::new("open")
        .args(["x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"])
        .spawn()
        .map_err(|e| format!("Failed to open System Preferences: {}", e))?;

    Ok(true)
}

#[cfg(target_os = "macos")]
fn request_accessibility_permission() -> Result<bool, String> {
    use std::process::Command;

    // Open System Preferences to Accessibility
    Command::new("open")
        .args(["x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
        .spawn()
        .map_err(|e| format!("Failed to open System Preferences: {}", e))?;

    Ok(true)
}

#[cfg(target_os = "macos")]
fn request_microphone_permission() -> Result<bool, String> {
    use std::process::Command;

    // Open System Preferences to Microphone
    Command::new("open")
        .args(["x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"])
        .spawn()
        .map_err(|e| format!("Failed to open System Preferences: {}", e))?;

    Ok(true)
}
