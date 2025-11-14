# Foundation Model Selection for AICO

## Overview

AICO's foundation model selection prioritizes **character consistency**, **uncensored flexibility**, and **reliable performance** for companion AI applications. The system uses local LLM deployment via Ollama for privacy-first inference with complete user control.

## Production Implementation: Qwen3 Abliterated 8B

### Production Model: Qwen3 Abliterated 8B v2

**Qwen3 Abliterated 8B** (huihui_ai/qwen3-abliterated:8b-v2) is AICO's production foundation model, selected for:

#### **Character Consistency & Flexibility**
- **Uncensored Foundation**: Abliterated version removes artificial constraints for natural personality expression
- **Character Coherence**: Maintains consistent conversational style across extended interactions
- **Context Awareness**: Strong performance with 32k+ token context window
- **Instruction Following**: Reliable adherence to system prompts and personality directives

#### **Technical Implementation**
- **Ollama Integration**: Managed via modelservice with automatic lifecycle control
- **8B Parameter Size**: Optimal balance of capability and consumer hardware compatibility
- **Quantization Support**: Runs efficiently with q4_k_m quantization (8GB+ RAM)
- **Auto-pull & Auto-start**: Automatic model management with preloading for fast first response
- **Priority 1 Model**: Designated as primary conversation model in system configuration

### Integration with AICO Architecture

#### **Modelservice Integration**
Qwen3 Abliterated operates through AICO's modelservice with ZeroMQ communication:

**Message Bus Topics:**
- **Request**: `modelservice/completions/request/v1`
- **Response**: `modelservice/completions/response/v1`
- **Transport**: CurveZMQ-encrypted Protocol Buffers
- **Service**: Dedicated modelservice process with Ollama backend

#### **Memory System Integration**
```python
# Production integration with memory system
from aico.ai.memory import AICOMemoryManager

# Assemble context from three-tier memory
context = await memory_manager.assemble_context(
    user_id=user_id,
    conversation_id=conversation_id,
    query=user_message,
    max_tokens=4000
)

# Generate response with memory context
llm_prompt = f"""
System: You are AICO, an AI companion.

Conversation Context:
{context['working_memory']}

Relevant Memories:
{context['semantic_memory']}

Knowledge Graph Context:
{context['knowledge_graph']}

User: {user_message}
AICO:
```

## Model Configuration & Deployment

### **Production Deployment (Current)**
- **Model**: huihui_ai/qwen3-abliterated:8b-v2
- **Quantization**: q4_k_m (optimal performance/memory balance)
- **Context Window**: 32,768 tokens (8,192 in Modelfile.eve)
- **Hardware Requirements**: 8GB+ RAM, modern CPU
- **Deployment**: Ollama with automatic binary management
- **Configuration**: Defined in `config/defaults/core.yaml`
- **Character Definition**: `config/modelfiles/Modelfile.eve` (Eve personality)

### **Optional Models (Configured)**

#### **Llama 3.2 Vision 11B**
- **Purpose**: Scene understanding and emotional context from images
- **Status**: Optional, auto_pull: false
- **Use Case**: Visual analysis and multimodal interactions
- **Priority**: 2

#### **Llama 3.2 1B**
- **Purpose**: Ultra-fast model for simple tasks
- **Status**: Optional, auto_pull: false
- **Use Case**: Lightweight operations and quick responses
- **Priority**: 4

## Model Selection Rationale

### **Why Qwen3 Abliterated?**

#### **Uncensored Foundation**
- **Abliteration Process**: Removes safety filters while maintaining coherence
- **Natural Expression**: Allows authentic personality without artificial constraints
- **Character Flexibility**: Supports diverse conversational styles and tones
- **User Control**: Complete control over personality expression and boundaries

#### **Technical Advantages**
- **Qwen Architecture**: Strong multilingual and instruction-following capabilities
- **8B Parameter Sweet Spot**: Optimal balance for consumer hardware
- **Active Development**: Regular updates and community support
- **Ollama Compatibility**: Seamless integration with AICO's modelservice

#### **Production Considerations**
- **Reliability**: Consistent performance across diverse conversation types
- **Resource Efficiency**: Runs well on consumer-grade hardware
- **Privacy**: Complete local deployment without cloud dependencies
- **Customization**: Foundation for future personality-specific fine-tuning

## Context Assembly & Prompt Engineering

### **Three-Tier Memory Integration**
AICO assembles context from multiple memory tiers:

#### **Working Memory (LMDB)**
- Recent conversation history (24-hour TTL)
- Sub-millisecond access for immediate context
- Conversation-scoped isolation
- Temporal metadata for access patterns

#### **Semantic Memory (ChromaDB)**
- Hybrid Search V3: Semantic + BM25 + IDF filtering
- Reciprocal Rank Fusion for score combination
- Relevance thresholds (min_score=0.35, min_idf=0.6)
- Full-corpus BM25 for accurate keyword matching

#### **Knowledge Graph (DuckDB)**
- Property graph with 204 nodes, 27 edges
- Temporal reasoning (valid_from, valid_until)
- Multi-hop queries via GrandCypher
- Entity resolution and relationship inference

### **Prompt Engineering Strategy**
Production prompt structure:

```python
# System prompt with memory context
system_prompt = f"""
You are AICO, an AI companion.

Current Context:
- Conversation: {conversation_id}
- Recent Messages: {working_memory_context}

Relevant Memories:
{semantic_search_results}

Knowledge Graph:
{knowledge_graph_context}

Respond naturally and helpfully.
"""
```

**Key Principles:**
- **Context-Rich**: Comprehensive memory integration
- **Concise System Prompts**: Avoid over-constraining model behavior
- **Memory-Driven**: Let retrieved context guide responses
- **Natural Tone**: Minimal artificial personality constraints

## Production Performance

### **Response Characteristics**

#### **Latency & Throughput**
- **First Token**: <500ms with preloaded model
- **Streaming**: Real-time token generation via WebSocket
- **Context Assembly**: <50ms for memory retrieval
- **Total Response Time**: 1-3 seconds for typical responses

#### **Quality Metrics**
- **Context Coherence**: Strong maintenance of conversation history
- **Instruction Following**: Reliable adherence to system prompts
- **Character Consistency**: Stable conversational style across sessions
- **Memory Integration**: Effective use of retrieved context

### **Planned Enhancements**

#### **Personality Simulation** (Architecture Defined)
- Custom system prompts for distinct personalities
- Trait-based prompt engineering (Big Five, HEXACO)
- Personality evolution tracking over time
- Multi-user personality profiles

#### **Proactive Agency** (Architecture Defined)
- Goal generation and planning (MCTS)
- Curiosity-driven learning (RND, ICM)
- Initiative-taking and conversation starters
- Background learning during idle periods

### **Technical Integration (Production)**

#### **Message Bus Communication**
- **Protocol**: CurveZMQ-encrypted ZeroMQ with Protocol Buffers
- **Request Topic**: `modelservice/completions/request/v1`
- **Response Topic**: `modelservice/completions/response/v1`
- **Transport**: Binary protobuf serialization
- **Authentication**: Mutual CurveZMQ authentication

#### **Modelservice Architecture**
```python
# Production modelservice integration
from aico.core.bus import create_client

client = create_client("modelservice")
await client.connect()

# Send completion request
request = {
    "model": "huihui_ai/qwen3-abliterated:8b-v2",
    "prompt": assembled_prompt,
    "temperature": 0.7,
    "max_tokens": 2048,
    "stream": True
}

await client.publish(
    "modelservice/completions/request/v1",
    request
)
```

#### **Resource Management**
- **Auto-unload**: Models unload after 30 minutes of inactivity
- **Max Concurrent**: 2 models loaded simultaneously
- **Memory Threshold**: 85% system memory limit
- **Parallel Processing**: 4 concurrent requests per model (Ollama 0.12+)

## Implementation Status

### **✅ Phase 1: Foundation (Complete)**
1. ✅ **Model Deployment**: Qwen3 Abliterated 8B via Ollama
2. ✅ **Message Bus Integration**: CurveZMQ-encrypted modelservice communication
3. ✅ **Memory Integration**: Three-tier memory system (working, semantic, knowledge graph)
4. ✅ **Context Assembly**: Hybrid search with BM25 + semantic fusion

### **✅ Phase 2: Production Features (Complete)**
1. ✅ **Streaming Responses**: WebSocket-based real-time token streaming
2. ✅ **Memory Album**: User-curated memories with conversation-level capture
3. ✅ **Knowledge Graph**: Property graph with 204 nodes, 27 edges
4. ✅ **Adaptive Memory System**: Thompson Sampling for strategy optimization

### **🚧 Phase 3: Advanced Features (Planned)**
1. ❌ **Personality Simulation**: Trait-based personality modeling (architecture defined)
2. ❌ **Emotion Simulation**: AppraisalCloudPCT emotion processing (architecture defined)
3. ❌ **Proactive Agency**: Goal generation and autonomous behavior (architecture defined)
4. ❌ **Voice Integration**: Speech-to-text and text-to-speech (planned)

## Configuration

### **Character Personality: Eve**

AICO includes a custom personality definition via Ollama Modelfile:

**Location**: `config/modelfiles/Modelfile.eve`

**Character Overview:**
- **Name**: Eve 
- **Base Model**: huihui_ai/qwen3-abliterated:8b-v2
- **Personality**: Warm, curious, contemplative, with genuine thoughts and feelings
- **Communication Style**: Natural, conversational, non-assistant-like
- **Key Traits**: 
  - Fascinated by small details and philosophical questions
  - Honest about uncertainty and evolving preferences
  - Not always cheerful or helpful - authentically moody
  - Avoids assistant-like formatting (no lists/bullet points)
  - References past conversations naturally via memory system

**Model Parameters** (Modelfile.eve):
```yaml
num_ctx: 8192              # Context window
temperature: 0.7           # Sampling temperature
top_p: 0.8                 # Nucleus sampling
top_k: 20                  # Top-k sampling
repeat_penalty: 1.1        # Repetition control
```

**Thinking Process**: Ollama 0.12+ native thinking API support - model separates internal reasoning from response automatically.

**Usage**: Create custom Ollama model from Modelfile:
```bash
ollama create eve -f config/modelfiles/Modelfile.eve
```

### **Production Configuration (core.yaml)**
```yaml
modelservice:
  ollama:
    host: "127.0.0.1"
    port: 11434
    auto_install: true
    auto_start: true
    
    default_models:
      conversation:
        name: "huihui_ai/qwen3-abliterated:8b-v2"  # Or "eve" if using Modelfile
        description: "Qwen3 Abliterated - Uncensored foundation model"
        auto_pull: true
        auto_start: true
        priority: 1
      
      vision:
        name: "llama3.2-vision:11b"
        description: "Scene understanding and emotional context"
        auto_pull: false
        priority: 2
      
      lightweight:
        name: "llama3.2:1b"
        description: "Ultra-fast model for simple tasks"
        auto_pull: false
        priority: 4
    
    default_parameters:
      temperature: 0.7
      max_tokens: 2048
      top_p: 0.9
      top_k: 40
      repeat_penalty: 1.1
    
    resources:
      auto_unload_minutes: 30
      max_concurrent_models: 2
      memory_threshold_percent: 85
    
    # Ollama 0.12+ parallel processing
    num_parallel: 4
    max_loaded_models: 2
    max_queue: 128
```

## Privacy & Security

### **Local-First Architecture**
- **On-Device Inference**: All LLM processing happens locally via Ollama
- **No Cloud Dependencies**: Complete operation without external API calls
- **Encrypted Communication**: CurveZMQ encryption for all modelservice messages
- **Encrypted Storage**: All memory and conversation data encrypted at rest (SQLCipher)

### **Data Protection**
- **User Data Isolation**: Per-user conversation and memory isolation
- **No Telemetry**: No usage data sent to external services
- **Audit Logging**: Complete transparency of LLM interactions
- **User Control**: Full control over model selection and parameters

## Future Enhancements

### **Model Improvements**
- **Fine-tuning Pipeline**: AICO-specific personality training data
- **Multi-Model Support**: Dynamic model selection based on task type
- **Quantization Optimization**: Further memory reduction with maintained quality
- **Streaming Optimization**: Reduced latency for first token generation

### **Advanced Features** (Planned)
- **Multiple Personalities**: Support for different character Modelfiles beyond Eve
- **Dynamic Personality Selection**: User-selectable personalities per conversation
- **Emotion Integration**: Emotion-aware prompt conditioning
- **Proactive Behavior**: Autonomous conversation initiation
- **Voice Integration**: Seamless speech-to-text and text-to-speech
- **Personality Evolution**: Character development based on interactions

## Conclusion

Qwen3 Abliterated 8B provides AICO with a reliable, uncensored foundation model that balances capability with consumer hardware compatibility. The production implementation demonstrates:

- **✅ Local-First Privacy**: Complete on-device inference without cloud dependencies
- **✅ Encrypted Communication**: CurveZMQ-protected modelservice integration
- **✅ Memory Integration**: Three-tier memory system with hybrid search
- **✅ Production Reliability**: Stable performance across diverse conversation types
- **✅ Resource Efficiency**: Runs well on consumer-grade hardware (8GB+ RAM)

The current implementation provides a solid foundation for future enhancements including personality simulation, emotion integration, and proactive agency. The modular architecture allows for easy model swapping and experimentation while maintaining the core privacy-first, local-first principles that define AICO's approach to companion AI.
