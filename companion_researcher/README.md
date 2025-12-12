# Companion Researcher

An AI-powered research companion with configurable personalities, built on top of the CSM (Conversational Speech Model).

## Features

- **Natural Conversation**: Chat naturally with your companion - it auto-detects when you're asking for research
- **Research Engine**: Automated web research with source retrieval, synthesis, and citations
- **Personality Profiles**: Hot-swap between different personalities (Coach, Researcher, Producer, Therapist-ish)
- **Voice Output**: Generate speech responses using the CSM model
- **Session Memory**: Track conversation history and research across sessions
- **Control Panel**: Fine-tune personality settings with sliders and toggles

## Architecture

```
companion_researcher/
├── backend/
│   ├── api/           # FastAPI routes and endpoints
│   ├── core/          # Voice engine and storage
│   ├── engines/       # Personality, Research, Synthesis, Intent engines
│   ├── models/        # Pydantic schemas
│   └── config/        # Settings and configuration
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── hooks/       # Custom React hooks
│   │   ├── services/    # API client
│   │   └── styles/      # CSS styles
│   └── public/
└── data/
    ├── personalities/   # JSON personality profiles
    ├── sessions/        # Stored conversation sessions
    └── vector_db/       # ChromaDB vector storage
```

## Quick Start

### Backend

```bash
# Install dependencies
cd companion_researcher
pip install -r requirements.txt

# Copy environment file and add your API keys
cp .env.example .env

# Run the server
python -m uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 to use the app.

## API Endpoints

### Chat
- `POST /api/chat` - Send a message (auto-detects research vs casual)
- `WS /api/chat/ws` - WebSocket for real-time chat

### Research
- `POST /api/research` - Execute direct research query
- `GET /api/research/{task_id}` - Get research result

### Personalities
- `GET /api/personalities` - List all personalities
- `POST /api/personalities` - Create new personality
- `PUT /api/personalities/{id}` - Update personality
- `POST /api/personalities/{id}/activate` - Set active personality

### Sessions
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/{id}` - Get session with messages
- `DELETE /api/sessions/{id}` - Delete session

### Voice
- `POST /api/voice/generate` - Generate speech audio

## Personality Configuration

Personalities are stored as JSON files in `data/personalities/`. Example:

```json
{
  "id": "researcher",
  "name": "Deep Researcher",
  "description": "A thorough, academic-focused research assistant",
  "system_prompt": "You are a meticulous research assistant...",
  "settings": {
    "tone": "serious",
    "tone_scale": 25,
    "depth": "high",
    "depth_scale": 85,
    "verbosity": "detailed"
  },
  "guardrails": {
    "always_cite_sources": true,
    "show_confidence": true
  },
  "research_preferences": {
    "preferred_source_types": ["academic", "documentation"],
    "default_depth": "deep"
  }
}
```

## Data Flow

1. **User Input** → Intent Parser determines if research or casual chat
2. **Research Path**: Task Planner → Research Engine → Synthesis → Personality styling
3. **Casual Path**: Direct to personality-styled response
4. **Voice Output**: Optional CSM speech synthesis

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `TAVILY_API_KEY` | Tavily search API key | - |
| `SERPAPI_KEY` | SerpAPI key for web search | - |
| `DEBUG` | Enable debug mode | true |
| `PORT` | Server port | 8000 |

## Development

### Running Tests
```bash
pytest
```

### Code Style
```bash
ruff check .
ruff format .
```

## Roadmap to v3 (Full OS)

1. **v1** (Current): Research companion with personalities
2. **v2**: Multi-modal input (voice input, image analysis)
3. **v3**: Full assistant OS with:
   - Proactive notifications
   - Calendar/task integration
   - Plugin system
   - Mobile app

## License

Apache 2.0 - See LICENSE file
