# Jarvis iOS App

A voice-enabled AI personal assistant powered by Sesame CSM and Claude.

## Requirements

- Xcode 15.0+
- iOS 17.0+
- Swift 5.9+

## Project Setup

### 1. Create Xcode Project

1. Open Xcode
2. Create new project: **App** template
3. Product Name: **Jarvis**
4. Organization Identifier: **com.yourcompany**
5. Interface: **SwiftUI**
6. Language: **Swift**

### 2. Add Source Files

Copy all files from `Sources/` into your Xcode project:
- `JarvisApp.swift`
- `ContentView.swift`
- `VoiceAssistant.swift`
- `WebSocketManager.swift`

### 3. Configure Permissions

Add to `Info.plist`:

```xml
<key>NSMicrophoneUsageDescription</key>
<string>Jarvis needs microphone access to hear your voice commands.</string>
<key>NSSpeechRecognitionUsageDescription</key>
<string>Jarvis uses speech recognition to understand your commands.</string>
```

### 4. Configure App Transport Security

For development with local server, add to `Info.plist`:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

**Note:** For production, configure specific domains instead.

### 5. Build Settings

- Set **iOS Deployment Target** to 17.0
- Enable **Background Modes** if you want background audio

## Architecture

```
Jarvis/
├── Sources/
│   ├── JarvisApp.swift         # App entry point
│   ├── ContentView.swift       # Main UI with orb visualization
│   ├── VoiceAssistant.swift    # Core voice logic
│   └── WebSocketManager.swift  # Real-time streaming (optional)
└── Resources/
    └── (assets, sounds, etc.)
```

## Configuration

Update the server URL in Settings or modify `AppState`:

```swift
@Published var serverURL: String = "https://your-server.com"
```

## Features

- **Voice Input**: Tap to record, tap again to send
- **Text Input**: Keyboard option for typing
- **Visual Feedback**: Animated orb shows state (listening/processing/speaking)
- **Conversation History**: Maintains context across messages
- **Tool Feedback**: Shows which tools Jarvis used

## Customization

### Orb Colors

Edit `OrbView` in `ContentView.swift`:

```swift
var orbColor: Color {
    if isListening { return Color(hex: "00d4ff") }  // Blue when listening
    if isProcessing { return Color(hex: "ff6b35") } // Orange when processing
    if isSpeaking { return Color(hex: "7b68ee") }   // Purple when speaking
    return Color(hex: "4a9eff")                      // Default blue
}
```

### Add Haptic Feedback

Already included - vibrates on record start/stop.

### Add Wake Word

Consider integrating:
- [Picovoice Porcupine](https://picovoice.ai/) for "Hey Jarvis"
- Apple's Speech framework for always-on listening

## Testing

1. Run the backend server
2. Update the server URL in the app
3. Build and run on device (microphone requires real device)
4. Tap the mic button and speak

## Troubleshooting

**No audio playback:**
- Check audio session category is `.playAndRecord`
- Ensure audio data is valid WAV format

**Connection errors:**
- Verify server URL is correct
- Check network connectivity
- Ensure server is running

**Microphone not working:**
- Grant microphone permissions
- Test on real device (not simulator)
