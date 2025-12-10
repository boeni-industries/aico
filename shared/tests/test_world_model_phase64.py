"""
Comprehensive Tests for World Model Phase 6.4

Tests schema learning, hypothesis management, and drift detection
according to design specifications in agency-component-world-model.md
"""

import pytest
from datetime import datetime, timedelta

from aico.ai.world_model.schema_learner import SchemaLearner
from aico.ai.world_model.hypothesis_manager import HypothesisManager
from aico.ai.world_model.drift_detector import DriftDetector
from aico.ai.world_model.models import (
    Schema, FieldSchema, ValidationResult,
    Hypothesis, HypothesisTestResult,
    DriftReport, Contradiction, ConfidenceDecayConfig
)


# ============================================================================
# SCHEMA LEARNER TESTS
# ============================================================================

class TestSchemaLearner:
    """Test schema extraction, validation, evolution, and drift detection."""
    
    def test_initialization(self):
        """Test SchemaLearner initialization with custom parameters."""
        learner = SchemaLearner(min_samples=5, confidence_threshold=0.8)
        
        assert learner.min_samples == 5
        assert learner.confidence_threshold == 0.8
    
    def test_extract_schema_basic(self):
        """Test basic schema extraction from consistent samples."""
        learner = SchemaLearner(min_samples=3)
        
        samples = [
            {"name": "Alice", "age": 30, "active": True},
            {"name": "Bob", "age": 25, "active": True},
            {"name": "Charlie", "age": 35, "active": False},
        ]
        
        schema = learner.extract_schema("Person", samples)
        
        assert schema.entity_type == "Person"
        assert schema.version == "1.0.0"
        assert schema.sample_count == 3
        assert len(schema.fields) == 3
        assert "name" in schema.fields
        assert "age" in schema.fields
        assert "active" in schema.fields
        assert schema.confidence > 0.0
    
    def test_extract_schema_field_types(self):
        """Test correct field type inference."""
        learner = SchemaLearner(min_samples=2)
        
        samples = [
            {"text": "hello", "count": 42, "ratio": 3.14, "flag": True, "tags": ["a", "b"]},
            {"text": "world", "count": 100, "ratio": 2.71, "flag": False, "tags": ["c"]},
        ]
        
        schema = learner.extract_schema("TestEntity", samples)
        
        assert schema.fields["text"].field_type == "string"
        assert schema.fields["count"].field_type == "number"
        assert schema.fields["ratio"].field_type == "number"
        assert schema.fields["flag"].field_type == "boolean"
        assert schema.fields["tags"].field_type == "array"
    
    def test_extract_schema_required_fields(self):
        """Test required field detection based on presence ratio."""
        learner = SchemaLearner(min_samples=3)
        
        samples = [
            {"always": "present", "sometimes": "here"},
            {"always": "present", "sometimes": "here"},
            {"always": "present"},  # 'sometimes' missing
        ]
        
        schema = learner.extract_schema("TestEntity", samples)
        
        # 'always' appears in 100% of samples -> required
        assert schema.fields["always"].required is True
        # 'sometimes' appears in 67% of samples -> not required
        assert schema.fields["sometimes"].required is False
    
    def test_extract_schema_constraints_numeric(self):
        """Test numeric constraint inference (min/max)."""
        learner = SchemaLearner(min_samples=3)
        
        samples = [
            {"age": 25},
            {"age": 30},
            {"age": 35},
        ]
        
        schema = learner.extract_schema("Person", samples)
        
        assert "min" in schema.fields["age"].constraints
        assert "max" in schema.fields["age"].constraints
        assert schema.fields["age"].constraints["min"] == 25
        assert schema.fields["age"].constraints["max"] == 35
    
    def test_extract_schema_constraints_string(self):
        """Test string constraint inference (min_length/max_length)."""
        learner = SchemaLearner(min_samples=2)
        
        samples = [
            {"name": "Alice"},
            {"name": "Bob"},
        ]
        
        schema = learner.extract_schema("Person", samples)
        
        assert "min_length" in schema.fields["name"].constraints
        assert "max_length" in schema.fields["name"].constraints
    
    def test_extract_schema_confidence_calculation(self):
        """Test schema confidence based on sample count and consistency."""
        learner = SchemaLearner(min_samples=10, confidence_threshold=0.7)
        
        # High consistency samples
        consistent_samples = [{"name": "User", "age": i} for i in range(20)]
        consistent_schema = learner.extract_schema("Consistent", consistent_samples)
        
        # Low consistency samples
        inconsistent_samples = [
            {"name": "User", "age": 25},
            {"name": "User"},  # Missing age
            {"age": 30},  # Missing name
            {"name": "User", "age": 35, "extra": "field"},
        ]
        inconsistent_schema = learner.extract_schema("Inconsistent", inconsistent_samples)
        
        # More samples and consistency = higher confidence
        assert consistent_schema.confidence > inconsistent_schema.confidence
    
    def test_validate_schema_success(self):
        """Test successful schema validation."""
        learner = SchemaLearner()
        
        schema = Schema(
            schema_id="test-1",
            version="1.0.0",
            entity_type="Person",
            fields={
                "name": FieldSchema(name="name", field_type="string", required=True),
                "age": FieldSchema(name="age", field_type="number", required=False),
            }
        )
        
        data = {"name": "Alice", "age": 30}
        result = learner.validate_schema(schema, data)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_schema_missing_required(self):
        """Test validation failure with missing required field."""
        learner = SchemaLearner()
        
        schema = Schema(
            schema_id="test-1",
            version="1.0.0",
            entity_type="Person",
            fields={
                "name": FieldSchema(name="name", field_type="string", required=True),
            }
        )
        
        data = {"age": 30}  # Missing required 'name'
        result = learner.validate_schema(schema, data)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Missing required field: name" in result.errors[0]
    
    def test_validate_schema_type_mismatch(self):
        """Test validation failure with type mismatch."""
        learner = SchemaLearner()
        
        schema = Schema(
            schema_id="test-1",
            version="1.0.0",
            entity_type="Person",
            fields={
                "age": FieldSchema(name="age", field_type="number", required=True),
            }
        )
        
        data = {"age": "thirty"}  # String instead of number
        result = learner.validate_schema(schema, data)
        
        assert result.is_valid is False
        assert any("Type mismatch" in err for err in result.errors)
    
    def test_validate_schema_unknown_field_warning(self):
        """Test validation warning for unknown fields."""
        learner = SchemaLearner()
        
        schema = Schema(
            schema_id="test-1",
            version="1.0.0",
            entity_type="Person",
            fields={
                "name": FieldSchema(name="name", field_type="string", required=True),
            }
        )
        
        data = {"name": "Alice", "unknown": "field"}
        result = learner.validate_schema(schema, data)
        
        assert result.is_valid is True  # Not an error
        assert len(result.warnings) == 1
        assert "Unknown field: unknown" in result.warnings[0]
    
    def test_validate_schema_constraint_violations(self):
        """Test validation with constraint violations."""
        learner = SchemaLearner()
        
        schema = Schema(
            schema_id="test-1",
            version="1.0.0",
            entity_type="Person",
            fields={
                "age": FieldSchema(
                    name="age",
                    field_type="number",
                    required=True,
                    constraints={"min": 0, "max": 120}
                ),
            }
        )
        
        # Value too high
        data = {"age": 150}
        result = learner.validate_schema(schema, data)
        
        assert result.is_valid is False
        assert any("max" in err for err in result.errors)
    
    def test_evolve_schema_add_fields(self):
        """Test schema evolution with new fields (minor version bump)."""
        learner = SchemaLearner(min_samples=2)
        
        old_schema = Schema(
            schema_id="test-1",
            version="1.0.0",
            entity_type="Person",
            fields={
                "name": FieldSchema(name="name", field_type="string", required=True),
            },
            sample_count=10,
            confidence=0.9,
        )
        
        new_samples = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ]
        
        evolved = learner.evolve_schema(old_schema, new_samples)
        
        assert evolved.schema_id == old_schema.schema_id  # Same ID
        assert evolved.version == "1.1.0"  # Minor version bump
        assert "email" in evolved.fields  # New field added
        assert "name" in evolved.fields  # Old field preserved
        assert evolved.sample_count == 12  # 10 + 2
    
    def test_evolve_schema_version_bumping(self):
        """Test semantic version bumping logic."""
        learner = SchemaLearner(min_samples=1)
        
        old_schema = Schema(
            schema_id="test-1",
            version="1.2.3",
            entity_type="Test",
            fields={},
            sample_count=5,
        )
        
        # Adding new fields = minor version bump
        new_samples = [{"new_field": "value"}]
        evolved = learner.evolve_schema(old_schema, new_samples)
        
        assert evolved.version == "1.3.0"  # Minor bump, patch reset
    
    def test_detect_schema_drift_no_drift(self):
        """Test drift detection with no drift."""
        learner = SchemaLearner(min_samples=2)
        
        schema = Schema(
            schema_id="test-1",
            version="1.0.0",
            entity_type="Person",
            fields={
                "name": FieldSchema(name="name", field_type="string"),
                "age": FieldSchema(name="age", field_type="number"),
            }
        )
        
        recent_samples = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        
        drift = learner.detect_schema_drift(schema, recent_samples)
        
        assert drift["has_drift"] is False
        assert len(drift["new_fields"]) == 0
        assert len(drift["missing_fields"]) == 0
    
    def test_detect_schema_drift_new_fields(self):
        """Test drift detection with new fields appearing."""
        learner = SchemaLearner(min_samples=2)
        
        schema = Schema(
            schema_id="test-1",
            version="1.0.0",
            entity_type="Person",
            fields={
                "name": FieldSchema(name="name", field_type="string"),
            }
        )
        
        recent_samples = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ]
        
        drift = learner.detect_schema_drift(schema, recent_samples)
        
        assert drift["has_drift"] is True
        assert "email" in drift["new_fields"]
    
    def test_detect_schema_drift_missing_fields(self):
        """Test drift detection with fields disappearing."""
        learner = SchemaLearner(min_samples=2)
        
        schema = Schema(
            schema_id="test-1",
            version="1.0.0",
            entity_type="Person",
            fields={
                "name": FieldSchema(name="name", field_type="string"),
                "age": FieldSchema(name="age", field_type="number"),
            }
        )
        
        recent_samples = [
            {"name": "Alice"},  # Missing 'age'
            {"name": "Bob"},
        ]
        
        drift = learner.detect_schema_drift(schema, recent_samples)
        
        assert drift["has_drift"] is True
        assert "age" in drift["missing_fields"]
    
    def test_detect_schema_drift_type_changes(self):
        """Test drift detection with type changes."""
        learner = SchemaLearner(min_samples=2)
        
        schema = Schema(
            schema_id="test-1",
            version="1.0.0",
            entity_type="Person",
            fields={
                "age": FieldSchema(name="age", field_type="number"),
            }
        )
        
        recent_samples = [
            {"age": "thirty"},  # String instead of number
            {"age": "forty"},
        ]
        
        drift = learner.detect_schema_drift(schema, recent_samples)
        
        assert drift["has_drift"] is True
        assert len(drift["type_mismatches"]) > 0
        assert drift["type_mismatches"][0]["field"] == "age"
        assert drift["type_mismatches"][0]["expected"] == "number"
        assert drift["type_mismatches"][0]["observed"] == "string"


# ============================================================================
# HYPOTHESIS MANAGER TESTS
# ============================================================================

class TestHypothesisManager:
    """Test hypothesis generation, Bayesian updating, and lifecycle management."""
    
    def test_initialization(self):
        """Test HypothesisManager initialization."""
        manager = HypothesisManager(
            prior_confidence=0.6,
            confirmation_threshold=0.85,
            rejection_threshold=0.15
        )
        
        assert manager.prior_confidence == 0.6
        assert manager.confirmation_threshold == 0.85
        assert manager.rejection_threshold == 0.15
    
    def test_generate_hypothesis(self):
        """Test basic hypothesis generation."""
        manager = HypothesisManager()
        
        hypothesis = manager.generate_hypothesis(
            user_id="user-1",
            description="User is changing jobs",
            hypothesis_type="state_change",
            affected_entities=["user-1", "job-1"],
            initial_evidence=["event-1", "event-2"]
        )
        
        assert hypothesis.user_id == "user-1"
        assert hypothesis.description == "User is changing jobs"
        assert hypothesis.hypothesis_type == "state_change"
        assert hypothesis.confidence == 0.5  # Default prior
        assert hypothesis.status == "open"
        assert len(hypothesis.evidence) == 2
        assert hypothesis.hypothesis_id in manager.hypotheses
    
    def test_bayesian_update_supporting_evidence(self):
        """Test Bayesian update with supporting evidence increases confidence."""
        manager = HypothesisManager(prior_confidence=0.5)
        
        hypothesis = manager.generate_hypothesis(
            user_id="user-1",
            description="Test hypothesis",
            hypothesis_type="pattern",
            affected_entities=[]
        )
        
        old_confidence = hypothesis.confidence
        
        # Test with supporting evidence (likelihood ratio = 2.0)
        result = manager.test_hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            test_type="evidence_check",
            supports_hypothesis=True,
            evidence_ids=["evidence-1"]
        )
        
        assert result.supports_hypothesis is True
        assert result.confidence_delta > 0
        assert hypothesis.confidence > old_confidence
        assert "evidence-1" in hypothesis.evidence
    
    def test_bayesian_update_counter_evidence(self):
        """Test Bayesian update with counter-evidence decreases confidence."""
        manager = HypothesisManager(prior_confidence=0.5)
        
        hypothesis = manager.generate_hypothesis(
            user_id="user-1",
            description="Test hypothesis",
            hypothesis_type="pattern",
            affected_entities=[]
        )
        
        old_confidence = hypothesis.confidence
        
        # Test with counter-evidence (likelihood ratio = 0.5)
        result = manager.test_hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            test_type="evidence_check",
            supports_hypothesis=False,
            evidence_ids=["counter-1"]
        )
        
        assert result.supports_hypothesis is False
        assert result.confidence_delta < 0
        assert hypothesis.confidence < old_confidence
        assert "counter-1" in hypothesis.counter_evidence
    
    def test_custom_likelihood_ratio(self):
        """Test Bayesian update with custom likelihood ratio."""
        manager = HypothesisManager(prior_confidence=0.5)
        
        hypothesis = manager.generate_hypothesis(
            user_id="user-1",
            description="Test",
            hypothesis_type="pattern",
            affected_entities=[]
        )
        
        # Very strong evidence (likelihood ratio = 10.0)
        result = manager.test_hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            test_type="pattern_match",
            supports_hypothesis=True,
            likelihood_ratio=10.0
        )
        
        # Should significantly increase confidence
        assert hypothesis.confidence > 0.8
    
    def test_auto_confirmation(self):
        """Test automatic confirmation when confidence exceeds threshold."""
        manager = HypothesisManager(
            prior_confidence=0.7,
            confirmation_threshold=0.8
        )
        
        hypothesis = manager.generate_hypothesis(
            user_id="user-1",
            description="Test",
            hypothesis_type="pattern",
            affected_entities=[]
        )
        
        # Add strong supporting evidence
        manager.test_hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            test_type="evidence_check",
            supports_hypothesis=True,
            likelihood_ratio=5.0
        )
        
        # Should auto-confirm
        assert hypothesis.status == "confirmed"
        assert hypothesis.confirmed_at is not None
    
    def test_auto_rejection(self):
        """Test automatic rejection when confidence drops below threshold."""
        manager = HypothesisManager(
            prior_confidence=0.3,
            rejection_threshold=0.2
        )
        
        hypothesis = manager.generate_hypothesis(
            user_id="user-1",
            description="Test",
            hypothesis_type="pattern",
            affected_entities=[]
        )
        
        # Add strong counter-evidence
        manager.test_hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            test_type="evidence_check",
            supports_hypothesis=False,
            likelihood_ratio=0.1
        )
        
        # Should auto-reject
        assert hypothesis.status == "rejected"
    
    def test_needs_user_confirmation(self):
        """Test transition to needs_user_confirmation status."""
        manager = HypothesisManager(
            prior_confidence=0.5,
            confirmation_threshold=0.8
        )
        
        hypothesis = manager.generate_hypothesis(
            user_id="user-1",
            description="Test",
            hypothesis_type="state_change",
            affected_entities=[]
        )
        
        # Add moderate supporting evidence to reach 0.7-0.8 range
        manager.test_hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            test_type="evidence_check",
            supports_hypothesis=True,
            likelihood_ratio=3.0
        )
        
        # Should need user confirmation (confidence >= 0.7 but < 0.8)
        if 0.7 <= hypothesis.confidence < 0.8:
            assert hypothesis.status == "needs_user_confirmation"
    
    def test_manual_confirmation(self):
        """Test manual hypothesis confirmation."""
        manager = HypothesisManager()
        
        hypothesis = manager.generate_hypothesis(
            user_id="user-1",
            description="Test",
            hypothesis_type="pattern",
            affected_entities=[]
        )
        
        confirmed = manager.confirm_hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            confirmation_source="user"
        )
        
        assert confirmed.status == "confirmed"
        assert confirmed.confidence == 1.0
        assert confirmed.confirmed_at is not None
        assert confirmed.metadata["confirmation_source"] == "user"
    
    def test_manual_rejection(self):
        """Test manual hypothesis rejection."""
        manager = HypothesisManager()
        
        hypothesis = manager.generate_hypothesis(
            user_id="user-1",
            description="Test",
            hypothesis_type="pattern",
            affected_entities=[]
        )
        
        rejected = manager.reject_hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            rejection_reason="User feedback"
        )
        
        assert rejected.status == "rejected"
        assert rejected.confidence == 0.0
        assert rejected.metadata["rejection_reason"] == "User feedback"
    
    def test_get_hypotheses_for_user(self):
        """Test retrieving hypotheses for a user."""
        manager = HypothesisManager()
        
        # Create hypotheses for different users
        h1 = manager.generate_hypothesis("user-1", "Test 1", "pattern", [])
        h2 = manager.generate_hypothesis("user-1", "Test 2", "state_change", [])
        h3 = manager.generate_hypothesis("user-2", "Test 3", "pattern", [])
        
        user1_hypotheses = manager.get_hypotheses_for_user("user-1")
        
        assert len(user1_hypotheses) == 2
        assert all(h.user_id == "user-1" for h in user1_hypotheses)
    
    def test_get_hypotheses_filtered_by_status(self):
        """Test retrieving hypotheses filtered by status."""
        manager = HypothesisManager()
        
        h1 = manager.generate_hypothesis("user-1", "Test 1", "pattern", [])
        h2 = manager.generate_hypothesis("user-1", "Test 2", "pattern", [])
        
        # Confirm one
        manager.confirm_hypothesis(h1.hypothesis_id)
        
        open_hypotheses = manager.get_hypotheses_for_user("user-1", status="open")
        confirmed_hypotheses = manager.get_hypotheses_for_user("user-1", status="confirmed")
        
        assert len(open_hypotheses) == 1
        assert len(confirmed_hypotheses) == 1
    
    def test_get_open_hypotheses(self):
        """Test retrieving all open hypotheses."""
        manager = HypothesisManager()
        
        h1 = manager.generate_hypothesis("user-1", "Test 1", "pattern", [])
        h2 = manager.generate_hypothesis("user-2", "Test 2", "pattern", [])
        h3 = manager.generate_hypothesis("user-1", "Test 3", "pattern", [])
        
        # Confirm one
        manager.confirm_hypothesis(h1.hypothesis_id)
        
        open_hypotheses = manager.get_open_hypotheses()
        
        assert len(open_hypotheses) == 2
        assert all(h.status == "open" for h in open_hypotheses)
    
    def test_generate_from_pattern_strong(self):
        """Test generating hypothesis from strong pattern."""
        manager = HypothesisManager()
        
        pattern = {
            "type": "temporal",
            "confidence": 0.8,
            "description": "User exercises every morning",
            "entities": ["user-1", "activity-exercise"]
        }
        
        hypothesis = manager.generate_from_pattern("user-1", pattern)
        
        assert hypothesis is not None
        assert hypothesis.hypothesis_type == "behavioral"
        assert hypothesis.confidence == 0.8
        assert hypothesis.metadata["generated_from"] == "pattern_detection"
    
    def test_generate_from_pattern_weak(self):
        """Test that weak patterns don't generate hypotheses."""
        manager = HypothesisManager()
        
        pattern = {
            "type": "temporal",
            "confidence": 0.4,  # Too weak
            "description": "Weak pattern",
            "entities": []
        }
        
        hypothesis = manager.generate_from_pattern("user-1", pattern)
        
        assert hypothesis is None  # Should not generate


# ============================================================================
# DRIFT DETECTOR TESTS
# ============================================================================

class TestDriftDetector:
    """Test drift detection, contradiction detection, and confidence decay."""
    
    def test_initialization(self):
        """Test DriftDetector initialization."""
        config = ConfidenceDecayConfig(
            half_life_days=20.0,
            min_confidence=0.05,
            decay_function="exponential"
        )
        detector = DriftDetector(decay_config=config, drift_threshold=0.6)
        
        assert detector.decay_config.half_life_days == 20.0
        assert detector.drift_threshold == 0.6
    
    def test_detect_drift_no_drift(self):
        """Test drift detection with stable data."""
        detector = DriftDetector(drift_threshold=0.5)
        
        states = [
            {"timestamp": datetime.utcnow() - timedelta(days=40), "state": {"value": 10}},
            {"timestamp": datetime.utcnow() - timedelta(days=20), "state": {"value": 11}},
            {"timestamp": datetime.utcnow() - timedelta(days=5), "state": {"value": 10}},
        ]
        
        report = detector.detect_drift("entity-1", "TestEntity", states, window_days=30)
        
        # Small changes, should not trigger drift
        assert report is None or report.severity < 0.5
    
    def test_detect_drift_significant_change(self):
        """Test drift detection with significant change."""
        detector = DriftDetector(drift_threshold=0.3)
        
        states = [
            {"timestamp": datetime.utcnow() - timedelta(days=40), "state": {"value": 10, "status": "active"}},
            {"timestamp": datetime.utcnow() - timedelta(days=5), "state": {"value": 100, "status": "inactive"}},
        ]
        
        report = detector.detect_drift("entity-1", "TestEntity", states, window_days=30)
        
        assert report is not None
        assert report.entity_id == "entity-1"
        assert report.severity >= 0.3
        assert report.old_state["value"] == 10
        assert report.new_state["value"] == 100
    
    def test_detect_contradictions_none(self):
        """Test contradiction detection with consistent facts."""
        detector = DriftDetector()
        
        facts = [
            {"id": "f1", "subject": "user-1", "predicate": "name", "object": "Alice", "confidence": 0.9, "timestamp": datetime.utcnow()},
            {"id": "f2", "subject": "user-1", "predicate": "age", "object": 30, "confidence": 0.8, "timestamp": datetime.utcnow()},
        ]
        
        contradictions = detector.detect_contradictions(facts)
        
        assert len(contradictions) == 0
    
    def test_detect_contradictions_found(self):
        """Test contradiction detection with conflicting facts."""
        detector = DriftDetector()
        
        facts = [
            {"id": "f1", "subject": "user-1", "predicate": "job", "object": "Engineer", "confidence": 0.9, "timestamp": datetime.utcnow() - timedelta(days=10)},
            {"id": "f2", "subject": "user-1", "predicate": "job", "object": "Designer", "confidence": 0.8, "timestamp": datetime.utcnow()},
        ]
        
        contradictions = detector.detect_contradictions(facts)
        
        assert len(contradictions) == 1
        assert contradictions[0].fact_ids == ["f2", "f1"]  # Most recent first
        assert "Engineer" in contradictions[0].description or "Designer" in contradictions[0].description
    
    def test_contradiction_resolution_favor_recent(self):
        """Test contradiction resolution favoring recent fact."""
        detector = DriftDetector()
        
        facts = [
            {"id": "f1", "subject": "user-1", "predicate": "job", "object": "Engineer", "confidence": 0.8, "timestamp": datetime.utcnow() - timedelta(days=30)},
            {"id": "f2", "subject": "user-1", "predicate": "job", "object": "Designer", "confidence": 0.8, "timestamp": datetime.utcnow()},
        ]
        
        contradiction = Contradiction(
            contradiction_id="c1",
            fact_ids=["f1", "f2"],
            description="Job conflict",
            severity=0.8,
            resolution_strategy="favor_recent"
        )
        
        resolution = detector.resolve_contradiction(contradiction, facts)
        
        assert resolution["preferred_fact_id"] == "f2"  # More recent
        assert "f1" in resolution["superseded_fact_ids"]
    
    def test_contradiction_resolution_favor_confident(self):
        """Test contradiction resolution favoring high confidence."""
        detector = DriftDetector()
        
        facts = [
            {"id": "f1", "subject": "user-1", "predicate": "job", "object": "Engineer", "confidence": 0.9, "timestamp": datetime.utcnow()},
            {"id": "f2", "subject": "user-1", "predicate": "job", "object": "Designer", "confidence": 0.5, "timestamp": datetime.utcnow()},
        ]
        
        contradiction = Contradiction(
            contradiction_id="c1",
            fact_ids=["f1", "f2"],
            description="Job conflict",
            severity=0.7,
            resolution_strategy="favor_confident"
        )
        
        resolution = detector.resolve_contradiction(contradiction, facts)
        
        assert resolution["preferred_fact_id"] == "f1"  # Higher confidence
    
    def test_contradiction_resolution_ask_user(self):
        """Test contradiction resolution requiring user input."""
        detector = DriftDetector()
        
        facts = [
            {"id": "f1", "subject": "user-1", "predicate": "job", "object": "Engineer", "confidence": 0.8, "timestamp": datetime.utcnow()},
            {"id": "f2", "subject": "user-1", "predicate": "job", "object": "Designer", "confidence": 0.8, "timestamp": datetime.utcnow()},
        ]
        
        contradiction = Contradiction(
            contradiction_id="c1",
            fact_ids=["f1", "f2"],
            description="Job conflict",
            severity=0.8,
            resolution_strategy="ask_user"
        )
        
        resolution = detector.resolve_contradiction(contradiction, facts)
        
        assert resolution["requires_user_input"] is True
        assert "preferred_fact_id" not in resolution
    
    def test_apply_confidence_decay_exponential(self):
        """Test exponential confidence decay."""
        config = ConfidenceDecayConfig(
            half_life_days=30.0,
            min_confidence=0.1,
            decay_function="exponential"
        )
        detector = DriftDetector(decay_config=config)
        
        # After 30 days (one half-life), confidence should be ~50%
        decayed = detector.apply_confidence_decay(confidence=1.0, age_days=30.0)
        assert 0.45 <= decayed <= 0.55
        
        # After 60 days (two half-lives), confidence should be ~25%
        decayed = detector.apply_confidence_decay(confidence=1.0, age_days=60.0)
        assert 0.20 <= decayed <= 0.30
    
    def test_apply_confidence_decay_linear(self):
        """Test linear confidence decay."""
        config = ConfidenceDecayConfig(
            half_life_days=30.0,
            min_confidence=0.1,
            decay_function="linear"
        )
        detector = DriftDetector(decay_config=config)
        
        # Linear decay: 0.5 / 30 days = 0.0167 per day
        decayed = detector.apply_confidence_decay(confidence=1.0, age_days=30.0)
        assert 0.45 <= decayed <= 0.55
    
    def test_apply_confidence_decay_min_floor(self):
        """Test that confidence doesn't decay below minimum."""
        config = ConfidenceDecayConfig(
            half_life_days=10.0,
            min_confidence=0.2,
            decay_function="exponential"
        )
        detector = DriftDetector(decay_config=config)
        
        # Very old data
        decayed = detector.apply_confidence_decay(confidence=1.0, age_days=1000.0)
        
        assert decayed >= 0.2  # Should not go below min
