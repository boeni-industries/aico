"""
AICO Advanced Fact Extractor

State-of-the-art fact extraction using GLiNER + relation extraction for conversation analysis.
Extracts structured facts with confidence scoring and relationship detection.

Key Features:
- GLiNER-based entity extraction (any entity type, no predefined categories)
- Relation extraction between entities
- Context-aware fact synthesis
- Confidence scoring and provenance tracking
- Lightweight, local processing (no external APIs)

Architecture:
- GLiNER: Generalist entity extraction (NAACL 2024)
- Pattern-based relation detection with context awareness
- Structured fact synthesis with metadata enrichment
- Integration with AICO's modelservice architecture
"""

import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger

logger = get_logger("shared", "ai.fact_extractor")


class FactType(Enum):
    """Types of facts that can be extracted from conversations."""
    IDENTITY = "identity"           # Names, titles, roles
    PREFERENCE = "preference"       # Likes, dislikes, interests
    LOCATION = "location"          # Places, addresses, origins
    TEMPORAL = "temporal"          # Dates, times, schedules
    RELATIONSHIP = "relationship"   # Family, friends, colleagues
    DEMOGRAPHIC = "demographic"     # Age, occupation, background
    CONTACT = "contact"            # Email, phone, social media
    EXPERIENCE = "experience"      # Skills, education, work
    OPINION = "opinion"            # Views, beliefs, attitudes
    GOAL = "goal"                  # Aspirations, plans, objectives


@dataclass
class ExtractedEntity:
    """An entity extracted from text with metadata."""
    text: str
    label: str
    start: int
    end: int
    confidence: float


@dataclass
class ExtractedRelation:
    """A relationship between two entities."""
    entity1: ExtractedEntity
    entity2: Optional[ExtractedEntity]
    relation_type: FactType
    confidence: float
    pattern_matched: str
    context: str


@dataclass
class ExtractedFact:
    """A structured fact extracted from conversation."""
    content: str
    fact_type: FactType
    confidence: float
    entities: List[ExtractedEntity]
    relations: List[ExtractedRelation]
    extraction_method: str
    source_segment_id: str
    metadata: Dict[str, Any]


class AdvancedFactExtractor:
    """
    Advanced fact extraction using GLiNER + relation extraction.
    
    Integrates with AICO's modelservice architecture for lightweight,
    local fact extraction from conversation segments.
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self.logger = logger
        
        # Modelservice client for NER requests
        self._modelservice_client = None
        
        # Dynamic entity types for conversation analysis
        self.conversation_entity_types = [
            "person", "organization", "location", "date", "time",
            "preference", "skill", "hobby", "relationship", "goal",
            "experience", "opinion", "contact_info", "demographic",
            "food", "activity", "place", "event", "emotion", "job",
            "family_member", "friend", "colleague", "interest"
        ]
        
        # Relation patterns for different fact types
        self.relation_patterns = {
            FactType.IDENTITY: [
                r"(?:my name is|i'm|i am|call me|they call me)\s+([^,.!?]+)",
                r"i'm\s+([^,.!?]+?)(?:\s+and|\s*[,.!?]|$)",
                r"(?:this is|i'm)\s+([^,.!?]+)",
            ],
            FactType.PREFERENCE: [
                r"i\s+(?:love|like|enjoy|prefer|adore|am into)\s+([^,.!?]+)",
                r"([^,.!?]+)\s+is\s+my\s+favorite",
                r"i\s+(?:hate|dislike|can't stand)\s+([^,.!?]+)",
                r"i'm\s+(?:passionate about|interested in|into)\s+([^,.!?]+)",
            ],
            FactType.LOCATION: [
                r"i\s+(?:live|work|am|stay)\s+in\s+([^,.!?]+)",
                r"i'm\s+from\s+([^,.!?]+)",
                r"(?:based|located)\s+in\s+([^,.!?]+)",
                r"i\s+(?:grew up|was born)\s+in\s+([^,.!?]+)",
            ],
            FactType.RELATIONSHIP: [
                r"my\s+([^,.!?]+?)\s+is\s+([^,.!?]+)",
                r"([^,.!?]+)\s+is\s+my\s+([^,.!?]+)",
                r"i\s+(?:have|got)\s+a\s+([^,.!?]+?)(?:\s+named\s+([^,.!?]+))?",
            ],
            FactType.DEMOGRAPHIC: [
                r"i'm\s+(\d+)\s+years?\s+old",
                r"i\s+work\s+as\s+(?:a|an)?\s*([^,.!?]+)",
                r"i'm\s+(?:a|an)\s+([^,.!?]+?)(?:\s+[,.!?]|$)",
                r"my\s+job\s+is\s+([^,.!?]+)",
            ],
            FactType.EXPERIENCE: [
                r"i\s+(?:studied|graduated from|went to)\s+([^,.!?]+)",
                r"i\s+(?:can|know how to)\s+([^,.!?]+)",
                r"i\s+have\s+experience\s+(?:in|with)\s+([^,.!?]+)",
                r"i\s+used to\s+([^,.!?]+)",
            ],
            FactType.TEMPORAL: [
                r"(?:on|in|at|since|until|from)\s+([^,.!?]+)",
                r"(?:every|each)\s+([^,.!?]+)",
                r"(?:yesterday|today|tomorrow|last|next)\s+([^,.!?]*)",
            ]
        }
    
    async def initialize(self):
        """Initialize the fact extractor with modelservice integration."""
        try:
            # Import modelservice client for NER requests
            from backend.services.modelservice_client import ModelServiceClient
            
            # Initialize modelservice client
            self._modelservice_client = ModelServiceClient(self.config)
            
            self.logger.info("🔍 [FACT_EXTRACTOR] Modelservice client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"🔍 [FACT_EXTRACTOR] Failed to initialize: {e}")
            raise
    
    async def extract_facts(self, conversation_segment) -> List[ExtractedFact]:
        """
        Extract structured facts from a conversation segment.
        
        Args:
            conversation_segment: ConversationSegment with text and metadata
            
        Returns:
            List of ExtractedFact objects with confidence scores
        """
        if not self._modelservice_client:
            await self.initialize()
        
        text = conversation_segment.text
        segment_id = getattr(conversation_segment, 'id', 'unknown')
        
        self.logger.debug(f"🔍 [FACT_EXTRACTOR] Extracting facts from segment: {text[:100]}...")
        
        try:
            # 1. Extract entities using GLiNER
            entities = await self._extract_entities(text)
            
            # 2. Extract relations using pattern matching + context
            relations = await self._extract_relations(text, entities)
            
            # 3. Synthesize structured facts
            facts = await self._synthesize_facts(text, entities, relations, segment_id)
            
            self.logger.info(f"🔍 [FACT_EXTRACTOR] Extracted {len(facts)} facts from segment")
            return facts
            
        except Exception as e:
            self.logger.error(f"🔍 [FACT_EXTRACTOR] Failed to extract facts: {e}")
            return []
    
    async def _extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using modelservice NER endpoint."""
        try:
            # Use modelservice NER endpoint (which uses GLiNER internally)
            ner_result = await self._modelservice_client.get_ner_entities(text)
            
            if not ner_result.get("success", False):
                self.logger.error(f"🔍 [ENTITIES] NER request failed: {ner_result.get('error', 'Unknown error')}")
                return []
            
            # Convert modelservice NER result to our format
            entities = []
            ner_data = ner_result.get("data", {}).get("entities", {})
            
            for entity_type, entity_list in ner_data.items():
                for entity_text in entity_list:
                    # Note: modelservice NER doesn't return positions/confidence, so we use defaults
                    entities.append(ExtractedEntity(
                        text=entity_text,
                        label=entity_type.lower(),
                        start=0,  # Position not available from modelservice
                        end=len(entity_text),
                        confidence=0.8  # Default confidence since not returned by modelservice
                    ))
            
            self.logger.debug(f"🔍 [ENTITIES] Extracted {len(entities)} entities: {[e.text for e in entities]}")
            return entities
            
        except Exception as e:
            self.logger.error(f"🔍 [ENTITIES] Failed to extract entities: {e}")
            return []
    
    async def _extract_relations(self, text: str, entities: List[ExtractedEntity]) -> List[ExtractedRelation]:
        """Extract relationships using pattern matching with context awareness."""
        relations = []
        text_lower = text.lower()
        
        try:
            # Pattern-based relation extraction
            for fact_type, patterns in self.relation_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                    
                    for match in matches:
                        # Find relevant entities in the match context
                        match_start, match_end = match.span()
                        context = text[max(0, match_start-50):min(len(text), match_end+50)]
                        
                        # Get entities that overlap with the match
                        relevant_entities = self._find_entities_in_range(
                            entities, match_start, match_end
                        )
                        
                        if relevant_entities:
                            relation = ExtractedRelation(
                                entity1=relevant_entities[0],
                                entity2=relevant_entities[1] if len(relevant_entities) > 1 else None,
                                relation_type=fact_type,
                                confidence=self._calculate_pattern_confidence(pattern, context),
                                pattern_matched=pattern,
                                context=context.strip()
                            )
                            relations.append(relation)
            
            self.logger.debug(f"🔍 [RELATIONS] Extracted {len(relations)} relations")
            return relations
            
        except Exception as e:
            self.logger.error(f"🔍 [RELATIONS] Failed to extract relations: {e}")
            return []
    
    def _find_entities_in_range(self, entities: List[ExtractedEntity], start: int, end: int) -> List[ExtractedEntity]:
        """Find entities that overlap with a text range."""
        relevant = []
        for entity in entities:
            if (entity.start >= start and entity.start <= end) or \
               (entity.end >= start and entity.end <= end) or \
               (entity.start <= start and entity.end >= end):
                relevant.append(entity)
        return relevant
    
    def _calculate_pattern_confidence(self, pattern: str, context: str) -> float:
        """Calculate confidence score for a pattern match."""
        base_confidence = 0.7
        
        # Boost confidence for explicit patterns
        if any(explicit in pattern for explicit in ["my name is", "i am", "i live"]):
            base_confidence += 0.2
        
        # Boost for first-person statements
        if any(pronoun in context.lower() for pronoun in ["i ", "my ", "me "]):
            base_confidence += 0.1
        
        # Reduce for uncertain patterns
        if any(uncertain in pattern for uncertain in ["(?:", ".*", ".+"]):
            base_confidence -= 0.1
        
        return min(0.95, max(0.3, base_confidence))
    
    async def _synthesize_facts(self, text: str, entities: List[ExtractedEntity], 
                              relations: List[ExtractedRelation], segment_id: str) -> List[ExtractedFact]:
        """Synthesize structured facts from entities and relations."""
        facts = []
        
        try:
            # Create facts from relations
            for relation in relations:
                fact = self._create_fact_from_relation(relation, segment_id)
                if fact:
                    facts.append(fact)
            
            # Handle standalone entities (no relations found)
            used_entities = set()
            for relation in relations:
                used_entities.add(relation.entity1.text)
                if relation.entity2:
                    used_entities.add(relation.entity2.text)
            
            for entity in entities:
                if entity.text not in used_entities and entity.confidence > 0.5:
                    fact = self._create_fact_from_entity(entity, text, segment_id)
                    if fact:
                        facts.append(fact)
            
            return facts
            
        except Exception as e:
            self.logger.error(f"🔍 [SYNTHESIS] Failed to synthesize facts: {e}")
            return []
    
    def _create_fact_from_relation(self, relation: ExtractedRelation, segment_id: str) -> Optional[ExtractedFact]:
        """Create a structured fact from a relation."""
        try:
            fact_templates = {
                FactType.IDENTITY: "User's name is {entity1}",
                FactType.PREFERENCE: "User likes {entity1}",
                FactType.LOCATION: "User is located in {entity1}",
                FactType.RELATIONSHIP: "User's {entity1} is {entity2}",
                FactType.DEMOGRAPHIC: "User is {entity1}",
                FactType.EXPERIENCE: "User has experience with {entity1}",
                FactType.TEMPORAL: "User mentioned {entity1}",
            }
            
            template = fact_templates.get(relation.relation_type)
            if not template:
                return None
            
            # Format the fact content
            content = template.format(
                entity1=relation.entity1.text,
                entity2=relation.entity2.text if relation.entity2 else ""
            ).strip()
            
            # Create metadata
            metadata = {
                "pattern_matched": relation.pattern_matched,
                "context": relation.context,
                "entity_confidence": relation.entity1.confidence,
                "relation_confidence": relation.confidence,
                "extraction_timestamp": datetime.utcnow().isoformat()
            }
            
            return ExtractedFact(
                content=content,
                fact_type=relation.relation_type,
                confidence=min(relation.confidence, relation.entity1.confidence),
                entities=[relation.entity1] + ([relation.entity2] if relation.entity2 else []),
                relations=[relation],
                extraction_method="relation_synthesis",
                source_segment_id=segment_id,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"🔍 [FACT_CREATION] Failed to create fact from relation: {e}")
            return None
    
    def _create_fact_from_entity(self, entity: ExtractedEntity, text: str, segment_id: str) -> Optional[ExtractedFact]:
        """Create a fact from a standalone entity."""
        try:
            # Only create facts for high-confidence, meaningful entities
            if entity.confidence < 0.6:
                return None
            
            # Determine fact type based on entity label
            fact_type_mapping = {
                "person": FactType.IDENTITY,
                "location": FactType.LOCATION,
                "organization": FactType.EXPERIENCE,
                "date": FactType.TEMPORAL,
                "preference": FactType.PREFERENCE,
                "skill": FactType.EXPERIENCE,
                "hobby": FactType.PREFERENCE,
            }
            
            fact_type = fact_type_mapping.get(entity.label.lower(), FactType.EXPERIENCE)
            
            # Create generic fact content
            content = f"User mentioned {entity.text}"
            
            metadata = {
                "entity_label": entity.label,
                "entity_confidence": entity.confidence,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "standalone_entity": True
            }
            
            return ExtractedFact(
                content=content,
                fact_type=fact_type,
                confidence=entity.confidence * 0.8,  # Reduce confidence for standalone entities
                entities=[entity],
                relations=[],
                extraction_method="entity_inference",
                source_segment_id=segment_id,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"🔍 [FACT_CREATION] Failed to create fact from entity: {e}")
            return None
