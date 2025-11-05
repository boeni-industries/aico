# AICO Memory System

The AICO memory system is the foundation of the AI companion's ability to maintain context, build relationships, and provide personalized interactions. It implements a three-tier memory architecture that enables natural conversation flow, explicit conversation management, and long-term relationship building.

## Overview

AICO's memory system goes beyond simple conversation history to create a comprehensive understanding of users, relationships, and interaction patterns. It serves as the core intelligence that enables:

- **Natural Conversation Flow**: Seamless context switching and thread management
- **Relationship Building**: Long-term memory of user preferences, patterns, and shared experiences  
- **Personalized Interactions**: Adaptive responses based on learned user behavior
- **Proactive Engagement**: Initiative generation based on conversation history and patterns

## Architecture Components

The memory system consists of three tiers (two implemented, one planned):

### 1. Working Memory (LMDB) ✅ IMPLEMENTED
Conversation history and immediate context management.
- All conversation messages scoped by `conversation_id`
- 24-hour TTL with automatic expiration
- Fast key-value storage (memory-mapped)
- Sub-millisecond retrieval performance
- **Dual Role**: Serves both immediate context AND conversation history (no separate episodic tier needed)

### 2. Semantic Memory + Knowledge Graph ✅ IMPLEMENTED
Long-term knowledge storage with semantic search and graph relationships.

**Conversation Segments (ChromaDB):**
- **Hybrid Search**: Combines semantic similarity with keyword matching (BM25)
- **IDF Filtering**: Removes overly common words for precise results
- **Relevance Thresholds**: Filters out irrelevant matches automatically
- Stores conversation chunks with embeddings for retrieval

**Knowledge Graph (ChromaDB + libSQL):**
- **Entity Extraction**: Multi-pass extraction with GLiNER + LLM
- **Entity Resolution**: 3-step deduplication (blocking → matching → merging)
- **Graph Fusion**: Conflict resolution and temporal updates
- **Structured Storage**: Nodes (entities) and edges (relationships) with properties
- **Production Data**: 204 nodes, 27 edges, 552 indexed properties

### 3. Procedural Memory (libSQL) 🔄 PLANNED
User interaction patterns and behavioral adaptation.
- **Pattern Learning**: Track response preferences, topic interests, engagement signals
- **Adaptive Personalization**: Adjust response style based on learned patterns
- **Conversation Quality**: Metrics on what works and what doesn't
- **Time-Aware**: Context-aware behavior based on time of day, conversation history

## Key Features

### Local-First Architecture
- **No External Dependencies**: All memory processing happens locally
- **Embedded Databases**: Uses libSQL and ChromaDB for persistence
- **Privacy-First**: All personal data remains on user's device
- **Offline Capable**: Full functionality without internet connection

### Conversation-Scoped Memory
- **Explicit Conversation IDs**: User-driven conversation selection via UI
- **Isolated Contexts**: Each conversation has independent memory scope
- **Cross-Conversation Knowledge**: Knowledge graph accumulates facts across all conversations
- **Context Preservation**: Working memory maintains session state per conversation

### Performance Optimized
- **Hardware Efficient**: Designed for consumer-grade hardware
- **Adaptive Resource Usage**: Scales performance based on available resources
- **Lazy Loading**: Loads context only when needed
- **Configurable Depth**: User-adjustable memory detail vs. performance trade-offs

## Implementation Location

The memory system is implemented as a shared AI module at `shared/aico/ai/memory/`, making it accessible across AICO's architecture while maintaining modularity and following established patterns. This location enables:

- **Cross-component access**: Backend modules, CLI tools, and other AI components can import and use memory functionality
- **Consistent patterns**: Follows AICO's established shared library structure for AI capabilities
- **Message bus integration**: Seamless integration with AICO's message-driven architecture
- **Frontend integration**: Flutter frontend accesses memory through REST API endpoints, maintaining separation of concerns

## Implementation Status

### ✅ Phase 1: Session Context Management (COMPLETE)
- Working memory with LMDB storage
- Conversation-scoped context retrieval
- Context assembly with relevance scoring
- Message history with automatic expiration

### ✅ Phase 2: Semantic Memory & Knowledge Graph (COMPLETE)
- Hybrid search (semantic + BM25 with IDF filtering)
- Multi-pass entity extraction (GLiNER + LLM)
- Entity resolution with deduplication
- Graph fusion with conflict resolution
- Production deployment: 204 nodes, 27 edges

### ❌ Phase 3: Behavioral Learning (NOT IMPLEMENTED)
- User pattern recognition
- Adaptive personalization
- Procedural memory store

### ❌ Phase 4: Proactive Engagement (NOT IMPLEMENTED)
- Predictive triggers
- Initiative generation
- Advanced relationship modeling

## Documentation Structure

This memory system documentation is organized into focused areas:

- **[Architecture](architecture.md)**: Detailed technical architecture and component design
- **[Hybrid Search](hybrid-search.md)**: **NEW** - Semantic + BM25 search implementation (V3)
- **[Context Management](context-management.md)**: Context assembly, routing, and optimization
- **[Implementation](implementation.md)**: Practical implementation guide and database schemas

## Integration Points

The memory system integrates with all major AICO components:

- **Conversation Engine**: Provides context for response generation
- **Personality System**: Informs trait expression and behavioral consistency
- **Emotion System**: Stores and retrieves emotional context
- **Agency System**: Drives proactive engagement and goal formation
- **Relationship Intelligence**: Enables natural family member recognition

This memory system represents the cognitive foundation that transforms AICO from a simple chatbot into a genuine AI companion capable of building meaningful, long-term relationships.
