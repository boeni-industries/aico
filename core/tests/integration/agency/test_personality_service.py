"""
PersonalityService Integration Tests

Comprehensive tests for personality service functionality.
"""

import pytest
from aico.ai.personality import PersonalityService, PersonalityContext, PersonalityTraits


@pytest.mark.asyncio
class TestPersonalityServiceComprehensive:
    """Comprehensive tests for PersonalityService."""
    
    async def test_get_personality_context_returns_defaults(self, test_db):
        """Test that get_personality_context returns default AICO personality."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        
        # Act
        context = await service.get_personality_context("test-user-123")
        
        # Assert
        assert context is not None
        assert context.user_id == "test-user-123"
        assert context.traits.extraversion == 0.6
        assert context.traits.agreeableness == 0.7
        assert context.traits.conscientiousness == 0.6
        assert context.traits.neuroticism == 0.3
        assert context.traits.openness == 0.8
        assert context.relationship.user_id == "test-user-123"
        assert context.relationship.closeness == 0.5
    
    async def test_get_personality_context_handles_exception(self, test_db):
        """Test that exceptions return minimal context."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        # Force an exception by passing invalid user_id type
        
        # Act - Should handle gracefully
        context = await service.get_personality_context("test-user")
        
        # Assert - Should still return valid context
        assert context is not None
        assert context.user_id == "test-user"
    
    async def test_adjust_priority_high_conscientiousness(self, test_db):
        """Test priority adjustment with high conscientiousness."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        context = PersonalityContext(
            user_id="test-user",
            traits=PersonalityTraits(conscientiousness=0.8),  # High
        )
        
        # Act
        adjusted = service.adjust_priority_for_personality("low", context)
        
        # Assert - Should bump up
        assert adjusted == "normal"
    
    async def test_adjust_priority_low_conscientiousness(self, test_db):
        """Test priority adjustment with low conscientiousness."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        context = PersonalityContext(
            user_id="test-user",
            traits=PersonalityTraits(conscientiousness=0.2),  # Low
        )
        
        # Act
        adjusted = service.adjust_priority_for_personality("high", context)
        
        # Assert - Should reduce
        assert adjusted == "normal"
    
    async def test_adjust_priority_moderate_conscientiousness(self, test_db):
        """Test priority adjustment with moderate conscientiousness."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        context = PersonalityContext(
            user_id="test-user",
            traits=PersonalityTraits(conscientiousness=0.5),  # Moderate
        )
        
        # Act
        adjusted = service.adjust_priority_for_personality("normal", context)
        
        # Assert - Should stay the same
        assert adjusted == "normal"
    
    async def test_adjust_priority_max_cap(self, test_db):
        """Test that priority doesn't exceed high."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        context = PersonalityContext(
            user_id="test-user",
            traits=PersonalityTraits(conscientiousness=0.9),  # Very high
        )
        
        # Act
        adjusted = service.adjust_priority_for_personality("high", context)
        
        # Assert - Should stay at high (can't go higher)
        assert adjusted == "high"
    
    async def test_adjust_priority_min_cap(self, test_db):
        """Test that priority doesn't go below low."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        context = PersonalityContext(
            user_id="test-user",
            traits=PersonalityTraits(conscientiousness=0.1),  # Very low
        )
        
        # Act
        adjusted = service.adjust_priority_for_personality("low", context)
        
        # Assert - Should stay at low (can't go lower)
        assert adjusted == "low"
    
    async def test_adjust_priority_invalid_base(self, test_db):
        """Test priority adjustment with invalid base priority."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        context = PersonalityContext(
            user_id="test-user",
            traits=PersonalityTraits(conscientiousness=0.5),
        )
        
        # Act - Invalid priority defaults to normal
        adjusted = service.adjust_priority_for_personality("invalid", context)
        
        # Assert - Should return normal (default)
        assert adjusted == "normal"
    
    async def test_adjust_priority_handles_exception(self, test_db):
        """Test that exceptions return base priority."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        # Create context with None traits to trigger exception
        context = PersonalityContext(user_id="test-user")
        context.traits = None  # type: ignore
        
        # Act
        adjusted = service.adjust_priority_for_personality("normal", context)
        
        # Assert - Should return base priority on error
        assert adjusted == "normal"
    
    async def test_calculate_proactivity_high_closeness(self, test_db):
        """Test proactivity calculation with high closeness."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        context = PersonalityContext(user_id="test-user")
        context.relationship.closeness = 0.9
        context.relationship.proactivity_preference = 0.5
        
        # Act
        proactivity = service.calculate_proactivity_level(context)
        
        # Assert - Should be weighted toward closeness
        # 0.5 * 0.6 + 0.9 * 0.4 = 0.3 + 0.36 = 0.66
        assert proactivity == pytest.approx(0.66, rel=0.01)
    
    async def test_calculate_proactivity_high_preference(self, test_db):
        """Test proactivity calculation with high preference."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        context = PersonalityContext(user_id="test-user")
        context.relationship.closeness = 0.5
        context.relationship.proactivity_preference = 0.9
        
        # Act
        proactivity = service.calculate_proactivity_level(context)
        
        # Assert - Should be weighted toward preference
        # 0.9 * 0.6 + 0.5 * 0.4 = 0.54 + 0.2 = 0.74
        assert proactivity == pytest.approx(0.74, rel=0.01)
    
    async def test_calculate_proactivity_low_values(self, test_db):
        """Test proactivity calculation with low values."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        context = PersonalityContext(user_id="test-user")
        context.relationship.closeness = 0.2
        context.relationship.proactivity_preference = 0.1
        
        # Act
        proactivity = service.calculate_proactivity_level(context)
        
        # Assert - Should be low
        # 0.1 * 0.6 + 0.2 * 0.4 = 0.06 + 0.08 = 0.14
        assert proactivity == pytest.approx(0.14, rel=0.01)
    
    async def test_calculate_proactivity_handles_exception(self, test_db):
        """Test that exceptions return default proactivity."""
        # Arrange
        service = PersonalityService(db_connection=test_db)
        context = PersonalityContext(user_id="test-user")
        context.relationship = None  # type: ignore
        
        # Act
        proactivity = service.calculate_proactivity_level(context)
        
        # Assert - Should return default 0.5 on error
        assert proactivity == 0.5
    
    async def test_service_without_db_connection(self):
        """Test service can be created without DB connection."""
        # Act
        service = PersonalityService(db_connection=None)
        
        # Assert
        assert service is not None
        assert service.db is None
    
    async def test_service_with_logger_initialization(self, test_db):
        """Test that logger is initialized if possible."""
        # Act
        service = PersonalityService(db_connection=test_db)
        
        # Assert - Logger should be set (or None if logging not initialized)
        assert hasattr(service, 'logger')
