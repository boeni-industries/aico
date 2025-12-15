"""
Schema Learning for World Model

Automatically extracts and evolves schemas from user data patterns.
Phase 6.4: Schema Learning implementation.

Based on statistical pattern detection and frequency analysis.
"""

import uuid
from typing import List, Dict, Any, Set, Optional
from datetime import datetime, UTC
from collections import Counter, defaultdict

from aico.core.logging import get_logger

from .models import Schema, FieldSchema, ValidationResult


logger = get_logger("shared", "world_model.schema_learner")


class SchemaLearner:
    """Learns and evolves schemas from data patterns."""
    
    def __init__(self, min_samples: int = 10, confidence_threshold: float = 0.7):
        """Initialize schema learner.
        
        Args:
            min_samples: Minimum samples needed to learn a schema
            confidence_threshold: Minimum confidence for schema fields
        """
        self.min_samples = min_samples
        self.confidence_threshold = confidence_threshold
        logger.info(f"[SCHEMA_LEARNER] Initialized (min_samples={min_samples}, threshold={confidence_threshold})")
    
    def extract_schema(
        self,
        entity_type: str,
        samples: List[Dict[str, Any]]
    ) -> Schema:
        """Extract schema from data samples.
        
        Args:
            entity_type: Type of entity (e.g., "Person", "Project")
            samples: List of sample data dictionaries
            
        Returns:
            Learned Schema
        """
        if len(samples) < self.min_samples:
            logger.warning(
                f"[SCHEMA_LEARNER] Insufficient samples for {entity_type}: "
                f"{len(samples)} < {self.min_samples}"
            )
        
        # Analyze field presence and types
        field_stats = self._analyze_fields(samples)
        
        # Build field schemas
        fields = {}
        for field_name, stats in field_stats.items():
            field_schema = self._create_field_schema(field_name, stats, len(samples))
            if field_schema:
                fields[field_name] = field_schema
        
        # Calculate overall confidence
        confidence = self._calculate_schema_confidence(field_stats, len(samples))
        
        schema = Schema(
            schema_id=str(uuid.uuid4()),
            version="1.0.0",
            entity_type=entity_type,
            fields=fields,
            sample_count=len(samples),
            confidence=confidence,
        )
        
        logger.info(
            f"[SCHEMA_LEARNER] Extracted schema for {entity_type}: "
            f"{len(fields)} fields, confidence={confidence:.2f}"
        )
        
        return schema
    
    def validate_schema(
        self,
        schema: Schema,
        data: Dict[str, Any]
    ) -> ValidationResult:
        """Validate data against schema.
        
        Args:
            schema: Schema to validate against
            data: Data to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field_name, field_schema in schema.fields.items():
            if field_schema.required and field_name not in data:
                errors.append(f"Missing required field: {field_name}")
        
        # Check field types and constraints
        for field_name, value in data.items():
            if field_name not in schema.fields:
                warnings.append(f"Unknown field: {field_name}")
                continue
            
            field_schema = schema.fields[field_name]
            
            # Type check
            expected_type = field_schema.field_type
            actual_type = self._infer_type(value)
            
            if actual_type != expected_type:
                errors.append(
                    f"Type mismatch for {field_name}: "
                    f"expected {expected_type}, got {actual_type}"
                )
            
            # Constraint checks
            constraint_errors = self._check_constraints(field_name, value, field_schema.constraints)
            errors.extend(constraint_errors)
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
        )
    
    def evolve_schema(
        self,
        old_schema: Schema,
        new_samples: List[Dict[str, Any]]
    ) -> Schema:
        """Evolve schema based on new data.
        
        Args:
            old_schema: Existing schema
            new_samples: New data samples
            
        Returns:
            Evolved Schema with updated version
        """
        # Extract schema from new samples
        new_schema = self.extract_schema(old_schema.entity_type, new_samples)
        
        # Merge schemas
        merged_fields = dict(old_schema.fields)
        
        # Add new fields
        for field_name, new_field in new_schema.fields.items():
            if field_name not in merged_fields:
                merged_fields[field_name] = new_field
                logger.info(f"[SCHEMA_LEARNER] Added new field: {field_name}")
            else:
                # Update existing field if new data suggests changes
                old_field = merged_fields[field_name]
                if new_field.field_type != old_field.field_type:
                    logger.warning(
                        f"[SCHEMA_LEARNER] Type conflict for {field_name}: "
                        f"{old_field.field_type} vs {new_field.field_type}"
                    )
        
        # Determine version bump
        new_version = self._bump_version(
            old_schema.version,
            has_new_fields=len(new_schema.fields) > len(old_schema.fields),
            has_breaking_changes=False  # Could be enhanced
        )
        
        evolved_schema = Schema(
            schema_id=old_schema.schema_id,
            version=new_version,
            entity_type=old_schema.entity_type,
            fields=merged_fields,
            created_at=old_schema.created_at,
            updated_at=datetime.now(UTC),
            sample_count=old_schema.sample_count + len(new_samples),
            confidence=min(old_schema.confidence + 0.1, 1.0),  # Increase confidence
        )
        
        logger.info(
            f"[SCHEMA_LEARNER] Evolved schema {old_schema.entity_type}: "
            f"{old_schema.version} → {new_version}"
        )
        
        return evolved_schema
    
    def detect_schema_drift(
        self,
        schema: Schema,
        recent_samples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect drift between schema and recent data.
        
        Args:
            schema: Current schema
            recent_samples: Recent data samples
            
        Returns:
            Drift report dictionary
        """
        if not recent_samples:
            return {"has_drift": False}
        
        # Analyze recent samples
        field_stats = self._analyze_fields(recent_samples)
        
        # Compare with schema
        new_fields = set(field_stats.keys()) - set(schema.fields.keys())
        missing_fields = set(schema.fields.keys()) - set(field_stats.keys())
        
        type_mismatches = []
        for field_name in set(field_stats.keys()) & set(schema.fields.keys()):
            stats = field_stats[field_name]
            schema_type = schema.fields[field_name].field_type
            observed_type = stats["dominant_type"]
            
            if observed_type != schema_type:
                type_mismatches.append({
                    "field": field_name,
                    "expected": schema_type,
                    "observed": observed_type,
                })
        
        has_drift = bool(new_fields or missing_fields or type_mismatches)
        
        return {
            "has_drift": has_drift,
            "new_fields": list(new_fields),
            "missing_fields": list(missing_fields),
            "type_mismatches": type_mismatches,
            "sample_count": len(recent_samples),
        }
    
    # Private helper methods
    
    def _analyze_fields(self, samples: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Analyze field statistics across samples."""
        field_stats = defaultdict(lambda: {
            "count": 0,
            "types": Counter(),
            "values": [],
        })
        
        for sample in samples:
            for field_name, value in sample.items():
                stats = field_stats[field_name]
                stats["count"] += 1
                stats["types"][self._infer_type(value)] += 1
                stats["values"].append(value)
        
        # Calculate dominant type and presence ratio
        for field_name, stats in field_stats.items():
            stats["presence_ratio"] = stats["count"] / len(samples)
            stats["dominant_type"] = stats["types"].most_common(1)[0][0] if stats["types"] else "unknown"
        
        return dict(field_stats)
    
    def _create_field_schema(
        self,
        field_name: str,
        stats: Dict[str, Any],
        total_samples: int
    ) -> Optional[FieldSchema]:
        """Create field schema from statistics."""
        presence_ratio = stats["presence_ratio"]
        
        # Skip fields that appear too infrequently
        if presence_ratio < 0.1:  # Less than 10% presence
            return None
        
        field_type = stats["dominant_type"]
        required = presence_ratio >= 0.9  # 90%+ presence = required
        
        # Extract examples (up to 3 unique values)
        # Handle unhashable types (lists, dicts) by converting to strings
        try:
            examples = list(set(stats["values"]))[:3]
        except TypeError:
            # Unhashable types - use first 3 values
            examples = stats["values"][:3]
        
        # Infer constraints
        constraints = {}
        if field_type == "number":
            values = [v for v in stats["values"] if isinstance(v, (int, float))]
            if values:
                constraints["min"] = min(values)
                constraints["max"] = max(values)
        elif field_type == "string":
            values = [v for v in stats["values"] if isinstance(v, str)]
            if values:
                constraints["min_length"] = min(len(v) for v in values)
                constraints["max_length"] = max(len(v) for v in values)
        
        return FieldSchema(
            name=field_name,
            field_type=field_type,
            required=required,
            constraints=constraints,
            examples=examples,
        )
    
    def _calculate_schema_confidence(
        self,
        field_stats: Dict[str, Dict[str, Any]],
        total_samples: int
    ) -> float:
        """Calculate overall schema confidence."""
        if not field_stats:
            return 0.0
        
        # Confidence based on:
        # 1. Sample count (more samples = higher confidence)
        # 2. Field consistency (higher presence ratios = higher confidence)
        # 3. Type consistency (dominant type frequency)
        
        sample_confidence = min(total_samples / (self.min_samples * 2), 1.0)
        
        presence_scores = [stats["presence_ratio"] for stats in field_stats.values()]
        presence_confidence = sum(presence_scores) / len(presence_scores) if presence_scores else 0.0
        
        type_scores = []
        for stats in field_stats.values():
            if stats["types"]:
                dominant_count = stats["types"].most_common(1)[0][1]
                type_consistency = dominant_count / stats["count"]
                type_scores.append(type_consistency)
        type_confidence = sum(type_scores) / len(type_scores) if type_scores else 0.0
        
        # Weighted average
        confidence = (
            sample_confidence * 0.3 +
            presence_confidence * 0.4 +
            type_confidence * 0.3
        )
        
        return min(confidence, 1.0)
    
    def _infer_type(self, value: Any) -> str:
        """Infer field type from value."""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "number"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"
    
    def _check_constraints(
        self,
        field_name: str,
        value: Any,
        constraints: Dict[str, Any]
    ) -> List[str]:
        """Check value against constraints."""
        errors = []
        
        if isinstance(value, (int, float)):
            if "min" in constraints and value < constraints["min"]:
                errors.append(f"{field_name}: value {value} < min {constraints['min']}")
            if "max" in constraints and value > constraints["max"]:
                errors.append(f"{field_name}: value {value} > max {constraints['max']}")
        
        elif isinstance(value, str):
            if "min_length" in constraints and len(value) < constraints["min_length"]:
                errors.append(f"{field_name}: length {len(value)} < min {constraints['min_length']}")
            if "max_length" in constraints and len(value) > constraints["max_length"]:
                errors.append(f"{field_name}: length {len(value)} > max {constraints['max_length']}")
        
        return errors
    
    def _bump_version(
        self,
        current_version: str,
        has_new_fields: bool,
        has_breaking_changes: bool
    ) -> str:
        """Bump semantic version."""
        try:
            major, minor, patch = map(int, current_version.split("."))
            
            if has_breaking_changes:
                major += 1
                minor = 0
                patch = 0
            elif has_new_fields:
                minor += 1
                patch = 0
            else:
                patch += 1
            
            return f"{major}.{minor}.{patch}"
        except:
            return "1.0.0"
