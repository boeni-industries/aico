# AICO Terminology Glossary

## Core Terms

### Communication
- **User Input**: Raw input (text, voice, image, multimodal)
- **User Message**: Processed, structured input ready for system processing
- **Request**: API-level HTTP/WebSocket request from frontend to backend
- **Query**: Specific information request within user input
- **Conversation**: Complete ongoing relationship/communication context
- **Session**: Technical connection/authentication period
- **Thread**: Logical grouping of related exchanges
- **Turn**: One side of communication (user OR AICO)
- **Exchange**: Complete back-and-forth (user turn + AICO turn)
- **Response**: AICO's reply (text, voice, multimodal)
- **Reaction**: AICO's behavioral/emotional response

### System Components
- **Conversation Engine**: Core orchestration for conversation flow, context integration, multimodal processing
- **Conversation Manager**: Handles conversation state, thread management, context switching
- **Response Generator**: LLM-based component producing textual responses
- **Input Processor**: Handles and routes different input types

### Context & Memory
- **Context**: Current situational information influencing conversation
- **Conversation Context**: Historical and current conversation state
- **User Context**: User's situation, mood, preferences
- **Thread Context**: Specific context within conversation thread
- **Memory**: Persistent conversation and user information

### Message Bus Topics
- **Input**: `user/input/{type}` (text, voice, multimodal)
- **Conversation**: `conversation/{action}` (start, message, response, end)
- **Context**: `context/{type}` (user, emotional, social, personality)
- **Response**: `response/{stage}` (generated, enhanced, delivered)

## Usage Guidelines

### When to Use Each Term

**Conversation vs Chat**:
- Use "conversation" for the broader, ongoing relationship context
- Use "chat" only when referring to legacy UI components or casual text-based interaction
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

## Consistency Rules

1. **Component Names**: Use "Conversation Engine" (reflects full orchestration capabilities)
2. **API Endpoints**: Use "conversation" for user-facing endpoints (`/api/v1/conversation/`)
3. **Message Topics**: Follow domain/action/type pattern consistently
4. **Documentation**: Use full terms on first reference, abbreviations sparingly
5. **Code**: Prefer explicit terms over abbreviations (conversation_context vs conv_ctx)

## Terms to Avoid

- **Deprecated**: "chat" when referring to the overall conversation system (use "conversation" instead)
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
