# Social Relationship Modeling Architecture

## Overview

AICO employs a modern hybrid vector-graph architecture for social relationship modeling that combines the semantic richness of vector embeddings with the structural reasoning capabilities of graph neural networks. This approach enables dynamic, nuanced understanding of social relationships through learned behavioral patterns rather than static relationship categories, while maintaining AICO's privacy-first principles.

## Architecture Principles

### **1. Dynamic Learning Over Static Ontologies**
- Relationships are learned from actual interactions rather than predefined categories
- Multi-dimensional relationship vectors capture nuanced social dynamics
- Adaptive system that evolves with changing social contexts

### **2. Privacy-First Local Processing**
- All relationship modeling happens on-device using local vector databases
- No social graph data transmitted to external services
- User maintains complete control over relationship data

### **3. Multi-Modal Relationship Understanding**
- Integrates conversation patterns, interaction frequency, and behavioral cues
- Temporal relationship evolution tracking
- Context-aware relationship interpretation

## Core Components

### **Vector Embedding System**

#### **Relationship Embeddings**
Each relationship is represented as a high-dimensional vector capturing:

- **Authority Dimension** (0.0-1.0): Peer-level to hierarchical relationships
- **Intimacy Dimension** (0.0-1.0): Formal/professional to personal/intimate
- **Care Responsibility** (0.0-1.0): No responsibility to primary caregiver
- **Interaction Frequency**: Learned from conversation patterns and engagement
- **Context Similarity**: Shared activities, interests, and communication topics
- **Temporal Stability**: How consistent the relationship has been over time

#### **User Behavioral Embeddings**
Each user profile includes learned vectors for:

- **Communication Style**: Formal, casual, technical, emotional patterns
- **Social Role Patterns**: Leadership, support, learning, mentoring tendencies
- **Interaction Preferences**: Group vs. individual, proactive vs. reactive
- **Context Adaptability**: How behavior changes across different social contexts

### **Graph Neural Network Layer**

#### **Relationship Graph Structure**
- **Nodes**: Individual users with their behavioral embeddings
- **Edges**: Relationship vectors between users
- **Subgraphs**: Contextual groupings (household, work team, friend group)

#### **Dynamic Inference Capabilities**
- **Multi-hop Reasoning**: Understanding indirect relationships (friend-of-friend)
- **Community Detection**: Identifying social clusters and group dynamics
- **Influence Propagation**: How information and emotions flow through the social graph
- **Relationship Strength Prediction**: Estimating bond strength from interaction patterns

### **Integration with AICO's AI Systems**

#### **Personality Engine Integration**
- Relationship context influences personality expression
- Different communication styles for different relationship types
- Consistent personality across relationships while adapting appropriateness

#### **Emotion Simulation Enhancement**
- Relationship-aware emotional responses
- Social appropriateness filtering based on relationship context
- Empathy calibration based on relationship intimacy levels

#### **Autonomous Agency Context**
- Proactive behavior adapted to relationship dynamics
- Initiative-taking appropriate to social role and relationship strength
- Goal generation considering social context and responsibilities

## Implementation Architecture

### **Data Storage Layer**
```
ChromaDB (Vector Store)
├── User Behavioral Patterns Collection
│   ├── Communication style vectors (learned)
│   ├── Social role embeddings (dynamic)
│   └── Behavioral pattern evolution
├── Relationship Vectors Collection
│   ├── 6-dimensional relationship embeddings
│   ├── Authority, intimacy, care responsibility dimensions
│   └── Temporal relationship evolution tracking
└── Interaction Patterns Collection
    ├── Conversation embeddings
    ├── Behavioral event vectors
    └── Context-aware interaction history

SQLite Metadata Store
├── User profiles (minimal metadata)
├── Relationship metadata (confidence, timestamps)
└── Interaction logs (audit trail)
```

### **System Architecture**

#### **Graph Embedding Foundation**
- **Node2Vec** for user behavioral embeddings
  - Random walk-based approach with configurable parameters (p=1.0, q=1.0)
  - 128-dimensional embeddings capturing structural and behavioral similarities
  - Walk length of 80 steps with 10 walks per node
  - Skip-gram model for learning node representations

#### **Relationship Vector System**
- **6-dimensional relationship vectors** learned from interaction patterns:
  - **Authority** (0.0-1.0): Peer-level to hierarchical relationships
  - **Intimacy** (0.0-1.0): Formal/professional to personal/intimate
  - **Care Responsibility** (0.0-1.0): No responsibility to primary caregiver
  - **Interaction Frequency**: Learned from conversation patterns
  - **Context Similarity**: Shared activities, interests, communication topics
  - **Temporal Stability**: Relationship consistency over time

#### **Graph Neural Network Layer**
- **GraphSAGE architecture** for advanced relationship reasoning
  - Multi-hop inference up to 3 degrees of separation
  - Community detection for social cluster identification
  - Influence propagation modeling for information and emotion flow
  - Message passing between relationship nodes

#### **Technology Stack**
1. **NetworkX** - Graph structure management and algorithms
2. **Node2Vec** (gensim) - Initial user behavioral embeddings
3. **PyTorch** - Custom relationship vector training and GNN implementation
4. **ChromaDB** - Vector storage and similarity search operations
5. **SQLite** - Metadata storage and interaction audit trails

### **Processing Pipeline**
1. **Interaction Capture**: Real-time conversation and behavior analysis
2. **Vector Update**: Continuous relationship embedding updates
3. **Graph Reasoning**: GNN-based multi-hop relationship inference
4. **Behavioral Calibration**: Dynamic communication and proactivity adjustment
5. **Context Integration**: Relationship context for AI system coordination

### **Privacy & Security**
- **Mandatory Local Processing**: All relationship modeling on-device only
- **AES-256-GCM Encryption**: Relationship data encrypted at rest
- **User-Controlled Access**: Selective sharing with explicit consent
- **Audit Logging**: Transparent relationship inference decision tracking
- **Information Compartmentalization**: Context isolation between relationships

## Behavioral Adaptation Framework

### **Dynamic Communication Style Adaptation**
Communication styles are dynamically determined by relationship vector dimensions rather than predefined categories:

- **Authority-Based Adaptation**:
  - High authority contexts: Respectful, appropriate deference, comprehensive information
  - Peer-level contexts: Collaborative, professional-casual, contextual information
  - Guidance contexts: Supportive guidance, warm professional, educational information

- **Intimacy-Based Adaptation**:
  - High intimacy: Warm personal tone, casual formality, emotionally aware responses
  - Moderate intimacy: Friendly tone, semi-casual, socially appropriate responses
  - Low intimacy: Professional tone, formal, task-focused responses

### **Dynamic Proactive Behavior Calibration**
Proactive behavior is calibrated based on care responsibility dimension and learned interaction patterns:

- **High-Care Relationships**: Proactive health check-ins, reminder systems, high emotional support
- **Moderate-Care Relationships**: Social engagement, shared interest discussions, responsive support
- **Low-Care Relationships**: Goal-oriented support, productivity assistance, minimal emotional involvement
- **Context-Aware Switching**: Work (task-oriented), family (care-oriented), social (engagement-oriented)

### **Dynamic Privacy Boundary Management**
Privacy boundaries are calculated using weighted relationship dimensions:
- **Intimacy weight (0.4)**: Primary factor for information sharing levels
- **Care responsibility weight (0.3)**: Care relationships receive appropriate access
- **Temporal stability weight (0.2)**: Stable relationships build trust over time
- **Context similarity weight (0.1)**: Shared contexts enable relevant information sharing

**Compartmentalization Features**:
- Cross-relationship information isolation
- Context-specific privacy boundaries (work/family/social)
- Explicit user consent for any information sharing between relationships

## Evolution and Learning

### **Relationship Maturation**
- Relationships evolve from initial formal interactions to deeper understanding
- Learning patterns adapt to changing life circumstances and role transitions
- Long-term relationship memory maintains consistency across time gaps

### **Context Switching**
- Same individuals may have different relationship contexts (work vs. family)
- Dynamic context recognition and appropriate behavioral switching
- Maintaining relationship continuity across different interaction environments

### **Social Graph Expansion**
- New relationship integration into existing social understanding
- Group dynamics learning when new members join established social contexts
- Relationship network effects and influence propagation modeling

## Future Enhancements

### **Multi-Device Relationship Synchronization**
- Encrypted relationship model synchronization across user devices
- Consistent social understanding in roaming scenarios
- Privacy-preserving relationship model sharing between trusted devices

### **Collective Learning (Optional)**
- Anonymous relationship pattern learning from user community
- Privacy-preserving federated learning for relationship understanding
- User-controlled participation in collective social intelligence

### **Advanced Reasoning**
- Temporal relationship prediction and lifecycle modeling
- Social conflict detection and mediation suggestions
- Group harmony optimization and social facilitation

## Integration Points

### **Message Bus Topics**
- `social/relationship/updated`: Relationship vector changes
- `social/context/changed`: Social context transitions
- `social/inference/result`: Relationship reasoning results

### **API Endpoints**
- Relationship context queries for AI systems
- Social appropriateness validation
- Privacy boundary enforcement

### **Configuration**
- Vector embedding learning rates and confidence thresholds
- Privacy boundary calculation weights and compartmentalization rules
- Graph neural network reasoning parameters and multi-hop limits
- Dynamic behavioral adaptation sensitivity settings

This architecture enables AICO to develop sophisticated, nuanced understanding of social relationships through learned behavioral patterns and vector-based reasoning, eliminating the need for static relationship categories while maintaining complete user privacy and control over personal social data.
