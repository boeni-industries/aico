# AMS Future Improvements

## Knowledge Graph Quality Feedback Loop

### Automated Analysis
- **Keyword Detection**: Flag feedback containing KG-related terms ("knowledge graph", "facts", "verify")
- **Entity Extraction**: Extract entities mentioned in AI response and user feedback
- **KG Comparison**: Automatically compare AI claims against current KG data
- **Discrepancy Detection**: Identify mismatches between AI response and KG facts
- **Auto-Triage**: Create review tasks when discrepancies found

### Human Review Workflow
- **Review Dashboard**: Queue of KG verification tasks with priority
- **Context Display**: Show AI response, KG facts, user feedback side-by-side
- **Action Options**: Approve KG, update KG, request more info
- **Pattern Tracking**: Log common KG error types for future detection

### Closed-Loop Learning
- **KG Updates**: Apply corrections from human review to knowledge graph
- **Skill Adjustment**: Penalize skills that produce KG-related errors
- **Freshness Checks**: Trigger validation for entities flagged as outdated
- **Error Patterns**: Learn from repeated issues to prevent future errors

### Sub-Category Enhancement
**Current:**
```
reason: "incorrect_info"
free_text: "should verify facts against the knowledge graph!"
```

**Enhanced:**
```
reason: "incorrect_info"
sub_reason: "knowledge_graph_verification"
free_text: "should verify facts against the knowledge graph!"
kg_entities: ["Marcus", "TechCorp"]
requires_review: true
```

### Implementation Priority

**Phase 1 (High Value, Low Effort):**
1. Keyword detection in free text
2. Auto-flag feedback for review
3. Entity extraction from conversations

**Phase 2 (High Value, Medium Effort):**
4. Automated KG vs AI response comparison
5. Structured review task creation
6. KG error pattern tracking

**Phase 3 (High Value, High Effort):**
7. Human review dashboard
8. KG update workflow integration
9. Skill confidence adjustment based on KG errors

### Benefits
- **Data Quality**: Continuous KG improvement through user feedback
- **Trust**: Users see their feedback directly improving system
- **Accuracy**: Reduced hallucinations and factual errors
- **Learning**: System learns which skills use KG correctly
- **Transparency**: Clear feedback loop from user → KG → AI

### Technical Notes
- Leverage existing feedback classification pipeline
- Extend `feedback_events` schema with KG-specific fields
- Create new `kg_review_tasks` table for human review queue
- Add KG verification metrics to skill confidence calculation
