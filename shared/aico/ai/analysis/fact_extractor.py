"""
Personal Fact Extractor for AICO Semantic Memory

Extracts personal facts from user messages using LLM analysis.
Designed specifically for Phase 2 semantic memory implementation.
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.data.schemas.semantic import PersonalFact, FactCategory, FactPermanence, FactExtractionResult

logger = get_logger("shared", "ai.fact_extractor")


class PersonalFactExtractor:
    """
    Extracts personal facts from user messages using LLM analysis.
    
    Uses the existing modelservice/Ollama LLM to intelligently identify
    personal facts worth storing in semantic memory for relationship building.
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self.modelservice = None  # Injected dependency
        
        # Configuration
        self.confidence_threshold = self.config.get("memory.semantic.confidence_threshold", 0.8)
        self.model_name = self.config.get("core.modelservice.ollama.default_models.llm.name", "hermes3:8b")
    
    async def extract_facts(self, user_message: str, user_id: str, context: Dict[str, Any] = None) -> List[PersonalFact]:
        """
        Extract personal facts from user message.
        
        Args:
            user_message: The user's message to analyze
            user_id: User identifier for context
            context: Additional context (recent messages, thread info, etc.)
            
        Returns:
            List of PersonalFact objects with confidence above threshold
        """
        if not self.modelservice:
            logger.error("Modelservice not available for fact extraction")
            return []
        
        try:
            # Generate analysis prompt
            prompt = self._build_extraction_prompt(user_message, user_id, context or {})
            
            # Get LLM response
            response = await self.modelservice.generate_completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1  # Low temperature for consistent structured output
            )
            
            if not response.get("success"):
                logger.error(f"LLM completion failed: {response.get('error')}")
                return []
            
            # Parse response to extract facts
            facts = self._parse_llm_response(response["data"]["content"], user_message, user_id)
            
            # Filter by confidence threshold
            high_confidence_facts = [
                fact for fact in facts 
                if fact.confidence >= self.confidence_threshold
            ]
            
            logger.info(f"Extracted {len(high_confidence_facts)} high-confidence facts from {len(facts)} total")
            return high_confidence_facts
            
        except Exception as e:
            logger.error(f"Fact extraction failed: {e}")
            return []
    
    def _build_extraction_prompt(self, message: str, user_id: str, context: Dict[str, Any]) -> str:
        """Build LLM prompt for fact extraction"""
        return f"""You are analyzing a user's message to identify personal facts worth remembering for relationship building.

User Message: "{message}"
User ID: {user_id}
Recent Context: {context.get('recent_messages', 'None')}

Extract ONLY significant personal facts that would help build a relationship with this user.

Respond with valid JSON only. No additional text.

{{
  "facts": [
    {{
      "fact_text": "exact factual statement about the user",
      "category": "identity|preference|relationship|date|context",
      "permanence": "permanent|evolving|temporary",
      "confidence": 0.95,
      "reasoning": "why this fact is worth remembering"
    }}
  ]
}}

STRICT CRITERIA - Only extract facts that are:
1. About the USER specifically (not opinions about others/world)
2. Factual and specific (not vague or emotional states)
3. Relationship-building relevant (helps personalize future interactions)
4. Stable enough to be worth storing (not momentary feelings)

Examples of GOOD facts:
- "My name is Sarah" → identity, permanent, confidence: 0.98
- "I'm vegetarian" → preference, evolving, confidence: 0.90
- "My daughter lives in Boston" → relationship, evolving, confidence: 0.95
- "My birthday is March 15th" → date, permanent, confidence: 0.98

Examples of BAD facts (don't extract):
- "I'm tired today" → temporary emotional state
- "I think the weather is nice" → opinion about environment
- "That's interesting" → reaction, not personal fact
- "I'm feeling sad" → temporary emotional state

If no facts are found, respond with: {{"facts": []}}

JSON RESPONSE ONLY:"""
    
    def _parse_llm_response(self, llm_response: str, source_message: str, user_id: str) -> List[PersonalFact]:
        """
        Parse LLM response with robust error handling.
        
        Uses multiple parsing strategies for maximum reliability.
        """
        try:
            # Strategy 1: Direct JSON parse
            return self._parse_direct_json(llm_response, source_message, user_id)
        except json.JSONDecodeError:
            try:
                # Strategy 2: Extract JSON from mixed content
                return self._extract_json_from_text(llm_response, source_message, user_id)
            except Exception:
                try:
                    # Strategy 3: Regex-based field extraction
                    return self._extract_fields_with_regex(llm_response, source_message, user_id)
                except Exception as e:
                    logger.warning(f"All parsing strategies failed: {e}")
                    return []
    
    def _parse_direct_json(self, response: str, source_message: str, user_id: str) -> List[PersonalFact]:
        """Parse clean JSON response"""
        parsed = json.loads(response.strip())
        return self._convert_to_facts(parsed.get("facts", []), source_message, user_id)
    
    def _extract_json_from_text(self, text: str, source_message: str, user_id: str) -> List[PersonalFact]:
        """Extract JSON from text that may contain extra content"""
        # Find JSON block in response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed = json.loads(json_str)
            return self._convert_to_facts(parsed.get("facts", []), source_message, user_id)
        raise ValueError("No JSON found in response")
    
    def _extract_fields_with_regex(self, text: str, source_message: str, user_id: str) -> List[PersonalFact]:
        """Fallback: extract fields using regex patterns"""
        facts = []
        
        # Look for fact patterns even if JSON is malformed
        fact_patterns = re.findall(
            r'"fact_text":\s*"([^"]+)".*?"category":\s*"([^"]+)".*?"confidence":\s*([0-9.]+)', 
            text, 
            re.DOTALL
        )
        
        for fact_text, category, confidence in fact_patterns:
            # Convert category string to enum with fallback
            try:
                category_enum = FactCategory(category)
            except ValueError:
                category_enum = FactCategory.CONTEXT
            
            facts.append(PersonalFact(
                fact_text=fact_text,
                category=category_enum,
                permanence=FactPermanence.EVOLVING,  # Default for regex extraction
                confidence=float(confidence),
                reasoning="Extracted via fallback parsing",
                source_message=source_message,
                timestamp=datetime.utcnow(),
                user_id=user_id
            ))
        
        logger.info(f"Regex extraction found {len(facts)} facts")
        return facts
    
    def _convert_to_facts(self, facts_data: List[Dict], source_message: str, user_id: str) -> List[PersonalFact]:
        """Convert parsed JSON data to PersonalFact objects using centralized schema"""
        facts = []
        
        for fact_data in facts_data:
            try:
                # Convert string values to enums with fallbacks
                category_str = fact_data.get("category", "context")
                try:
                    category = FactCategory(category_str)
                except ValueError:
                    logger.warning(f"Unknown category '{category_str}', defaulting to CONTEXT")
                    category = FactCategory.CONTEXT
                
                permanence_str = fact_data.get("permanence", "evolving")
                try:
                    permanence = FactPermanence(permanence_str)
                except ValueError:
                    logger.warning(f"Unknown permanence '{permanence_str}', defaulting to EVOLVING")
                    permanence = FactPermanence.EVOLVING
                
                fact = PersonalFact(
                    fact_text=fact_data.get("fact_text", ""),
                    category=category,
                    permanence=permanence,
                    confidence=float(fact_data.get("confidence", 0.0)),
                    reasoning=fact_data.get("reasoning", ""),
                    source_message=source_message,
                    timestamp=datetime.utcnow(),
                    user_id=user_id
                )
                
                # Validate fact has required fields
                if fact.fact_text and fact.confidence > 0:
                    facts.append(fact)
                else:
                    logger.warning(f"Skipping invalid fact: {fact_data}")
                    
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to convert fact data: {fact_data}, error: {e}")
                continue
        
        return facts
