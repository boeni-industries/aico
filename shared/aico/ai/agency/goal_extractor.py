"""
User Goal Extractor

Extracts goal-forming user intents from conversation messages using a hybrid approach:
1. Fast XLM-RoBERTa intent classification (multilingual, <100ms)
2. LLM-based goal detail extraction (slower, but async)

Designed to run asynchronously without blocking conversation flow.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
import time

from aico.core.logging import get_logger
from aico.ai.analysis.intent_classifier import IntentClassificationProcessor, IntentType
from .perceptual_events import PerceptualEvent, GoalHorizon
from .models import Goal, GoalStatus

logger = get_logger("shared.ai.agency.goal_extractor")


class UserGoalExtractor:
    """
    Extracts user goals from conversation messages.
    
    Uses XLM-RoBERTa for fast multilingual intent classification,
    then LLM for detailed goal extraction when goal-forming intent detected.
    """
    
    def __init__(self, intent_classifier: Optional[IntentClassificationProcessor] = None, event_store=None, db_connection=None):
        """
        Initialize goal extractor.
        
        Args:
            intent_classifier: Optional pre-initialized intent classifier
            event_store: Optional AgencyEventStore for metrics tracking
            db_connection: Optional database connection for goal similarity search
        """
        self.intent_classifier = intent_classifier
        self._modelservice_client = None
        self.event_store = event_store
        self._db_connection = db_connection
        
        # Goal-forming intent patterns
        self.goal_forming_intents = {
            IntentType.REQUEST.value: 0.45,  # "Can you help me...", "I need..." - lowered to 0.45 for reliable detection
            IntentType.INFORMATION_SHARING.value: 0.5,  # "I want to...", "I'm planning to..."
            IntentType.QUESTION.value: 0.55,  # "How can I...", "What should I do to..." - lowered to 0.55
        }
        
        # Confidence thresholds
        self.min_intent_confidence = 0.6
        self.min_goal_confidence = 0.5
        
        logger.info("[GOAL_EXTRACTOR] User goal extractor initialized")
    
    async def _get_intent_classifier(self) -> IntentClassificationProcessor:
        """Get or initialize intent classifier"""
        if self.intent_classifier is None:
            from aico.ai.analysis.intent_classifier import get_intent_classifier
            self.intent_classifier = await get_intent_classifier()
        return self.intent_classifier
    
    async def _get_modelservice_client(self):
        """Get ModelService client for LLM extraction"""
        if self._modelservice_client is None:
            try:
                from backend.services.modelservice_client import ModelServiceClient
                from aico.core.config import ConfigurationManager
                config_manager = ConfigurationManager()
                self._modelservice_client = ModelServiceClient(config_manager)
                
                # Get conversation model name from llm config (vLLM)
                vllm_config = config_manager.get("llm.vllm", {})
                self._llm_model = vllm_config.get("model", "huihui_ai/qwen3-abliterated:8b-v2")
                logger.debug(f"[GOAL_EXTRACTOR] ModelService client initialized with model: {self._llm_model}")
            except Exception as e:
                logger.error(f"[GOAL_EXTRACTOR] Failed to initialize ModelService client: {e}")
                raise
        return self._modelservice_client
    
    async def extract_goal_from_message(
        self,
        user_id: str,
        message_id: str,
        message_text: str,
        conversation_id: str,
        conversation_context: Optional[List[str]] = None
    ) -> Optional[PerceptualEvent]:
        """
        Extract goal from user message if present.
        
        Args:
            user_id: User ID
            message_id: Message ID for provenance
            message_text: User's message text
            conversation_context: Recent conversation context
            
        Returns:
            PerceptualEvent if goal detected, None otherwise
        """
        start_time = time.time()
        intent_classification_ms = 0.0
        goal_extraction_ms = 0.0
        
        try:
            print(f"🔍 [GOAL_EXTRACTOR] === Starting goal extraction ===")
            print(f"🔍 [GOAL_EXTRACTOR] Message: '{message_text[:80]}...'")
            
            # Step 1: Fast intent classification (XLM-RoBERTa, ~50ms)
            print(f"🔍 [GOAL_EXTRACTOR] Step 1: Classifying intent with XLM-RoBERTa...")
            intent_start = time.time()
            intent_result = await self._classify_intent(message_text, user_id, conversation_id, conversation_context)
            intent_classification_ms = (time.time() - intent_start) * 1000
            
            if not intent_result:
                print(f"🔍 [GOAL_EXTRACTOR] ❌ Intent classification failed")
                logger.warning("[GOAL_EXTRACTOR] Intent classification returned no result")
                await self._log_extraction_event(
                    user_id=user_id,
                    message_id=message_id,
                    outcome="no_intent",
                    total_latency_ms=(time.time() - start_time) * 1000,
                    intent_classification_ms=intent_classification_ms,
                    error_message="Intent classification failed"
                )
                return None
            
            intent_type = intent_result.get("predicted_intent")
            confidence = intent_result.get("confidence", 0.0)
            print(f"🔍 [GOAL_EXTRACTOR] ✅ Intent classified: '{intent_type}' (confidence={confidence:.2f})")
            logger.info(f"[GOAL_EXTRACTOR] Intent classified: {intent_type} (conf={confidence:.2f})")
            
            # Check if this is a goal-forming intent
            is_goal_forming = self._is_goal_forming_intent(intent_type, confidence)
            print(f"🔍 [GOAL_EXTRACTOR] Goal-forming check: {is_goal_forming}")
            
            if not is_goal_forming:
                print(f"🔍 [GOAL_EXTRACTOR] ❌ Intent '{intent_type}' not goal-forming (threshold not met)")
                logger.debug(f"[GOAL_EXTRACTOR] Intent '{intent_type}' (conf={confidence:.2f}) not goal-forming")
                await self._log_extraction_event(
                    user_id=user_id,
                    message_id=message_id,
                    outcome="not_goal_forming",
                    intent_type=intent_type,
                    intent_confidence=confidence,
                    intent_classification_ms=intent_classification_ms,
                    total_latency_ms=(time.time() - start_time) * 1000
                )
                return None
            
            print(f"🔍 [GOAL_EXTRACTOR] ✅ Goal-forming intent detected: {intent_type}")
            logger.info(f"[GOAL_EXTRACTOR] Goal-forming intent detected: {intent_type} (conf={confidence:.2f})")
            
            # Step 2: LLM-based goal extraction (slower, ~500ms, but async)
            print(f"🔍 [GOAL_EXTRACTOR] Step 2: Extracting goal details with LLM...")
            goal_start = time.time()
            goal_details = await self._extract_goal_details_llm(
                message_text, 
                intent_type,
                conversation_context
            )
            goal_extraction_ms = (time.time() - goal_start) * 1000
            
            if not goal_details:
                print(f"🔍 [GOAL_EXTRACTOR] ❌ LLM extraction failed")
                logger.warning("[GOAL_EXTRACTOR] LLM extraction returned no result")
                await self._log_extraction_event(
                    user_id=user_id,
                    message_id=message_id,
                    outcome="extraction_failed",
                    intent_type=intent_type,
                    intent_confidence=confidence,
                    intent_classification_ms=intent_classification_ms,
                    goal_extraction_ms=goal_extraction_ms,
                    total_latency_ms=(time.time() - start_time) * 1000,
                    error_message="LLM extraction returned no result"
                )
                return None
            
            goal_confidence = goal_details.get("confidence", 0.0)
            print(f"🔍 [GOAL_EXTRACTOR] LLM extraction result:")
            print(f"🔍 [GOAL_EXTRACTOR]   Title: '{goal_details.get('title', 'N/A')}'")
            print(f"🔍 [GOAL_EXTRACTOR]   Confidence: {goal_confidence:.2f}")
            print(f"🔍 [GOAL_EXTRACTOR]   Horizon: {goal_details.get('horizon', 'N/A')}")
            
            if goal_confidence < self.min_goal_confidence:
                print(f"🔍 [GOAL_EXTRACTOR] ❌ Goal confidence {goal_confidence:.2f} below threshold {self.min_goal_confidence}")
                logger.debug(f"[GOAL_EXTRACTOR] LLM extraction confidence {goal_confidence:.2f} below threshold")
                await self._log_extraction_event(
                    user_id=user_id,
                    message_id=message_id,
                    outcome="low_confidence",
                    intent_type=intent_type,
                    intent_confidence=confidence,
                    intent_classification_ms=intent_classification_ms,
                    goal_title=goal_details.get('title'),
                    goal_confidence=goal_confidence,
                    goal_extraction_ms=goal_extraction_ms,
                    total_latency_ms=(time.time() - start_time) * 1000
                )
                return None
            
            # Step 2.5: Check for similar existing goals (deduplication)
            print(f"🔍 [GOAL_EXTRACTOR] Step 2.5: Checking for similar existing goals...")
            print(f"🔍 [GOAL_EXTRACTOR] New goal title: '{goal_details.get('title', '')}'")
            existing_goal = await self._find_similar_goal(
                user_id=user_id,
                title=goal_details.get('title', ''),
                similarity_threshold=0.85
            )
            print(f"🔍 [GOAL_EXTRACTOR] Similarity search result: {existing_goal.goal_id if existing_goal else 'None'}")
            
            if existing_goal:
                print(f"🔍 [GOAL_EXTRACTOR] ✅ Found similar existing goal: {existing_goal.goal_id}")
                print(f"🔍 [GOAL_EXTRACTOR] Reinforcing existing goal instead of creating duplicate")
                
                # Reinforce existing goal
                await self._reinforce_goal(
                    goal=existing_goal,
                    message_id=message_id,
                    message_text=message_text,
                    confidence=goal_confidence
                )
                
                # Create PerceptualEvent for the reinforced goal
                event = PerceptualEvent.create_user_intent_event(
                    user_id=user_id,
                    message_id=message_id,
                    summary_text=goal_details.get("summary", message_text),
                    goal_title=existing_goal.title,
                    goal_description=existing_goal.description,
                    horizon=existing_goal.goal_type,
                    urgency=goal_details.get("urgency", 0.5),
                    confidence=goal_details.get("confidence", 0.7),
                    intent_type=intent_type,
                    original_message=message_text
                )
                
                # Add reinforcement metadata to event
                event.metadata["reinforced_goal_id"] = existing_goal.goal_id
                event.metadata["mention_count"] = existing_goal.metadata.get("mention_count", 1)
                
                print(f"🔍 [GOAL_EXTRACTOR] ✅✅✅ Goal reinforced! Mention count: {existing_goal.metadata.get('mention_count', 1)}")
                
                await self._log_extraction_event(
                    user_id=user_id,
                    message_id=message_id,
                    outcome="success_reinforced",
                    intent_type=intent_type,
                    intent_confidence=confidence,
                    intent_classification_ms=intent_classification_ms,
                    goal_title=existing_goal.title,
                    goal_confidence=goal_confidence,
                    goal_horizon=existing_goal.goal_type,
                    goal_extraction_ms=goal_extraction_ms,
                    total_latency_ms=(time.time() - start_time) * 1000,
                    percept_id=event.percept_id
                )
                
                return event
            
            # Step 3: Create new PerceptualEvent (no similar goal found)
            print(f"🔍 [GOAL_EXTRACTOR] Step 3: Creating new PerceptualEvent...")
            event = PerceptualEvent.create_user_intent_event(
                user_id=user_id,
                message_id=message_id,
                summary_text=goal_details.get("summary", message_text),
                goal_title=goal_details.get("title", "Untitled goal"),
                goal_description=goal_details.get("description"),
                horizon=self._parse_horizon(goal_details.get("horizon", "project")),
                urgency=goal_details.get("urgency", 0.5),
                confidence=goal_details.get("confidence", 0.7),
                intent_type=intent_type,
                original_message=message_text
            )
            
            print(f"🔍 [GOAL_EXTRACTOR] ✅✅✅ UserIntentEvent created successfully!")
            print(f"🔍 [GOAL_EXTRACTOR]   Event ID: {event.percept_id}")
            print(f"🔍 [GOAL_EXTRACTOR]   Goal: '{goal_details.get('title')}'")
            logger.info(f"[GOAL_EXTRACTOR] Created UserIntentEvent: '{goal_details.get('title')}'")
            
            # Log successful extraction
            await self._log_extraction_event(
                user_id=user_id,
                message_id=message_id,
                outcome="success",
                intent_type=intent_type,
                intent_confidence=confidence,
                intent_classification_ms=intent_classification_ms,
                goal_title=goal_details.get('title'),
                goal_confidence=goal_confidence,
                goal_horizon=goal_details.get('horizon'),
                goal_extraction_ms=goal_extraction_ms,
                total_latency_ms=(time.time() - start_time) * 1000,
                percept_id=event.percept_id
            )
            
            return event
            
        except Exception as e:
            print(f"🔍 [GOAL_EXTRACTOR] ❌❌❌ EXCEPTION: {e}")
            import traceback
            print(f"🔍 [GOAL_EXTRACTOR] Traceback: {traceback.format_exc()}")
            logger.exception(f"[GOAL_EXTRACTOR] Goal extraction failed: {e}")
            
            # Log error
            await self._log_extraction_event(
                user_id=user_id,
                message_id=message_id,
                outcome="error",
                intent_classification_ms=intent_classification_ms,
                goal_extraction_ms=goal_extraction_ms,
                total_latency_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
            
            return None
    
    async def _classify_intent(
        self,
        text: str,
        user_id: str,
        conversation_id: str,
        conversation_context: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Classify intent using XLM-RoBERTa"""
        try:
            print(f"🔍 [GOAL_EXTRACTOR] Getting intent classifier...")
            classifier = await self._get_intent_classifier()
            print(f"🔍 [GOAL_EXTRACTOR] ✅ Got classifier: {classifier}")
            
            # Create processing context
            from aico.ai.base import ProcessingContext
            import uuid
            context = ProcessingContext(
                user_id=user_id,
                conversation_id=conversation_id,
                request_id=str(uuid.uuid4()),
                message_content=text,
                shared_state={"recent_intents": conversation_context or []}
            )
            
            print(f"🔍 [GOAL_EXTRACTOR] Calling classifier.process()...")
            result = await classifier.process(context)
            print(f"🔍 [GOAL_EXTRACTOR] Got result: success={result.success}, result_data={result.result_data}")
            
            if result.success:
                print(f"🔍 [GOAL_EXTRACTOR] ✅ Intent classified: {result.result_data}")
                return result.result_data
            else:
                print(f"🔍 [GOAL_EXTRACTOR] ❌ Classification failed: {result.error_message}")
                logger.warning(f"[GOAL_EXTRACTOR] Intent classification failed: {result.error_message}")
                return None
                
        except Exception as e:
            print(f"🔍 [GOAL_EXTRACTOR] ❌ Exception in _classify_intent: {e}")
            import traceback
            print(f"🔍 [GOAL_EXTRACTOR] Traceback: {traceback.format_exc()}")
            logger.error(f"[GOAL_EXTRACTOR] Intent classification error: {e}")
            return None
    
    def _is_goal_forming_intent(self, intent_type: str, confidence: float) -> bool:
        """Check if intent is goal-forming"""
        if intent_type not in self.goal_forming_intents:
            return False
        
        required_confidence = self.goal_forming_intents[intent_type]
        return confidence >= required_confidence
    
    async def _extract_goal_details_llm(
        self,
        message_text: str,
        intent_type: str,
        conversation_context: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract goal details using LLM with structured JSON output.
        
        Returns dict with: title, description, horizon, urgency, confidence
        """
        try:
            print(f"🔍 [LLM_EXTRACTION] Starting LLM goal extraction...")
            print(f"🔍 [LLM_EXTRACTION] Message: '{message_text}'")
            print(f"🔍 [LLM_EXTRACTION] Intent: {intent_type}")
            
            client = await self._get_modelservice_client()
            print(f"🔍 [LLM_EXTRACTION] ✅ Got ModelService client: {client}")
            
            # Build extraction prompt with JSON schema
            prompt = self._build_extraction_prompt_json(message_text, intent_type, conversation_context)
            print(f"🔍 [LLM_EXTRACTION] Prompt length: {len(prompt)} chars")
            print(f"🔍 [LLM_EXTRACTION] Prompt preview: {prompt[:200]}...")
            
            # Call LLM with get_chat_completions (proper chat API)
            print(f"🔍 [LLM_EXTRACTION] Calling ModelService get_chat_completions...")
            
            # Use configured conversation model
            model_name = getattr(self, '_llm_model', 'huihui_ai/qwen3-abliterated:8b-v2')
            print(f"🔍 [LLM_EXTRACTION] Using model: {model_name}")
            
            # Build messages array (proper chat format)
            messages = [
                {
                    "role": "system",
                    "content": "You are a goal extraction assistant. Always return valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await client.get_chat_completions(
                model=model_name,
                messages=messages,
                options={
                    "temperature": 0.2,
                    "num_predict": 500
                }
            )
            
            print(f"🔍 [LLM_EXTRACTION] Response received: {response}")
            
            if not response.get("success"):
                error_msg = response.get('error', 'Unknown error')
                print(f"🔍 [LLM_EXTRACTION] ❌ LLM call failed: {error_msg}")
                logger.warning(f"[GOAL_EXTRACTOR] LLM call failed: {error_msg}")
                return None
            
            # Extract LLM response text
            llm_text = response.get("data", {}).get("content", "")
            print(f"🔍 [LLM_EXTRACTION] LLM response text: '{llm_text}'")
            
            if not llm_text:
                print(f"🔍 [LLM_EXTRACTION] ❌ Empty LLM response")
                logger.warning(f"[GOAL_EXTRACTOR] Empty LLM response")
                return None
            
            # Parse JSON response
            print(f"🔍 [LLM_EXTRACTION] Parsing JSON response...")
            goal_details = self._parse_json_response(llm_text)
            
            if goal_details:
                print(f"🔍 [LLM_EXTRACTION] ✅ Successfully parsed goal:")
                print(f"🔍 [LLM_EXTRACTION]   Title: '{goal_details.get('title')}'")
                print(f"🔍 [LLM_EXTRACTION]   Confidence: {goal_details.get('confidence')}")
                print(f"🔍 [LLM_EXTRACTION]   Horizon: {goal_details.get('horizon')}")
            else:
                print(f"🔍 [LLM_EXTRACTION] ❌ Failed to parse goal from response")
            
            return goal_details
            
        except Exception as e:
            print(f"🔍 [LLM_EXTRACTION] ❌ Exception: {e}")
            import traceback
            print(f"🔍 [LLM_EXTRACTION] Traceback: {traceback.format_exc()}")
            logger.error(f"[GOAL_EXTRACTOR] LLM extraction error: {e}")
            return None
    
    def _build_extraction_prompt(
        self,
        message_text: str,
        intent_type: str,
        conversation_context: Optional[List[str]] = None
    ) -> str:
        """Build prompt for LLM goal extraction (legacy text format)"""
        context_str = ""
        if conversation_context:
            context_str = f"\n\nRecent conversation context:\n{chr(10).join(conversation_context[-3:])}"
        
        return f"""Extract goal information from this user message.

User message: "{message_text}"
Detected intent: {intent_type}{context_str}

Extract and return in this exact format:
TITLE: <short goal title>
DESCRIPTION: <detailed description or NONE>
HORIZON: <theme|project|task>
URGENCY: <0.0-1.0>
CONFIDENCE: <0.0-1.0>
SUMMARY: <one-sentence summary>

Be concise and precise. If no clear goal is present, set CONFIDENCE to 0.0."""
    
    def _build_extraction_prompt_json(
        self,
        message_text: str,
        intent_type: str,
        conversation_context: Optional[List[str]] = None
    ) -> str:
        """Build prompt for LLM goal extraction with JSON output"""
        context_str = ""
        if conversation_context:
            context_str = f"\n\nRecent conversation context:\n{chr(10).join(conversation_context[-3:])}"
        
        return f"""Analyze this user message for goal-forming intent.

User message: "{message_text}"
Detected intent: {intent_type}{context_str}

Extract goal information and return as valid JSON with this structure:
{{
  "has_goal": true/false,
  "title": "short goal title",
  "description": "detailed description or null",
  "horizon": "theme" | "project" | "task",
  "urgency": 0.0-1.0,
  "confidence": 0.0-1.0,
  "summary": "one-sentence summary"
}}

Horizon definitions:
- theme: Long-term life goal (e.g., "become fluent in Spanish")
- project: Multi-step goal requiring planning (e.g., "learn Spanish basics")
- task: Single actionable step (e.g., "practice Spanish verbs today")

If no clear goal is present, set has_goal to false and confidence to 0.0.

Return ONLY valid JSON, no other text."""
    
    def _parse_llm_response(self, llm_text: str) -> Dict[str, Any]:
        """Parse structured LLM response (legacy text format)"""
        result = {
            "title": "Untitled goal",
            "description": None,
            "horizon": "project",
            "urgency": 0.5,
            "confidence": 0.0,
            "summary": llm_text[:200]
        }
        
        try:
            lines = llm_text.strip().split('\n')
            for line in lines:
                if ':' not in line:
                    continue
                    
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == "title":
                    result["title"] = value
                elif key == "description":
                    result["description"] = None if value.upper() == "NONE" else value
                elif key == "horizon":
                    result["horizon"] = value.lower()
                elif key == "urgency":
                    try:
                        result["urgency"] = float(value)
                    except ValueError:
                        pass
                elif key == "confidence":
                    try:
                        result["confidence"] = float(value)
                    except ValueError:
                        pass
                elif key == "summary":
                    result["summary"] = value
                    
        except Exception as e:
            logger.warning(f"[GOAL_EXTRACTOR] Failed to parse LLM response: {e}")
        
        return result
    
    def _parse_json_response(self, llm_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON LLM response with validation"""
        import json
        
        try:
            # Try to extract JSON from response (handle markdown code blocks)
            json_text = llm_text.strip()
            
            # Remove markdown code blocks if present
            if json_text.startswith('```'):
                lines = json_text.split('\n')
                json_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else json_text
            
            # Parse JSON
            data = json.loads(json_text)
            
            # Validate structure
            if not isinstance(data, dict):
                print(f"🔍 [JSON_PARSE] ❌ Response is not a JSON object")
                return None
            
            # Check if goal was detected
            if not data.get("has_goal", False):
                print(f"🔍 [JSON_PARSE] No goal detected (has_goal=false)")
                return None
            
            # Extract and validate fields
            result = {
                "title": data.get("title", "Untitled goal"),
                "description": data.get("description"),
                "horizon": data.get("horizon", "project").lower(),
                "urgency": float(data.get("urgency", 0.5)),
                "confidence": float(data.get("confidence", 0.0)),
                "summary": data.get("summary", data.get("title", ""))
            }
            
            # Validate horizon
            if result["horizon"] not in ["theme", "project", "task"]:
                print(f"🔍 [JSON_PARSE] Invalid horizon '{result['horizon']}', defaulting to 'project'")
                result["horizon"] = "project"
            
            # Clamp values
            result["urgency"] = max(0.0, min(1.0, result["urgency"]))
            result["confidence"] = max(0.0, min(1.0, result["confidence"]))
            
            print(f"🔍 [JSON_PARSE] ✅ Successfully parsed JSON goal")
            return result
            
        except json.JSONDecodeError as e:
            print(f"🔍 [JSON_PARSE] ❌ JSON decode error: {e}")
            print(f"🔍 [JSON_PARSE] Response text: '{llm_text[:500]}'")
            logger.warning(f"[GOAL_EXTRACTOR] Failed to parse JSON response: {e}")
            
            # Fallback to text parsing
            print(f"🔍 [JSON_PARSE] Falling back to text parsing...")
            return self._parse_llm_response(llm_text)
            
        except Exception as e:
            print(f"🔍 [JSON_PARSE] ❌ Unexpected error: {e}")
            logger.error(f"[GOAL_EXTRACTOR] Error parsing JSON response: {e}")
            return None
    
    async def _find_similar_goal(
        self,
        user_id: str,
        title: str,
        similarity_threshold: float = 0.85
    ) -> Optional[Goal]:
        """
        Find similar existing goal using semantic similarity.
        
        Args:
            user_id: User ID to search goals for
            title: New goal title to compare
            similarity_threshold: Minimum cosine similarity (0-1)
            
        Returns:
            Existing Goal if similar match found, None otherwise
        """
        try:
            from aico.ai.agency.models import GoalStatus
            import numpy as np
            
            print(f"🔍 [SIMILARITY] Searching for goals similar to: '{title}'")
            
            # Get embedding for new goal title
            client = await self._get_modelservice_client()
            
            print(f"🔍 [SIMILARITY] Calling modelservice.get_embeddings(model='paraphrase-multilingual', prompt='{title}')")
            response = await client.get_embeddings(
                model="paraphrase-multilingual",
                prompt=title
            )
            
            print(f"🔍 [SIMILARITY] Response type: {type(response)}")
            print(f"🔍 [SIMILARITY] Response keys: {response.keys() if isinstance(response, dict) else 'N/A'}")
            print(f"🔍 [SIMILARITY] Response: {response}")
            
            if not response.get("success"):
                error_msg = response.get("error", "Unknown error")
                print(f"🔍 [SIMILARITY] ❌ Embedding generation failed: {error_msg}")
                logger.error(f"[GOAL_EXTRACTOR] Failed to get embedding for similarity check: {error_msg}")
                return None
            
            new_embedding = np.array(response["data"]["embedding"])
            print(f"🔍 [SIMILARITY] ✅ Got embedding for new goal (dim={len(new_embedding)})")
            
            # Get all pending goals for user
            print(f"🔍 [SIMILARITY] About to import GoalStore...")
            from aico.services.agency_service import AgencyService
            from aico.data.uow import UnitOfWork
            from aico.data.postgres.connection import get_session_factory
            print(f"🔍 [SIMILARITY] Creating GoalStore with db_connection={self._db_connection}")
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                agency_service = AgencyService(uow)
                print(f"🔍 [SIMILARITY] Calling list_goals(user_id={user_id}, status=PENDING)...")
                pending_goals = await agency_service.list_goals(
                    user_id=user_id,
                    status=GoalStatus.PENDING
                )
            
            print(f"🔍 [SIMILARITY] Found {len(pending_goals)} pending goals to compare")
            
            # Compare embeddings
            best_match = None
            best_similarity = 0.0
            goals_with_embeddings = 0
            
            for goal in pending_goals:
                goal_embedding = goal.metadata.get("title_embedding")
                if not goal_embedding:
                    print(f"🔍 [SIMILARITY] ⚠️  Goal '{goal.title}' has no embedding, skipping")
                    continue
                
                goals_with_embeddings += 1
                goal_embedding = np.array(goal_embedding)
                
                # Cosine similarity
                similarity = np.dot(new_embedding, goal_embedding) / (
                    np.linalg.norm(new_embedding) * np.linalg.norm(goal_embedding)
                )
                
                print(f"🔍 [SIMILARITY] '{goal.title}' similarity: {similarity:.3f}")
                
                if similarity >= similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = goal
            
            print(f"🔍 [SIMILARITY] Compared {goals_with_embeddings}/{len(pending_goals)} goals with embeddings")
            
            if best_match:
                print(f"🔍 [SIMILARITY] ✅ Best match: '{best_match.title}' (similarity={best_similarity:.3f})")
                logger.info(
                    f"[GOAL_EXTRACTOR] Found similar goal: '{best_match.title}' "
                    f"(similarity={best_similarity:.3f})"
                )
            else:
                print(f"🔍 [SIMILARITY] ❌ No similar goals found (threshold={similarity_threshold})")
            
            return best_match
            
        except Exception as e:
            logger.error(f"[GOAL_EXTRACTOR] Error finding similar goal: {e}")
            return None
    
    async def _reinforce_goal(
        self,
        goal: Goal,
        message_id: str,
        message_text: str,
        confidence: float
    ) -> None:
        """
        Reinforce existing goal with new mention.
        
        Updates metadata with intent persistence tracking:
        - Appends to intent_mentions array
        - Increments mention_count
        - Updates last_mentioned timestamp
        - Calculates mention_frequency
        
        Args:
            goal: Existing goal to reinforce
            message_id: ID of message containing the mention
            message_text: Text of the message
            confidence: Confidence of this mention
        """
        try:
            from datetime import datetime, UTC
            from aico.services.agency_service import AgencyService
            from aico.data.uow import UnitOfWork
            from aico.data.postgres.connection import get_session_factory
            
            now = datetime.now(UTC)
            
            # Get or initialize intent_mentions array
            intent_mentions = goal.metadata.get("intent_mentions", [])
            
            # Add new mention
            intent_mentions.append({
                "message_id": message_id,
                "timestamp": now.isoformat(),
                "confidence": confidence,
                "message_text": message_text[:100]  # Truncate for storage
            })
            
            # Update mention count
            mention_count = len(intent_mentions)
            
            # Get first mention timestamp
            first_mentioned = goal.metadata.get(
                "first_mentioned",
                goal.created_at.isoformat() if goal.created_at else now.isoformat()
            )
            
            # Calculate mention frequency (mentions per day)
            first_dt = datetime.fromisoformat(first_mentioned.replace('Z', '+00:00'))
            days_since_first = max(1, (now - first_dt).total_seconds() / 86400)
            mention_frequency = mention_count / days_since_first
            
            # Update goal metadata
            goal.metadata["intent_mentions"] = intent_mentions
            goal.metadata["mention_count"] = mention_count
            goal.metadata["first_mentioned"] = first_mentioned
            goal.metadata["last_mentioned"] = now.isoformat()
            goal.metadata["mention_frequency"] = mention_frequency
            
            # Save updated goal
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                agency_service = AgencyService(uow)
                await agency_service.update_goal(goal)
            
            logger.info(
                f"[GOAL_EXTRACTOR] Reinforced goal {goal.goal_id}: "
                f"mention_count={mention_count}, frequency={mention_frequency:.2f}/day"
            )
            
        except Exception as e:
            logger.error(f"[GOAL_EXTRACTOR] Error reinforcing goal: {e}")
    
    def _parse_horizon(self, horizon_str: str) -> GoalHorizon:
        """Parse horizon string to enum"""
        horizon_map = {
            "theme": GoalHorizon.THEME,
            "project": GoalHorizon.PROJECT,
            "task": GoalHorizon.TASK
        }
        return horizon_map.get(horizon_str.lower(), GoalHorizon.PROJECT)
    
    async def _log_extraction_event(
        self,
        user_id: str,
        message_id: str,
        outcome: str,
        intent_type: Optional[str] = None,
        intent_confidence: float = 0.0,
        intent_classification_ms: float = 0.0,
        goal_title: Optional[str] = None,
        goal_confidence: float = 0.0,
        goal_horizon: Optional[str] = None,
        goal_extraction_ms: float = 0.0,
        total_latency_ms: float = 0.0,
        percept_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Log goal extraction event to agency_events table"""
        if not self.event_store:
            return
        
        try:
            from .models import AgencyEvent
            
            event = AgencyEvent(
                user_id=user_id,
                goal_id=None,  # No goal created yet
                plan_id=None,
                event_type=f"goal_extraction_{outcome}",
                source="goal_extractor",
                payload={
                    "message_id": message_id,
                    "outcome": outcome,
                    "intent_type": intent_type,
                    "intent_confidence": intent_confidence,
                    "intent_classification_ms": intent_classification_ms,
                    "goal_title": goal_title,
                    "goal_confidence": goal_confidence,
                    "goal_horizon": goal_horizon,
                    "goal_extraction_ms": goal_extraction_ms,
                    "total_latency_ms": total_latency_ms,
                    "percept_id": percept_id,
                    "error_message": error_message
                }
            )
            
            await self.event_store.log_event(event)
            logger.debug(f"[GOAL_EXTRACTOR] Logged extraction event: {outcome}")
            
        except Exception as e:
            logger.warning(f"[GOAL_EXTRACTOR] Failed to log extraction event: {e}")


# Global instance
_goal_extractor = None


async def get_goal_extractor() -> UserGoalExtractor:
    """Get global goal extractor instance"""
    global _goal_extractor
    
    if _goal_extractor is None:
        _goal_extractor = UserGoalExtractor()
    
    return _goal_extractor
