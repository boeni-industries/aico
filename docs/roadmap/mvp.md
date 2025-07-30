# MVP Roadmap

**Goal**: Basic companion that talks, remembers, and initiates.

## Essential Components

- **Text chat interface** - Flutter + simple web UI
- **Local LLM integration** - Ollama or similar local model
- **Basic memory** - Conversations + user facts in local storage
- **Simple goal system** - Check-ins, suggestions, basic prompts
- **Personality traits** - 3-5 core dimensions (openness, warmth, curiosity)

## Validation Criteria

- Remembers user preferences across sessions
- Initiates conversations without prompting
- Shows consistent personality responses
- Works completely offline
- Responds within 3-5 seconds

## Technical Stack

- **Frontend**: Flutter for cross-platform UI
- **Backend**: Python with FastAPI for core services
- **LLM**: Local Ollama instance (Llama 2 or similar)
- **Storage**: SQLite for memory, JSON for personality config
- **Message Bus**: Redis pub/sub or simple Python messaging

## Success Definition

User can have a 10-minute conversation where AICO:
1. Remembers something from earlier in the conversation
2. Asks a follow-up question unprompted
3. Shows personality consistency
4. Makes a relevant suggestion based on context
