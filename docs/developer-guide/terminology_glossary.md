# AICO Terminology Glossary

## Core Conversation & Communication Terms

### Input & Processing
- **User Input**: Raw input from user (text, voice, image, multimodal)
- **User Message**: Processed, structured user input ready for system processing
- **Request**: API-level HTTP/WebSocket request from frontend to backend
- **Query**: Specific information request or question within user input

### Conversation Flow
- **Conversation**: Complete ongoing relationship/communication context between user and AICO
- **Session**: Technical connection/authentication period (may span multiple conversations)
- **Thread**: Logical grouping of related exchanges within a conversation
- **Turn**: One side of communication - either user speaks OR AICO responds
- **Exchange**: Complete back-and-forth unit (user turn + AICO turn)
- **Interaction**: General term for any user-AICO communication event

### System Components
- **Conversation Engine**: Core orchestration component responsible for conversation flow, context integration, multimodal processing, emotion/personality coordination, and response generation
- **Conversation Manager**: Handles conversation state, thread management, and context switching
- **Response Generator**: LLM-based component that produces AICO's textual responses
- **Input Processor**: Component that handles and routes different types of user input

### Response & Output
- **Response**: AICO's reply to user input (text, voice, multimodal)
- **Reaction**: AICO's behavioral/emotional response (separate from textual response)

### Context & Memory
- **Context**: Current situational information influencing conversation
- **Conversation Context**: Historical and current state of ongoing conversation
- **User Context**: Information about user's current situation, mood, preferences
- **Thread Context**: Specific context within a conversation thread
- **Memory**: Persistent information stored about conversations and user

### Message Bus Topics (Standardized)
- **Input Topics**: `user/input/{type}` (text, voice, multimodal)
- **Conversation Topics**: `conversation/{action}` (start, message, response, end)
- **Context Topics**: `context/{type}` (user, emotional, social, personality)
- **Response Topics**: `response/{stage}` (generated, enhanced, delivered)

## Usage Guidelines

### When to Use Each Term

**Conversation vs Chat**:
- Use "conversation" for the broader, ongoing relationship context
- Use "chat" only when referring to the UI component or casual text-based interaction
- Component name: "Conversation Engine" (reflects full orchestration capabilities)

**Input vs Message vs Request**:
- "User Input": Raw data from user interface
- "User Message": Structured, processed input ready for system handling  
- "Request": Technical API/HTTP layer communication
- "Query": When user is asking for specific information

**Session vs Thread vs Turn vs Exchange**:
- "Session": Technical authentication/connection period
- "Thread": Logical conversation grouping (like email threads)
- "Turn": One person speaking (user says something OR AICO responds)
- "Exchange": Complete conversation unit (user turn + AICO turn = full back-and-forth)

**Response vs Reaction**:
- "Response": Primary term for AICO's reply to user
- "Reaction": Behavioral/emotional response separate from text

### Message Bus Topic Patterns

**Standard Format**: `{domain}/{action}/{type}`

**Examples**:
```
user/input/text
user/input/voice  
user/input/multimodal
conversation/message/received
conversation/response/generated
conversation/context/updated
context/emotional/current
context/personality/expression
response/enhanced/ready
```

## Migration Strategy

### Phase 1: Core Documentation
- Update architecture docs to use standardized terms
- Revise conversation flow documentation
- Update API documentation with consistent terminology

### Phase 2: Message Bus Topics  
- Standardize all topic names following new patterns
- Update all publishers and subscribers
- Maintain backward compatibility during transition

### Phase 3: Code Implementation
- Update component names and interfaces
- Revise function and variable names
- Update comments and docstrings

### Phase 4: User-Facing Content
- Update UI labels and help text
- Revise user documentation
- Update CLI command descriptions

## Consistency Rules

1. **Component Names**: Use "Conversation Engine" (reflects full orchestration capabilities)
2. **API Endpoints**: Use "conversation" for user-facing endpoints (`/api/v1/conversation/`)
3. **Message Topics**: Follow domain/action/type pattern consistently
4. **Documentation**: Use full terms on first reference, abbreviations sparingly
5. **Code**: Prefer explicit terms over abbreviations (conversation_context vs conv_ctx)

## Terms to Avoid

- **Deprecated**: "chat" when referring to the overall conversation system
- **Ambiguous**: "interaction" without qualifier (specify type)
- **Technical**: "request" when referring to user input (use "user input" or "user message")
- **Inconsistent**: Mixed topic patterns (stick to domain/action/type)

## Cross-Reference

### Related Components
- **Memory System**: Stores conversation history and context
- **Emotion Simulation**: Provides emotional context for conversations  
- **Personality Simulation**: Influences conversation style and responses
- **Avatar System**: Provides visual embodiment during conversations
- **Voice System**: Handles speech-to-text and text-to-speech for conversations

### External Integrations
- **LLM Integration**: Powers response generation in Conversation Engine
- **Multimodal Processing**: Handles image/video input in conversations
- **Plugin System**: Extends conversation capabilities
