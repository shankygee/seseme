# Jarvis AI Assistant

A voice-enabled AI personal assistant for iPhone, powered by **Sesame CSM** for natural speech and **Claude** for intelligence.

> "Just a rather very intelligent system" - Like Iron Man's Jarvis, but real.

## Features

- **Natural Voice**: Human-like speech using Sesame CSM text-to-speech
- **Conversational AI**: Powered by Claude with full context awareness
- **Task Execution**: Set reminders, send messages, control smart home, and more
- **Real-time Processing**: WebSocket support for streaming responses
- **Privacy-First**: Self-hosted backend, your data stays yours

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        iPhone App                                │
│  Voice Recording → Send to Backend → Play Response              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (GPU Server)                         │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Whisper   │  │   Claude    │  │         CSM             │ │
│  │ Speech→Text │  │  AI Brain   │  │     Text→Speech         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                          │                                       │
│               ┌──────────┴──────────┐                           │
│               │   Agent Framework   │                           │
│               │ (Tools & Actions)   │                           │
│               └─────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/YOUR_REPO/seseme.git
cd seseme/jarvis

# Run local setup
chmod +x deploy/scripts/setup-local.sh
./deploy/scripts/setup-local.sh
```

### 2. Configure API Key

Edit `backend/.env` and add your Anthropic API key:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Start the Server

```bash
source venv/bin/activate
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Text chat (no voice)
curl -X POST http://localhost:8000/api/v1/chat/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello Jarvis!", "user_id": "test"}'
```

### 5. Build iOS App

See [ios/README.md](ios/README.md) for Xcode setup instructions.

## Project Structure

```
jarvis/
├── backend/                 # Python FastAPI server
│   ├── app/
│   │   ├── main.py         # API endpoints
│   │   └── config.py       # Configuration
│   ├── services/
│   │   ├── voice_service.py        # CSM integration
│   │   ├── transcription_service.py # Whisper integration
│   │   └── conversation_service.py  # Chat history
│   ├── agents/
│   │   ├── jarvis_agent.py # Claude agent with tools
│   │   └── tools.py        # Available actions
│   └── requirements.txt
│
├── ios/                     # Swift iOS app
│   └── Jarvis/
│       └── Sources/
│           ├── JarvisApp.swift
│           ├── ContentView.swift
│           ├── VoiceAssistant.swift
│           └── WebSocketManager.swift
│
└── deploy/                  # Deployment configs
    ├── Dockerfile
    ├── docker-compose.yml
    ├── nginx.conf
    └── scripts/
        ├── setup-local.sh
        ├── deploy-aws.sh
        ├── deploy-gcp.sh
        └── deploy-runpod.sh
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/transcribe` | Speech-to-text |
| POST | `/api/v1/synthesize` | Text-to-speech |
| POST | `/api/v1/chat/voice` | Full voice chat pipeline |
| POST | `/api/v1/chat/text` | Text chat with voice response |
| WS | `/ws/chat/{user_id}` | Real-time streaming |

### Voice Chat Request

```bash
curl -X POST http://localhost:8000/api/v1/chat/voice \
  -F "audio=@recording.wav" \
  -F "user_id=user123" \
  -F "conversation_id=conv456"
```

### Response Format

```json
{
  "text": "I've set a reminder for tomorrow at 9 AM.",
  "audio_base64": "UklGRi...",
  "conversation_id": "conv456",
  "tools_used": ["set_reminder"]
}
```

## Available Tools

Jarvis can execute these actions:

| Tool | Description |
|------|-------------|
| `get_current_time` | Get date/time |
| `set_reminder` | Create reminders |
| `search_web` | Web search |
| `send_message` | SMS/Email |
| `get_weather` | Weather forecast |
| `manage_calendar` | Calendar events |
| `control_smart_home` | Smart devices |
| `take_note` | Create notes |
| `play_music` | Music control |
| `get_news` | News headlines |
| `calculate` | Math/conversions |
| `manage_tasks` | To-do list |

## Deployment

### Local Development
```bash
./deploy/scripts/setup-local.sh
```

### Docker
```bash
cd deploy
docker compose up -d
```

### Cloud (GPU Required)

| Platform | Command | Cost |
|----------|---------|------|
| RunPod | `./deploy/scripts/deploy-runpod.sh` | ~$0.30/hr |
| AWS | `./deploy/scripts/deploy-aws.sh` | ~$0.50/hr |
| GCP | `./deploy/scripts/deploy-gcp.sh` | ~$0.35/hr |

## Requirements

### Backend
- Python 3.10+
- NVIDIA GPU (8GB+ VRAM recommended)
- CUDA 12.1+
- 16GB+ RAM

### iOS App
- Xcode 15+
- iOS 17+
- Real device for microphone testing

## Configuration

Key environment variables:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Model Settings
DEVICE=cuda              # or cpu
WHISPER_MODEL=large-v3   # tiny, base, small, medium, large
CLAUDE_MODEL=claude-sonnet-4-20250514

# Optional
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://...
```

## Customization

### Change Jarvis's Voice

Add a reference audio clip:
```python
voice_service.set_voice(
    audio_path="custom_voice.wav",
    reference_text="Hello, I'm your assistant."
)
```

### Add New Tools

Edit `backend/agents/tools.py`:
```python
JARVIS_TOOLS.append({
    "name": "my_custom_tool",
    "description": "Does something cool",
    "input_schema": {...}
})
```

### Modify Personality

Edit `JARVIS_SYSTEM_PROMPT` in `backend/agents/jarvis_agent.py`.

## Troubleshooting

**"CUDA out of memory"**
- Use smaller Whisper model: `WHISPER_MODEL=medium`
- Reduce max audio length in config

**"Connection refused" on iOS**
- Check server is running
- Verify IP address in Settings
- Ensure firewall allows port 8000

**Slow responses**
- Enable `faster-whisper`: `USE_FASTER_WHISPER=true`
- Use GPU instance for production
- Consider streaming WebSocket endpoint

## Roadmap

- [ ] Wake word detection ("Hey Jarvis")
- [ ] Background task execution
- [ ] Voice cloning from samples
- [ ] Apple Watch companion
- [ ] HomeKit deep integration
- [ ] Multi-language support

## License

Apache 2.0 - See [LICENSE](../LICENSE)

## Credits

- [Sesame CSM](https://github.com/SesameAILabs/csm) - Conversational Speech Model
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech Recognition
- [Anthropic Claude](https://anthropic.com) - AI Intelligence
- [FastAPI](https://fastapi.tiangolo.com) - Backend Framework
