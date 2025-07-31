---
title: Technology Stack
---

# Technology Stack

This document centralizes all technology decisions for the AICO system. It provides a comprehensive overview of the technologies selected for each layer of the architecture.

## Interface Layer

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Flutter** | Cross-platform UI framework | Single codebase for desktop/mobile, high performance, rich widget library |
| **WebView** | 3D avatar rendering | Embeds web-based avatar technologies within Flutter |
| **Three.js** | 3D graphics library | Industry standard for web-based 3D rendering |
| **Ready Player Me** | Avatar creation | Customizable avatars with built-in animation support |
| **TalkingHead.js** | Lip-sync and expressions | Real-time lip-sync and facial expression capabilities |
| **JavaScript Bridge** | Flutter-WebView communication | Bidirectional communication between Flutter and web avatar |

## AI/ML Layer

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Llama.cpp** | Local LLM inference | Efficient quantized models, cross-platform support |
| **Ollama** | LLM management | Simplified model management and API |
| **Mistral** | Base LLM architecture | Strong performance in quantized form |
| **LangChain/LangGraph** | Agent orchestration | Graph-based workflow for complex agent behaviors |
| **CrewAI/Autogen** | Multi-agent coordination | Enables collaborative agent behaviors |
| **RND** | Curiosity algorithm | Random Network Distillation for intrinsic motivation |
| **ICM** | Curiosity algorithm | Intrinsic Curiosity Module for prediction-based rewards |
| **HER** | Goal-conditioned learning | Hindsight Experience Replay for learning from failures |
| **GCPO** | Goal-conditioned learning | Goal-Conditioned Policy Optimization for on-policy learning |
| **MCTS** | Planning system | Monte Carlo Tree Search for decision making |
| **Behavior Trees** | Action modeling | Goal-oriented behavior modeling and execution |
| **AppraisalCloudPCT** | Emotion simulation | Component Process Model for sophisticated emotion generation |
| **ONNX Runtime** | Model inference | Cross-platform inference optimization |
| **OpenVINO** | Edge inference | Intel optimization for edge devices |
| **Whisper.cpp** | Speech-to-text | Efficient local speech recognition |
| **Coqui/Piper** | Text-to-speech | Local high-quality voice synthesis |

## Data & Storage Layer

AICO employs a specialized multi-database architecture optimized for local-first operation. See [Data Layer](data_layer.md) for comprehensive details.

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **libSQL** | Primary storage | Modern SQLite fork with encryption, improved concurrency, and vector extensions |
| **DuckDB** | Analytical engine | Columnar storage for efficient OLAP workloads and complex analytics |
| **ChromaDB** | Vector database | Embedded vector storage with document metadata and similarity search |
| **RocksDB** | Key-value store (optional) | Ultra-fast access for performance-critical paths and caching |
| **Sentence Transformers** | Embedding generation | Efficient text embedding models for semantic understanding |
| **P2P Sync Protocol** | Federated device sync | Custom protocol for secure device-to-device synchronization |

## Communication Layer

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **ZeroMQ** | Internal message bus | Lightweight, embedded pub/sub messaging for all core modules |
| **FastAPI** | API framework | Modern, fast Python web framework powering the service gateway |
| **REST API** | UI/adapter protocol | Standard HTTP API for commands, queries, and configuration |
| **WebSocket API** | UI/adapter protocol | Real-time, bidirectional communication for events and notifications |
| **JSON** | Message format | Human-readable, widely supported serialization |
| **JSON Schema** | Message validation | Schema validation for message formats |

## Security & Privacy Layer

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **libSQL Encryption** | Database encryption | Built-in encryption for primary storage |
| **AES-256** | Data encryption | Industry standard encryption |
| **Homomorphic Encryption** | Privacy-preserving computation | Compute on encrypted data |
| **Differential Privacy** | Statistical privacy | Privacy-preserving analytics |
| **Zero-Knowledge Proofs** | Authentication | Verify without revealing data |
| **Secure Multi-party Computation** | Collaborative learning | Learn without sharing raw data |

## Deployment & Distribution Layer

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Docker/Podman** | Containerization | Isolated, reproducible environments |
| **Alpine Linux** | Base images | Minimal footprint for containers |
| **Electron** | Desktop packaging | Cross-platform desktop application packaging |
| **Delta Updates** | Efficient updates | Bandwidth-efficient update mechanism |
| **Cryptographic Signatures** | Update verification | Ensures update authenticity |

## Development & Testing Layer

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Python** | Core development | Primary language for AI components |
| **Dart/Flutter** | UI development | Cross-platform UI framework |
| **JavaScript/TypeScript** | Avatar development | Web technologies for avatar system |
| **Pytest** | Testing framework | Comprehensive Python testing |
| **GitHub Actions** | CI/CD | Automated testing and deployment |
| **MkDocs** | Documentation | Markdown-based documentation system |
| **Material for MkDocs** | Documentation theme | Clean, responsive documentation UI |

## Module-Specific Technologies

### Personality Simulation

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **TraitEmergence** | Personality architecture | Multi-dimensional trait-based modeling |
| **Big Five & HEXACO** | Trait models | Comprehensive personality representation |

### Emotion Simulation

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **AppraisalCloudPCT** | Emotion architecture | Advanced Component Process Model variant |
| **4-Stage Appraisal** | Emotion generation | Cognitive appraisal process (Relevance → Implication → Coping → Normative) |

### Autonomous Agency

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **MCTS** | Decision making | Monte Carlo Tree Search for planning |
| **Behavior Trees** | Action execution | Structured behavior representation |
| **RND/ICM** | Curiosity algorithms | Intrinsic motivation for exploration |
| **HER/GCPO** | Goal learning | Goal-conditioned reinforcement learning |

### Avatar System

| Technology | Purpose | Justification |
|------------|---------|---------------|
| **Three.js** | 3D rendering | Web-based 3D graphics |
| **Ready Player Me** | Avatar models | Customizable 3D avatars |
| **TalkingHead.js** | Facial animation | Real-time lip-sync and expressions |
| **WebView** | Integration | Embedding web technologies in Flutter |
