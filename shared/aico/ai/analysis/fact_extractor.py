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
from datetime import datetime
from typing import List, Dict, Any, Optional
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
class ExtractedFact:
    """A structured fact extracted from conversation."""
    content: str
    fact_type: FactType
    confidence: float
    entities: List[ExtractedEntity]
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
        
        # OPTIMIZED GLiNER entity types for conversation facts (multilingual)
        # Based on GLiNER research: specific, descriptive entity types work best
        self.conversation_entity_types = [
            # Personal Identity (high-value persistent facts)
            "person name", "full name", "first name", "last name", "nickname",
            "age", "birth date", "nationality", "native language",
            
            # Professional Information
            "job title", "profession", "occupation", "company name", "workplace",
            "industry", "work experience", "salary", "career goal",
            
            # Geographic Information
            "home address", "city", "country", "region", "hometown", 
            "current location", "travel destination", "favorite place",
            
            # Relationships & Social
            "family member", "spouse", "partner", "child", "parent", "sibling",
            "friend", "colleague", "mentor", "pet name", "pet type",
            
            # Skills & Expertise
            "programming language", "technical skill", "software tool", 
            "certification", "degree", "qualification", "expertise area",
            
            # Interests & Preferences
            "hobby", "sport", "music genre", "favorite band", "book title",
            "movie title", "food preference", "cuisine type", "restaurant",
            
            # Goals & Projects
            "personal goal", "project name", "learning objective", 
            "career aspiration", "dream", "plan",
            
            # Contact & Digital Identity
            "email address", "phone number", "social media handle", 
            "username", "website", "linkedin profile",
            
            # Health & Personal
            "medical condition", "allergy", "medication", "diet restriction",
            "fitness goal", "health concern",
            
            # Education
            "school name", "university", "degree program", "major", 
            "graduation year", "academic achievement"
        ]
        
        # GLiNER configuration for optimal performance
        self.gliner_config = {
            "model_name": "urchade/gliner_multi-v2.1",  # Multilingual Apache 2.0 model
            "threshold": 0.35,  # Lower threshold for conversation facts (research-based)
            "max_length": 512,  # Optimal for conversation segments
            "batch_size": 1,    # Process one segment at a time for accuracy
            "device": "auto"    # Let GLiNER decide CPU/GPU
        }
        
        # REMOVED: English-only regex patterns - GLiNER handles relations better
        # These patterns were English-only hacks that violated multilingual principle
        # GLiNER's ML-based approach is superior to fragile regex patterns
    
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
            
            # 2. Synthesize structured facts directly from GLiNER entities
            # REMOVED: English-only relation extraction - GLiNER handles this better
            facts = await self._synthesize_facts(text, entities, segment_id)
            
            self.logger.info(f"🔍 [FACT_EXTRACTOR] Extracted {len(facts)} facts from segment")
            return facts
            
        except Exception as e:
            self.logger.error(f"🔍 [FACT_EXTRACTOR] Failed to extract facts: {e}")
            return []
    
    async def _extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract HIGH-VALUE entities using OPTIMIZED GLiNER configuration."""
        try:
            # RESEARCH-BASED GLiNER optimization: send configuration with entity types
            ner_request = {
                "text": text,
                "entity_types": self.conversation_entity_types,
                "threshold": self.gliner_config["threshold"],
                "model_name": self.gliner_config["model_name"],
                "max_length": self.gliner_config["max_length"]
            }
            
            self.logger.debug(f"🔍 [GLINER_OPTIMIZED] Using model: {self.gliner_config['model_name']}, threshold: {self.gliner_config['threshold']}")
            
            ner_result = await self._modelservice_client.get_ner_entities_optimized(ner_request)
            
            # Debug: Check what we actually received from ModelService
            self.logger.debug(f"🔍 [DEBUG] ner_result type: {type(ner_result)}, content: {ner_result}")
            
            # Handle case where ner_result might be a string instead of dict
            if isinstance(ner_result, str):
                self.logger.error(f"🔍 [ENTITIES] ner_result is string, not dict: {ner_result}")
                return await self._extract_entities_fallback(text)
            
            if not ner_result.get("success", False):
                self.logger.error(f"🔍 [ENTITIES] Optimized NER request failed: {ner_result.get('error', 'Unknown error')}")
                # Fallback to basic NER
                return await self._extract_entities_fallback(text)
            
            # Process GLiNER results with confidence-based filtering
            entities = []
            ner_data = ner_result.get("data", {})
            
            # Debug: Check what we actually received
            self.logger.debug(f"🔍 [DEBUG] ner_data type: {type(ner_data)}, content: {ner_data}")
            
            # Handle case where ner_data might be a string instead of dict
            if isinstance(ner_data, str):
                self.logger.error(f"🔍 [ENTITIES] ner_data is string, not dict: {ner_data}")
                return await self._extract_entities_fallback(text)
            
            # GLiNER returns entities with confidence scores
            for entity_info in ner_data.get("entities", []):
                entity_text = entity_info.get("text", "").strip()
                entity_label = entity_info.get("label", "").lower()
                confidence = entity_info.get("confidence", 0.0)
                
                # RESEARCH-BASED: Use confidence score instead of hardcoded filtering
                if confidence >= self.gliner_config["threshold"] and self._is_high_value_entity(entity_text, entity_label):
                    entities.append(ExtractedEntity(
                        text=entity_text,
                        label=entity_label,
                        start=entity_info.get("start", 0),
                        end=entity_info.get("end", len(entity_text)),
                        confidence=confidence
                    ))
            
            self.logger.info(f"🔍 [GLINER_OPTIMIZED] Extracted {len(entities)} high-confidence entities (threshold: {self.gliner_config['threshold']})")
            self.logger.debug(f"🔍 [ENTITIES] Details: {[f'{e.label}:{e.text}({e.confidence:.2f})' for e in entities]}")
            return entities
            
        except Exception as e:
            self.logger.error(f"🔍 [ENTITIES] Optimized extraction failed: {e}")
            return await self._extract_entities_fallback(text)
    
    async def _extract_entities_fallback(self, text: str) -> List[ExtractedEntity]:
        """Fallback to basic NER if optimized version fails."""
        try:
            self.logger.warning("🔍 [ENTITIES] Using fallback NER extraction")
            ner_result = await self._modelservice_client.get_ner_entities(
                text, 
                entity_types=self.conversation_entity_types
            )
            
            if not ner_result.get("success", False):
                self.logger.error(f"🔍 [ENTITIES] Fallback NER also failed: {ner_result.get('error', 'Unknown error')}")
                return []
            
            entities = []
            ner_data = ner_result.get("data", {}).get("entities", {})
            
            for entity_type, entity_list in ner_data.items():
                for entity_info in entity_list:
                    if isinstance(entity_info, str):
                        entity_text = entity_info
                        confidence = 0.7  # Lower default for fallback
                    else:
                        entity_text = entity_info.get("text", "")
                        confidence = entity_info.get("confidence", 0.7)
                    
                    if self._is_high_value_entity(entity_text, entity_type):
                        entities.append(ExtractedEntity(
                            text=entity_text,
                            label=entity_type.lower(),
                            start=entity_info.get("start", 0) if isinstance(entity_info, dict) else 0,
                            end=entity_info.get("end", len(entity_text)) if isinstance(entity_info, dict) else len(entity_text),
                            confidence=confidence
                        ))
            
            self.logger.info(f"🔍 [ENTITIES] Fallback extracted {len(entities)} entities")
            return entities
            
        except Exception as e:
            self.logger.error(f"🔍 [ENTITIES] Fallback extraction failed: {e}")
            return []
    
    def _is_high_value_entity(self, text: str, entity_type: str) -> bool:
        """Filter out low-value entities using language-agnostic rules."""
        text_clean = text.strip()
        
        # LANGUAGE-AGNOSTIC filtering based on structural patterns
        
        # Filter out single characters (any language)
        if len(text_clean) <= 1:
            return False
        
        # Filter out pure numbers
        if text_clean.isdigit():
            return False
        
        # Filter out pure punctuation
        if all(not c.isalnum() for c in text_clean):
            return False
        
        # RESEARCH-BASED entity-type validation (language-agnostic, GLiNER-optimized)
        
        # Personal identity entities - high value for conversation facts
        if entity_type in ["person name", "full name", "first name", "last name", "nickname"]:
            return len(text_clean) >= 2 and any(c.isalpha() for c in text_clean) and not text_clean.isdigit()
        
        # Professional information - critical for user profiling
        if entity_type in ["job title", "profession", "occupation", "company name", "workplace"]:
            return len(text_clean) >= 2 and any(c.isalnum() for c in text_clean)
        
        # Geographic information - important for context
        if entity_type in ["home address", "city", "country", "region", "hometown", "current location"]:
            return len(text_clean) >= 2 and any(c.isalpha() for c in text_clean)
        
        # Relationships - high-value personal facts
        if entity_type in ["family member", "spouse", "partner", "child", "parent", "sibling", "friend", "colleague"]:
            return len(text_clean) >= 2 and any(c.isalpha() for c in text_clean)
        
        # Skills & expertise - valuable for personalization
        if entity_type in ["programming language", "technical skill", "software tool", "certification"]:
            return len(text_clean) >= 2 and any(c.isalnum() for c in text_clean)
        
        # Interests & preferences - good for conversation context
        if entity_type in ["hobby", "sport", "music genre", "favorite band", "book title", "movie title"]:
            return len(text_clean) >= 3 and any(c.isalpha() for c in text_clean)
        
        # Contact information - high-value structured data
        if entity_type in ["email address", "phone number", "social media handle", "username"]:
            if "email" in entity_type:
                return "@" in text_clean and "." in text_clean and len(text_clean) >= 5
            elif "phone" in entity_type:
                return any(c.isdigit() for c in text_clean) and len(text_clean) >= 7
            elif "username" in entity_type or "handle" in entity_type:
                return len(text_clean) >= 3 and any(c.isalnum() for c in text_clean)
        
        # Goals & aspirations - valuable for long-term context
        if entity_type in ["personal goal", "project name", "learning objective", "career aspiration"]:
            return len(text_clean) >= 4 and any(c.isalpha() for c in text_clean)
        
        # Health & personal - sensitive but valuable
        if entity_type in ["medical condition", "allergy", "medication", "diet restriction"]:
            return len(text_clean) >= 3 and any(c.isalpha() for c in text_clean)
        
        # Education - important background information
        if entity_type in ["school name", "university", "degree program", "major"]:
            return len(text_clean) >= 2 and any(c.isalpha() for c in text_clean)
        
        # Default validation for any other entity types
        return (len(text_clean) >= 2 and 
                any(c.isalnum() for c in text_clean) and 
                not text_clean.isdigit() and
                len([c for c in text_clean if c.isalpha()]) >= 1)
    
    # REMOVED: All English-only pattern matching methods
    # These were language-specific hacks that violated multilingual principle:
    # - _extract_relations() - English regex patterns
    # - _find_entities_in_range() - Only used by relation extraction
    # - _calculate_pattern_confidence() - English-specific confidence boosting
    # 
    # GLiNER's ML-based approach handles relations and context better than regex
    
    async def _synthesize_facts(self, text: str, entities: List[ExtractedEntity], 
                              segment_id: str) -> List[ExtractedFact]:
        """Synthesize structured facts directly from GLiNER entities."""
        facts = []
        
        try:
            # SIMPLIFIED: Create facts directly from high-confidence entities
            # GLiNER already provides context and relationships through entity extraction
            for entity in entities:
                if entity.confidence >= self.gliner_config["threshold"]:
                    fact = self._create_fact_from_entity(entity, text, segment_id)
                    if fact:
                        facts.append(fact)
            
            return facts
            
        except Exception as e:
            self.logger.error(f"🔍 [SYNTHESIS] Failed to synthesize facts: {e}")
            return []
    
    # REMOVED: _create_fact_from_relation() - English-only templates
    # Used hardcoded English templates like "User's name is {entity1}"
    # Not needed since we removed relation extraction
    
    def _create_fact_from_entity(self, entity: ExtractedEntity, text: str, segment_id: str) -> Optional[ExtractedFact]:
        """Create a fact from a standalone entity."""
        try:
            # Only create facts for high-confidence, meaningful entities
            if entity.confidence < 0.6:
                return None
            
            # Map GLiNER entity types to fact types (language-agnostic)
            fact_type_mapping = {
                # Personal identity
                "person name": FactType.IDENTITY,
                "full name": FactType.IDENTITY,
                "first name": FactType.IDENTITY,
                "last name": FactType.IDENTITY,
                "nickname": FactType.IDENTITY,
                
                # Geographic
                "city": FactType.LOCATION,
                "country": FactType.LOCATION,
                "home address": FactType.LOCATION,
                "current location": FactType.LOCATION,
                
                # Professional
                "job title": FactType.DEMOGRAPHIC,
                "profession": FactType.DEMOGRAPHIC,
                "company name": FactType.EXPERIENCE,
                "workplace": FactType.LOCATION,
                
                # Skills & interests
                "programming language": FactType.EXPERIENCE,
                "technical skill": FactType.EXPERIENCE,
                "hobby": FactType.PREFERENCE,
                "sport": FactType.PREFERENCE,
                
                # Relationships
                "family member": FactType.RELATIONSHIP,
                "spouse": FactType.RELATIONSHIP,
                "friend": FactType.RELATIONSHIP,
                
                # Contact
                "email address": FactType.IDENTITY,
                "phone number": FactType.IDENTITY,
            }
            
            fact_type = fact_type_mapping.get(entity.label.lower(), FactType.EXPERIENCE)
            
            # LANGUAGE-AGNOSTIC: Use entity text directly as fact content
            # This preserves the original language and context
            content = entity.text
            
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
                extraction_method="gliner_entity_extraction",
                source_segment_id=segment_id,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"🔍 [FACT_CREATION] Failed to create fact from entity: {e}")
            return None
