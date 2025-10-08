# AICO Memory Intelligence Evaluator

A comprehensive end-to-end testing framework for AICO's memory system that evaluates all aspects of memory performance including working memory, semantic memory, episodic memory, context adherence, entity extraction, and conversation continuity.

## Overview

This evaluation framework is designed for continuous improvement and scoring of AICO's memory system through realistic conversation scenarios and multi-dimensional evaluation metrics. It provides automated testing, detailed analysis, and actionable insights for memory system optimization.

## Features

### 🧠 Comprehensive Memory Testing
- **Working Memory**: Session context and immediate conversation state
- **Episodic Memory**: Conversation history and temporal patterns
- **Semantic Memory**: Knowledge base and entity relationships
- **Procedural Memory**: User patterns and behavioral learning
- **Thread Management**: Automatic thread resolution and continuity
- **Entity Extraction**: Named entity recognition accuracy

### 📊 Multi-Dimensional Scoring
- **Context Adherence**: How well AI maintains conversational context
- **Knowledge Retention**: Ability to recall information from earlier turns
- **Entity Extraction**: Accuracy of named entity recognition
- **Conversation Relevancy**: Topical coherence and response appropriateness
- **Thread Management**: Accuracy of thread resolution decisions
- **Response Quality**: Overall coherence and helpfulness
- **Memory Consistency**: Factual accuracy and contradiction detection

### 🎯 Realistic Test Scenarios
- **6-Turn Comprehensive Test**: Primary memory evaluation scenario
- **Entity Extraction Intensive**: Complex named entity testing
- **Thread Management Test**: Context switching and reactivation
- **Long-term Memory Test**: Extended retention and recall
- **Performance Stress Test**: High-volume entity processing

### 📈 Continuous Improvement
- **Automated Scoring**: Objective performance metrics
- **Trend Analysis**: Performance tracking over time
- **Detailed Reports**: JSON, Markdown, and console output
- **Extensible Framework**: Easy addition of new scenarios and metrics

## Installation

```bash
# Navigate to the memory evaluation directory
cd /Users/mbo/Documents/dev/aico/scripts/memory_eval

# Install required dependencies (if not already installed)
pip install aiohttp asyncio dataclasses
```

## Quick Start

### Basic Usage

```bash
# Run the comprehensive memory test (default scenario)
python run_evaluation.py

# Run a specific scenario
python run_evaluation.py --scenario entity_extraction_intensive

# Run all available scenarios
python run_evaluation.py --all-scenarios

# List available scenarios
python run_evaluation.py --list-scenarios
```

### Continuous Evaluation

```bash
# Run continuous evaluation for system improvement
python run_evaluation.py --continuous --iterations 10 --delay 3.0

# Continuous evaluation with all scenarios
python run_evaluation.py --continuous --all-scenarios --iterations 5
```

### Custom Configuration

```bash
# Custom backend URL and timeout
python run_evaluation.py --backend-url http://localhost:8000 --timeout 45

# Wait for backend to be ready
python run_evaluation.py --wait-for-backend --max-wait 120

# Verbose output with custom output directory
python run_evaluation.py --verbose --output-dir ./my_results
```

## Test Scenarios

### 1. Comprehensive Memory Test (Default)
**6-turn conversation testing all memory components**

- **Turns**: 6 comprehensive conversation exchanges
- **Focus**: Entity extraction, context retention, thread management
- **Entities**: Names, locations, organizations, dates, preferences
- **Memory Tests**: Working, episodic, semantic memory integration
- **Success Criteria**: 85% overall, 90% knowledge retention

**Example Flow**:
1. User introduction with personal details (Michael, San Francisco, TechCorp)
2. Job discussion with emotional context (software engineer, nervousness)
3. Topic shift to pets (cat named Whiskers, moving stress)
4. Birthday planning (October 13th, restaurant exploration)
5. Memory recall test (job title verification)
6. Entity recall test (cat's name)

### 2. Entity Extraction Intensive
**Complex named entity recognition testing**

- **Focus**: High-volume entity extraction accuracy
- **Entities**: Locations, organizations, dates, money, facilities
- **Difficulty**: Hard (complex entity relationships)
- **Use Case**: Travel planning with multiple entities per turn

### 3. Thread Management Test
**Context switching and thread reactivation**

- **Focus**: Thread creation, continuation, and reactivation logic
- **Scenarios**: Topic changes, context switching, thread resumption
- **Validation**: Accurate thread resolution decisions
- **Use Case**: Multi-topic conversations with context switches

### 4. Long-term Memory Test
**Extended retention and recall capabilities**

- **Focus**: Cross-conversation knowledge retention
- **Memory Types**: Episodic and semantic memory integration
- **Validation**: Information recall across topic changes
- **Use Case**: Professional context with topic diversions

### 5. Performance Stress Test
**High-volume processing and performance benchmarking**

- **Focus**: System performance under load
- **Entities**: Multiple organizations, large numbers, complex data
- **Metrics**: Response time, throughput, accuracy under stress
- **Use Case**: Conference planning with extensive details

## Evaluation Metrics

### Core Memory Metrics

| Metric | Description | Weight | Target |
|--------|-------------|--------|--------|
| **Context Adherence** | Maintains conversational context across turns | 20% | ≥85% |
| **Knowledge Retention** | Recalls information from previous turns | 20% | ≥90% |
| **Entity Extraction** | Accuracy of named entity recognition | 15% | ≥80% |
| **Conversation Relevancy** | Response appropriateness and coherence | 15% | ≥85% |
| **Thread Management** | Accuracy of thread resolution decisions | 15% | ≥95% |
| **Response Quality** | Overall response coherence and helpfulness | 10% | ≥80% |
| **Memory Consistency** | Factual accuracy and contradiction detection | 5% | ≥95% |

### Performance Metrics

- **Response Time**: Average, min, max response times
- **Throughput**: Turns per minute processing rate
- **Error Rate**: Percentage of failed operations
- **Memory Usage**: System resource utilization

## Output Reports

### 1. Console Output
Real-time evaluation progress with:
- Turn-by-turn conversation flow
- Immediate metric feedback
- Performance indicators
- Error reporting

### 2. JSON Reports
Machine-readable evaluation data:
```json
{
  "metadata": {
    "session_id": "uuid",
    "scenario_name": "comprehensive_memory_test",
    "timestamp": "2024-01-15T10:30:00",
    "conversation_turns": 6
  },
  "scores": {
    "overall": {"score": 0.87, "percentage": 87.0},
    "context_adherence": {"score": 0.85, "percentage": 85.0}
  },
  "performance": {
    "average_response_time_ms": 1250,
    "turns_per_minute": 2.4
  }
}
```

### 3. Detailed Markdown Reports
Comprehensive analysis including:
- Executive summary with grades
- Metric-by-metric analysis
- Conversation flow breakdown
- Performance analysis
- Recommendations for improvement

## Architecture

### Components

```
memory_eval/
├── __init__.py              # Package initialization
├── evaluator.py             # Main evaluation orchestrator
├── scenarios.py             # Test scenario definitions
├── metrics.py               # Scoring and evaluation metrics
├── api_client.py            # AICO backend HTTP client
├── reporters.py             # Output formatting and reports
├── run_evaluation.py        # Command-line interface
└── README.md               # This documentation
```

### Integration Points

- **AICO Backend API**: REST endpoints for conversation
- **Memory System**: Working, episodic, semantic, procedural memory
- **Entity Extraction**: NER via modelservice
- **Thread Management**: Automatic thread resolution
- **Performance Monitoring**: Response time and throughput tracking

## Extending the Framework

### Adding New Scenarios

```python
from memory_eval.scenarios import ConversationScenario, ConversationTurn

# Define new scenario
new_scenario = ConversationScenario(
    name="custom_test",
    description="Custom memory test scenario",
    conversation_turns=[
        ConversationTurn(
            user_message="Test message",
            expected_entities={"PERSON": ["TestUser"]},
            expected_context_elements=["test_context"],
            validation_rules=["should_acknowledge_test"]
        )
    ],
    success_criteria={"overall_score": 0.80}
)

# Add to scenario library
scenario_library.add_custom_scenario(new_scenario)
```

### Adding New Metrics

```python
from memory_eval.metrics import MemoryMetrics, MetricScore

class CustomMetrics(MemoryMetrics):
    async def calculate_custom_metric(self, session) -> MetricScore:
        # Implement custom scoring logic
        score = self._calculate_custom_score(session)
        
        return MetricScore(
            score=score,
            explanation="Custom metric evaluation"
        )
```

### Custom Reporters

```python
from memory_eval.reporters import DetailedReporter

class CustomReporter(DetailedReporter):
    def generate_custom_report(self, result):
        # Implement custom report format
        return custom_formatted_report
```

## Configuration

### Environment Variables

```bash
# Backend configuration
export AICO_BACKEND_URL="http://localhost:8000"
export AICO_AUTH_TOKEN="your_token_here"

# Evaluation settings
export MEMORY_EVAL_TIMEOUT=30
export MEMORY_EVAL_OUTPUT_DIR="./results"
```

### Backend Requirements

- AICO backend running on specified URL
- Authentication system enabled
- Memory system components active:
  - Working memory (RocksDB/LMDB)
  - Episodic memory (encrypted libSQL)
  - Semantic memory (ChromaDB)
  - Entity extraction (spaCy NER)
  - Sentiment analysis (transformers)

## Troubleshooting

### Common Issues

1. **Backend Connection Failed**
   ```bash
   # Check backend health
   curl http://localhost:8000/api/v1/health
   
   # Wait for backend to be ready
   python run_evaluation.py --wait-for-backend --max-wait 120
   ```

2. **Authentication Errors**
   ```bash
   # Use explicit auth token
   python run_evaluation.py --auth-token "your_token"
   
   # Check test user credentials in api_client.py
   ```

3. **Memory System Errors**
   - Ensure all memory components are initialized
   - Check ChromaDB permissions and storage
   - Verify NER and sentiment analysis models are loaded

4. **Performance Issues**
   ```bash
   # Increase timeout for slow responses
   python run_evaluation.py --timeout 60
   
   # Run single scenario for debugging
   python run_evaluation.py --scenario comprehensive_memory_test --verbose
   ```

### Debug Mode

```bash
# Enable verbose logging
python run_evaluation.py --verbose

# Check specific scenario details
python run_evaluation.py --list-scenarios

# Test backend connectivity
python -c "
import asyncio
from memory_eval.api_client import AICOTestClient

async def test():
    client = AICOTestClient()
    health = await client.check_backend_health()
    print(health)

asyncio.run(test())
"
```

## Performance Benchmarks

### Target Performance
- **Response Time**: <2000ms average
- **Entity Extraction**: >80% accuracy
- **Context Retention**: >85% across 6 turns
- **Memory Consistency**: >95% factual accuracy
- **Overall Score**: >85% for production readiness

### Optimization Areas
- Memory context assembly efficiency
- Entity extraction model performance
- Thread resolution algorithm tuning
- Response generation optimization
- Database query performance

## Contributing

### Adding Test Scenarios
1. Define scenario in `scenarios.py`
2. Add validation rules and expected outcomes
3. Test with various conversation patterns
4. Document success criteria

### Improving Metrics
1. Analyze current metric limitations
2. Implement enhanced scoring algorithms
3. Add detailed explanation generation
4. Validate against human evaluation

### Enhancing Reports
1. Add new visualization formats
2. Implement trend analysis features
3. Create automated improvement suggestions
4. Integrate with CI/CD pipelines

## License

This evaluation framework is part of the AICO project and follows the same licensing terms.
