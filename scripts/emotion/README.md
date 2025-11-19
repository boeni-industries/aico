# Emotion Simulation Test Suite

Comprehensive testing and benchmarking for AICO's emotion simulation system.

## Overview

This test suite validates that AICO's emotion simulation:
- Generates appropriate emotional responses to conversation context
- Transitions smoothly between emotional states
- Persists emotional state correctly
- Conditions LLM responses appropriately

## Test Scripts

### `test_emotion_simulation.py`

Main test script that runs predefined multi-turn conversations and validates emotional state at each turn.

**Usage:**
```bash
# Basic usage
python scripts/emotion/test_emotion_simulation.py <user_uuid> <pin>

# With custom backend URL
python scripts/emotion/test_emotion_simulation.py <user_uuid> <pin> --base-url http://localhost:8000

# Export results to JSON
python scripts/emotion/test_emotion_simulation.py <user_uuid> <pin> --output results.json

# Run specific scenario
python scripts/emotion/test_emotion_simulation.py <user_uuid> <pin> --scenario default
```

**Example:**
```bash
python scripts/emotion/test_emotion_simulation.py user_123 1234
```

## Test Scenarios

### Default Scenario: "Emotional Journey: Support Through Crisis"

Tests emotional transitions through a realistic support conversation:

1. **Neutral Greeting** - Baseline neutral state
2. **Warm Concern** - User expresses stress → empathetic concern
3. **Protective** - User fears job loss → protective response
4. **Supportive Warmth** - User seeks advice → warm problem-solving
5. **Calm Relief** - Positive resolution → calm satisfaction

**Expected Emotional Arc:**
```
neutral → warm_concern → protective → warm_concern → calm
```

## Test Structure

### Components

1. **EmotionExpectation** - Defines expected emotional state
   - `feeling`: Expected primary emotion label
   - `valence_range`: Expected valence bounds (pleasure/displeasure)
   - `arousal_range`: Expected arousal bounds (activation/energy)
   - `intensity_range`: Expected intensity bounds
   - `description`: Human-readable expectation

2. **ConversationTurn** - Single conversation turn
   - `turn_number`: Sequential turn number
   - `user_message`: User's message text
   - `expectation`: Expected emotional response
   - `context`: Rationale for this turn

3. **TurnResult** - Test result for a turn
   - `status`: PASS/WARN/FAIL/SKIP
   - `actual_*`: Actual emotional state values
   - `expected`: Expected emotional state
   - `ai_response`: AICO's response text
   - `errors`: Critical validation failures
   - `warnings`: Minor deviations

4. **EmotionTestScenario** - Complete test scenario
   - `name`: Scenario name
   - `description`: Scenario description
   - `turns`: List of conversation turns

### Validation Rules

**FAIL Conditions:**
- Primary feeling doesn't match expected
- Valence outside expected range

**WARN Conditions:**
- Arousal outside expected range
- Intensity outside expected range

**PASS Conditions:**
- All validations pass

## Output

### Console Output

```
✨ AICO CLI
Running Scenario: Emotional Journey: Support Through Crisis

✅ PASS Turn 1: Neutral greeting response
✅ PASS Turn 2: Warm concern for user's stress
⚠️  WARN Turn 3: Protective concern for user's wellbeing
   • Arousal out of range: expected (0.6, 0.8), got 0.55
✅ PASS Turn 4: Supportive warmth with problem-solving
✅ PASS Turn 5: Calm relief at positive resolution

================================================================================
Test Summary
================================================================================

┌─────────────────┬────────┐
│ Metric          │ Value  │
├─────────────────┼────────┤
│ Total Turns     │ 5      │
│ ✅ Passed       │ 4      │
│ ⚠️  Warnings    │ 1      │
│ ❌ Failed       │ 0      │
│ Success Rate    │ 80.0%  │
└─────────────────┴────────┘
```

### JSON Export

```json
{
  "timestamp": "2025-11-19T15:45:00",
  "scenario": {
    "name": "Emotional Journey: Support Through Crisis",
    "turns": [...]
  },
  "results": [
    {
      "turn": 1,
      "status": "PASS",
      "actual": {
        "feeling": "neutral",
        "valence": 0.0,
        "arousal": 0.5,
        "intensity": 0.5
      },
      "expected": {...},
      "ai_response": "Hello! I'm doing well...",
      "errors": [],
      "warnings": []
    }
  ],
  "summary": {
    "total": 5,
    "passed": 4,
    "warned": 1,
    "failed": 0
  }
}
```

## Adding New Scenarios

Create a new scenario function in `test_emotion_simulation.py`:

```python
def create_my_scenario() -> EmotionTestScenario:
    return EmotionTestScenario(
        name="My Test Scenario",
        description="Tests specific emotional behavior",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="Your message here",
                expectation=EmotionExpectation(
                    feeling="expected_feeling",
                    valence_range=(-0.5, 0.5),
                    arousal_range=(0.4, 0.6),
                    intensity_range=(0.5, 0.7),
                    description="What you expect to happen"
                ),
                context="Why this turn is important"
            ),
            # Add more turns...
        ]
    )
```

Then add it to the scenario choices in `main()`.

## Benchmarking

### Performance Metrics

Track these metrics across test runs:
- Emotional state transition accuracy
- Valence/arousal/intensity precision
- Response time per turn
- Persistence reliability

### Regression Testing

Run tests after changes to:
- Emotion engine appraisal logic
- CPM state generation
- LLM conditioning
- Database persistence

### Continuous Integration

Add to CI pipeline:
```bash
# Run tests and fail on errors
python scripts/emotion/test_emotion_simulation.py $USER_UUID $PIN --output ci_results.json
```

## Troubleshooting

### Authentication Fails
- Verify user_uuid and PIN are correct
- Check backend is running on specified URL
- Ensure user exists in database

### Emotion State Fetch Fails
- Verify JWT authentication is working
- Check emotion REST endpoints are registered
- Ensure EmotionEngine service is running

### All Tests Fail
- Check backend logs for EmotionEngine errors
- Verify database schema v17 is applied
- Ensure message bus is running

### Inconsistent Results
- EmotionEngine may need tuning (appraisal_sensitivity, regulation_strength)
- Check for race conditions (increase delay between turns)
- Verify emotional state persistence is working

## Future Enhancements

- [ ] Add more test scenarios (joy, sadness, anger, fear)
- [ ] Test emotional memory across sessions
- [ ] Benchmark LLM conditioning effectiveness
- [ ] Add performance timing metrics
- [ ] Test multimodal expression parameters
- [ ] Add stress testing with rapid turns
- [ ] Test emotional regulation boundaries
- [ ] Add visualization of emotional arcs
