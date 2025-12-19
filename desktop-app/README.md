# Live Agent Screen Companion

A real-time AI assistant that can see your screen, hear you speak, talk back naturally, and control your mouse and keyboard to help you accomplish tasks.

**Think of it as a world-class expert sitting at your computer, helping you live.**

## Features

- **Screen Awareness**: Agent sees your screen in real-time and understands what's happening
- **Natural Voice**: Uses Sesame CSM for human-like speech synthesis
- **Voice Input**: Speak naturally to the agent with streaming speech recognition
- **Computer Control**: Agent can move mouse, click, type, and use keyboard shortcuts
- **Safety First**: User always has control, with easy interrupt mechanisms
- **Minimal UI**: Floating control panel that stays out of your way

## Requirements

### Desktop App (macOS)
- macOS 12.0 or later
- Rust 1.70+
- Node.js 18+
- Screen capture permission
- Accessibility permission (for input control)
- Microphone permission

### TTS Server
- CUDA-capable GPU (recommended) or Apple Silicon
- Python 3.10+
- ~6GB VRAM for CSM model

## Quick Start

### 1. Set Up the TTS Server

```bash
# From the project root
cd server

# Create virtual environment (if not using the main one)
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r ../requirements.txt

# Start the server
python main.py
```

The server will start on `http://localhost:8000`.

### 2. Build the Desktop App

```bash
cd desktop-app

# Install dependencies
npm install

# Run in development mode
npm run tauri:dev

# Or build for production
npm run tauri:build
```

### 3. Configure the App

1. Open the app and click the settings icon
2. Enter your API keys:
   - **Anthropic API Key** (for Claude) or **OpenAI API Key** (for GPT-4)
   - **OpenAI API Key** for Whisper speech recognition, or use Groq for faster transcription
3. Set the **CSM Server URL** to `http://localhost:8000`

### 4. Grant Permissions

On first launch, the app will request:
- **Screen Recording**: Required to see your screen
- **Accessibility**: Required for mouse/keyboard control
- **Microphone**: Required for voice input

## Usage

1. **Share Screen**: Click "Share Screen" to let the agent see your screen
2. **Talk**: Press the microphone button or just start speaking
3. **Let the Agent Help**: The agent will see your screen, understand your request, and either explain what to do or offer to do it for you
4. **Interrupt**: Say "stop" or click the stop button to interrupt the agent at any time

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Desktop App (Tauri)                   │
├─────────────────────────────────────────────────────────┤
│  React UI          │  Rust Backend                       │
│  - Control Panel   │  - Screen Capture (ScreenCaptureKit)│
│  - Settings        │  - Input Control (Accessibility API)│
│  - Voice Capture   │  - Agent Communication              │
│                    │  - Audio Playback                   │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    External Services                     │
├─────────────────────────────────────────────────────────┤
│  Claude/GPT-4        │  Whisper/Groq    │  CSM Server   │
│  (Multimodal Agent)  │  (STT)           │  (TTS)        │
└─────────────────────────────────────────────────────────┘
```

## Safety Model

The agent operates with strict safety constraints:

1. **User Control First**: User can always interrupt by speaking "stop" or clicking the stop button
2. **Permission Required**: Agent asks before taking control of mouse/keyboard
3. **Instant Release**: Moving the mouse or pressing any key immediately revokes agent control
4. **Visual Indicator**: Clear UI shows when agent is in control
5. **No Background Control**: Agent cannot control the computer unless the app is focused and user has granted permission

## API Configuration

### LLM Providers
- **Anthropic (Claude)**: Best for complex reasoning and screen understanding
- **OpenAI (GPT-4)**: Alternative with strong vision capabilities

### STT Providers
- **OpenAI Whisper**: High accuracy, moderate latency
- **Groq**: Very fast transcription, good accuracy

### TTS
- **Sesame CSM**: Natural, conversational voice (requires local server)
- **Browser Speech**: Fallback using Web Speech API (less natural)

## Development

### Project Structure

```
desktop-app/
├── src/                    # React frontend
│   ├── components/         # UI components
│   ├── hooks/             # React hooks (Tauri integration)
│   ├── stores/            # Zustand state management
│   └── types/             # TypeScript types
├── src-tauri/             # Rust backend
│   └── src/
│       ├── main.rs        # Entry point
│       ├── screen_capture.rs
│       ├── input_control.rs
│       ├── agent.rs
│       ├── audio.rs
│       ├── permissions.rs
│       └── state.rs
server/
├── main.py                # CSM TTS server
└── requirements.txt
```

### Running Tests

```bash
# Frontend tests
cd desktop-app
npm test

# Rust tests
cd desktop-app/src-tauri
cargo test
```

## Troubleshooting

### Screen capture not working
1. Go to System Preferences → Security & Privacy → Screen Recording
2. Ensure "Live Agent" is checked
3. Restart the app

### Input control not working
1. Go to System Preferences → Security & Privacy → Accessibility
2. Ensure "Live Agent" is checked
3. Restart the app

### Voice not working
1. Check microphone permissions
2. Ensure CSM server is running
3. Check the browser console for errors

### High latency
1. Use Groq for faster STT
2. Ensure CSM server is running on GPU
3. Lower screen capture quality in settings

## License

Apache 2.0 - See LICENSE file for details.

## Credits

- [Sesame CSM](https://github.com/SesameAILabs/csm) for the amazing voice model
- [Tauri](https://tauri.app) for the desktop framework
- [Anthropic](https://anthropic.com) and [OpenAI](https://openai.com) for the AI models
