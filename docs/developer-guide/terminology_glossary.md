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

## Migration Strategy

### Phase 3: Code Implementation - Dry Run Analysis

**SCOPE**: Replace "chat" terminology with "conversation" throughout codebase (IN PROGRESS)

**FILES TO UPDATE (38 files total)**:

**Backend/API Files**:
- `backend/api/logs/dependencies.py` - Update comment references
- `backend/api/logs/schemas.py` - Update schema field descriptions

**CLI Files**:
- `cli/commands/ollama.py` - Update command descriptions (2 matches)
- `cli/commands/security.py` - Update help text
- `cli/utils/zmq_client.py` - Update class/method names (2 matches)

**Configuration Files**:
- `config/defaults/security.yaml` - Update configuration comments (2 matches)

**Documentation Files (25 files)** - ✅ COMPLETED:
- ✅ `docs/architecture/api_reference.md` - Update API endpoint descriptions
- ✅ `docs/architecture/architecture_overview.md` - Update component references (4 matches)
- ✅ `docs/architecture/configuration_management.md` - Update config descriptions (2 matches)
- ✅ `docs/architecture/emotion_sim_msg.md` - Update message descriptions
- ✅ `docs/architecture/integration_msg.md` - Update integration patterns (4 matches)
- ✅ `docs/architecture/personality_sim.md` - Update component references
- ✅ `docs/architecture/personality_sim_msg.md` - Update message patterns
- ✅ `docs/concepts/llm/foundation_model.md` - Update LLM integration descriptions
- ✅ `docs/concepts/llm/multimodality.md` - Update multimodal processing
- ✅ `docs/developer-guide/guidelines.md` - Update development guidelines
- ✅ `docs/developer-guide/protobuf.md` - Update protobuf message descriptions
- ✅ `docs/flow/conversation_e2e.md` - Update flow descriptions
- ✅ `docs/frontend/component_library.md` - Update UI component names (2 matches)
- ✅ `docs/frontend/design_principles.md` - Update design terminology
- ✅ `docs/frontend/frontend_architecture_overview.md` - Update architecture (4 matches)
- ✅ `docs/frontend/navigation.md` - Update navigation labels
- ✅ `docs/frontend/state_management.md` - Update state descriptions
- ✅ `docs/frontend/testing_strategy.md` - Update test descriptions (3 matches)
- ✅ `docs/instrumentation/instrumentation_logging.md` - Update logging patterns (5 matches)
- ✅ `docs/roadmap/mvp.md` - Update MVP descriptions (4 matches)
- ✅ `docs/welcome.md` - Update welcome content
- ✅ `mkdocs.yml` - Update navigation labels

**Modelservice Files**:
- `modelservice/core/protobuf_messages.py` - Update class/method names (7 matches)
- `modelservice/core/zmq_handlers.py` - Update handler descriptions (2 matches)

**Protocol Buffer Files**:
- `proto/aico_integration.proto` - Update message definitions (5 matches)
- `proto/aico_modelservice.proto` - Update service definitions (6 matches)

**Scripts**:
- `scripts/completions_simplified_test.py` - Update variable/function names (3 matches)
- `scripts/howto_completions_zmq.py` - Update variable/function names (3 matches)

**Shared/Generated Files**:
- `shared/aico/core/topics.py` - Update topic descriptions
- `shared/aico/proto/aico_integration_pb2.py` - Update generated comments (3 matches)
- `shared/aico/proto/aico_modelservice_pb2.py` - Update generated comments (3 matches)

**CHANGE CATEGORIES**:
1. **Class/Interface Names**: ChatRepository → ConversationRepository, ChatEngine → ConversationEngine
2. **Function/Method Names**: handle_chat → handle_conversation, chat_completion → conversation_completion
3. **Variable Names**: chat_context → conversation_context, chat_history → conversation_history
4. **API Endpoints**: /chat/ → /conversation/, chat-related → conversation-related
5. **Configuration Keys**: chat_* → conversation_*
6. **Documentation**: All "chat" references → "conversation" where appropriate
7. **Comments/Docstrings**: Update terminology throughout
8. **Protocol Buffers**: Message field names and service definitions
9. **Topic Names**: Already completed in Phase 2

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
