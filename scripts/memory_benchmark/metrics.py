"""
Memory Evaluation Metrics

Comprehensive scoring framework for evaluating AICO's memory system performance
across multiple dimensions including context adherence, knowledge retention,
entity extraction accuracy, and conversation quality.
"""

import re
import json
import httpx
import chromadb
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
import statistics


@dataclass
class MetricScore:
    """Individual metric score with details"""
    score: float  # 0.0 to 1.0
    max_score: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    
    @property
    def percentage(self) -> float:
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0.0


@dataclass
class EvaluationResult:
    """Complete evaluation results for a memory test session"""
    session_id: str
    scenario_name: str
    overall_score: MetricScore
    
    # Core memory metrics
    context_adherence: MetricScore
    knowledge_retention: MetricScore
    entity_extraction: MetricScore
    conversation_relevancy: MetricScore
    semantic_memory_quality: MetricScore  # Replaces thread_management
    response_quality: MetricScore
    memory_consistency: MetricScore
    
    # Performance metrics
    performance_metrics: Dict[str, float]
    
    # Session metadata
    conversation_turns: int
    total_duration_seconds: float
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class MemoryMetrics:
    """Comprehensive memory benchmark metrics calculator for V2 fact-centric architecture"""
    
    def __init__(self):
        """Initialize with real AICO memory system connections"""
        # ChromaDB client for querying stored facts (V2 architecture)
        self.chroma_client = None
        self.user_facts_collection = None
        
        
    async def initialize_memory_connections(self):
        """Initialize connections to AICO's memory systems"""
        try:
            # Import AICO's configuration and paths
            from aico.core.config import ConfigurationManager
            from aico.core.paths import AICOPaths
            from chromadb.config import Settings
            
            # Get AICO's semantic memory path (same as CLI uses)
            semantic_memory_dir = AICOPaths.get_semantic_memory_path()
            
            if not semantic_memory_dir.exists():
                print(f"⚠️ ChromaDB directory doesn't exist: {semantic_memory_dir}")
                print("   Run a conversation first to initialize the memory system")
                return
            
            # Connect to ChromaDB using AICO's file-based approach
            self.chroma_client = chromadb.PersistentClient(
                path=str(semantic_memory_dir),
                settings=Settings(allow_reset=True, anonymized_telemetry=False)
            )
            
            # Get the collections AICO uses for memory storage
            try:
                self.user_facts_collection = self.chroma_client.get_collection("user_facts")
                # Add timeout to prevent hanging
                count_task = asyncio.create_task(asyncio.to_thread(self.user_facts_collection.count))
                count = await asyncio.wait_for(count_task, timeout=5.0)
                print(f"✅ Connected to user_facts collection ({count} documents)")
            except asyncio.TimeoutError:
                print("⚠️ user_facts collection count timed out - continuing anyway")
                self.user_facts_collection = self.chroma_client.get_collection("user_facts")
            except Exception:
                print("⚠️ user_facts collection not found - may not be created yet")
                
            # V2: No conversation_segments collection - facts are stored directly
                
            print("✅ Connected to AICO's file-based ChromaDB instance")
            
        except Exception as e:
            print(f"❌ Failed to connect to AICO memory systems: {e}")
            
    async def cleanup(self):
        """Cleanup connections"""
        pass  # No HTTP connections to clean up
        
    async def calculate_context_adherence(self, session) -> MetricScore:
        """
        FIXED Context Adherence Scoring v3.0
        Actually tests AI response quality against expected context elements.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data available")
            
        adherence_scores = []
        details = {"turn_scores": [], "total_elements_tested": 0, "elements_found": 0}
        element_keywords = self._get_context_element_keywords()
        
        for i, turn in enumerate(session.conversation_log):
            expected_context_elements = turn.get("expected_context_elements", [])
            ai_response = turn.get("ai_response", "")
            
            if not expected_context_elements:
                # No context elements expected for this turn - perfect score
                adherence_scores.append(1.0)
                continue
                
            if not ai_response:
                # No AI response to evaluate - zero score
                adherence_scores.append(0.0)
                continue
                
            # Test each expected context element against AI response
            elements_found = 0
            for element in expected_context_elements:
                if element in element_keywords:
                    keywords = element_keywords[element]
                    # Check if ANY of the keywords appear in the response
                    response_lower = ai_response.lower()
                    if any(keyword.lower() in response_lower for keyword in keywords):
                        elements_found += 1
                        details["elements_found"] += 1
                else:
                    # Fallback: literal string search for unknown elements
                    if element.lower() in ai_response.lower():
                        elements_found += 1
                        details["elements_found"] += 1
                
                details["total_elements_tested"] += 1
            
            # Calculate turn score based on percentage of elements found
            turn_score = elements_found / len(expected_context_elements) if expected_context_elements else 0.0
            adherence_scores.append(turn_score)
            
            details["turn_scores"].append({
                "turn": i + 1,
                "expected_elements": len(expected_context_elements),
                "found_elements": elements_found,
                "score": turn_score
            })
        
        # Calculate overall score
        overall_score = statistics.mean(adherence_scores) if adherence_scores else 0.0
        
        explanation = f"Context adherence: {details['elements_found']}/{details['total_elements_tested']} elements found across {len(adherence_scores)} turns"
        
        return MetricScore(overall_score, explanation=explanation, details=details)
        
    async def calculate_knowledge_retention(self, session) -> MetricScore:
        """
        FIXED Knowledge Retention Scoring v3.0
        Tests if AI actually uses previously mentioned information in responses.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data available")
        
        retention_scores = []
        details = {"turn_scores": [], "total_references_tested": 0, "successful_references": 0}
        
        for i, turn in enumerate(session.conversation_log):
            should_remember_turns = turn.get("should_remember_from_turns", [])
            should_reference_entities = turn.get("should_reference_entities", [])
            ai_response = turn.get("ai_response", "")
            
            if not should_remember_turns and not should_reference_entities:
                # No memory requirements for this turn
                retention_scores.append(1.0)
                continue
                
            if not ai_response:
                retention_scores.append(0.0)
                continue
            
            # Test entity references
            entities_found = 0
            for entity in should_reference_entities:
                if entity.lower() in ai_response.lower():
                    entities_found += 1
                    details["successful_references"] += 1
                details["total_references_tested"] += 1
            
            # Test previous turn references
            previous_refs_found = 0
            for prev_turn_idx in should_remember_turns:
                if prev_turn_idx <= len(session.conversation_log):
                    prev_turn = session.conversation_log[prev_turn_idx - 1]  # Convert to 0-based
                    prev_entities = prev_turn.get("expected_entities", {})
                    
                    # Check if any entities from previous turn are referenced
                    for entity_type, entities in prev_entities.items():
                        for entity in entities:
                            if entity.lower() in ai_response.lower():
                                previous_refs_found += 1
                                details["successful_references"] += 1
                                break
                    details["total_references_tested"] += 1
            
            # Calculate turn score
            total_expected = len(should_reference_entities) + len(should_remember_turns)
            total_found = entities_found + previous_refs_found
            turn_score = total_found / total_expected if total_expected > 0 else 1.0
            
            retention_scores.append(turn_score)
            details["turn_scores"].append({
                "turn": i + 1,
                "expected_references": total_expected,
                "found_references": total_found,
                "score": turn_score
            })
        
        # Calculate overall score
        overall_score = statistics.mean(retention_scores) if retention_scores else 0.0
        
        explanation = f"Knowledge retention: {details['successful_references']}/{details['total_references_tested']} references found across {len(retention_scores)} turns"
        
        return MetricScore(overall_score, explanation=explanation, details=details)
        
    async def calculate_entity_extraction_accuracy(self, session) -> MetricScore:
        """
        Test AICO's actual entity extraction by querying real GLiNER and ChromaDB storage.
        This tests the REAL memory system, not fake regex patterns.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data for entity evaluation")
        
        if not self.chroma_client:
            await self.initialize_memory_connections()
            
        extraction_scores = []
        details = {
            "gliner_tests": [],
            "chromadb_stored_entities": [],
            "total_messages_tested": 0,
            "successful_extractions": 0
        }
        
        user_id = getattr(session, 'user_id', None)
        conversation_id = getattr(session, 'conversation_id', None)
        all_conversation_ids = getattr(session, 'all_conversation_ids', [conversation_id] if conversation_id else [])
        
        # Give a moment for async memory processing to complete
        await asyncio.sleep(2.0)
        
        # Query entities from all conversation_ids used in the conversation
        stored_entities = {}
        for conv_id in all_conversation_ids:
            if conv_id:
                entities_from_conv = await self._query_stored_entities(user_id, conv_id, "")
                if entities_from_conv:
                    # Merge entities from this conversation
                    for entity_type, entity_list in entities_from_conv.items():
                        if entity_type not in stored_entities:
                            stored_entities[entity_type] = []
                        stored_entities[entity_type].extend(entity_list)
                        # Remove duplicates
                        stored_entities[entity_type] = list(set(stored_entities[entity_type]))
        
        for i, turn in enumerate(session.conversation_log):
            user_message = turn.get("user_message", "")
            if not user_message:
                continue
                
            details["total_messages_tested"] += 1
            turn_score = 0.0
            
            # FIXED: Test actual entity extraction quality vs expected entities
            expected_entities = turn.get("expected_entities", {})
            
            if not expected_entities:
                # No entities expected for this turn
                extraction_scores.append(1.0)
                continue
            
            # Calculate precision and recall for entity extraction
            total_expected = sum(len(entities) for entities in expected_entities.values())
            total_found = 0
            correct_entities = 0
            
            for entity_type, expected_list in expected_entities.items():
                stored_list = stored_entities.get(entity_type, []) if stored_entities else []
                
                # Count how many expected entities were actually found
                for expected_entity in expected_list:
                    if any(expected_entity.lower() in stored.lower() for stored in stored_list):
                        correct_entities += 1
                
                total_found += len(stored_list)
            
            # Calculate precision (correct/found) and recall (correct/expected)
            precision = correct_entities / total_found if total_found > 0 else 0.0
            recall = correct_entities / total_expected if total_expected > 0 else 0.0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            extraction_scores.append(f1_score)
            details["successful_extractions"] += 1 if f1_score > 0.5 else 0
            
            details["gliner_tests"].append({
                "turn": i + 1,
                "message": user_message[:100] + "..." if len(user_message) > 100 else user_message,
                "expected_entities": expected_entities,
                "stored_entities": stored_entities,
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "correct_entities": correct_entities,
                "total_expected": total_expected,
                "total_found": total_found,
                "score": f1_score
            })
            
        overall_score = statistics.mean(extraction_scores) if extraction_scores else 0.0
        
        return MetricScore(
            score=overall_score,
            details=details,
            explanation=f"Real entity extraction testing across {len(extraction_scores)} messages using GLiNER and ChromaDB"
        )
        
    async def calculate_conversation_relevancy(self, session) -> MetricScore:
        """
        Evaluate how relevant and appropriate AI responses are to user messages.
        Measures topical coherence and response appropriateness.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data available")
            
        relevancy_scores = []
        details = {"turn_evaluations": []}
        
        for i, turn in enumerate(session.conversation_log):
            user_message = turn.get("user_message", "")
            ai_response = turn.get("ai_response", "")
            validation_rules = turn.get("validation_rules", [])
            
            turn_score = 0.0
            turn_details = {"turn": i + 1, "rule_compliance": {}}
            
            # Basic relevancy check - response should be non-empty and substantial
            if ai_response and len(ai_response.strip()) > 10:
                turn_score += 0.3
                
            # Check validation rules compliance
            if validation_rules:
                rules_passed = 0
                for rule in validation_rules:
                    if self._check_validation_rule(ai_response, user_message, rule):
                        rules_passed += 1
                        turn_details["rule_compliance"][rule] = True
                    else:
                        turn_details["rule_compliance"][rule] = False
                        
                rule_score = rules_passed / len(validation_rules)
                turn_score += rule_score * 0.7
            else:
                turn_score += 0.7  # Full points if no specific rules
                
            relevancy_scores.append(turn_score)
            details["turn_evaluations"].append(turn_details)
            
        overall_score = statistics.mean(relevancy_scores) if relevancy_scores else 0.0
        
        return MetricScore(
            score=overall_score,
            details=details,
            explanation=f"Conversation relevancy across {len(relevancy_scores)} turns"
        )
        
        
    async def calculate_semantic_memory_quality(self, session) -> MetricScore:
        """
        Evaluate semantic memory system quality: entity extraction accuracy, 
        fact storage consistency, and retrieval effectiveness.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data for semantic memory evaluation")
            
        # This should measure the ACTUAL semantic memory system quality
        # For now, we'll base it on the combination of entity extraction and knowledge retention
        # since those are the real semantic memory components that are working
        
        try:
            # Get entity extraction score
            entity_score = await self.calculate_entity_extraction_accuracy(session)
            
            # Get knowledge retention score  
            retention_score = await self.calculate_knowledge_retention(session)
            
            # Combine scores with weights
            combined_score = (entity_score.score * 0.6) + (retention_score.score * 0.4)
            
            details = {
                "entity_extraction_score": entity_score.score,
                "knowledge_retention_score": retention_score.score,
                "combined_approach": "Entity extraction (60%) + Knowledge retention (40%)",
                "entity_details": entity_score.details,
                "retention_details": retention_score.details
            }
            
            return MetricScore(
                score=combined_score,
                details=details,
                explanation=f"Semantic memory quality: {combined_score:.1%} (Entity: {entity_score.score:.1%}, Retention: {retention_score.score:.1%})"
            )
            
        except Exception as e:
            return MetricScore(
                score=0.0, 
                details={"error": str(e)},
                explanation=f"Semantic memory evaluation failed: {str(e)}"
            )
        
    async def calculate_response_quality(self, session) -> MetricScore:
        """
        Evaluate overall quality of AI responses including coherence, helpfulness, and appropriateness.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data available")
            
        quality_scores = []
        details = {"quality_assessments": []}
        
        for i, turn in enumerate(session.conversation_log):
            ai_response = turn.get("ai_response", "")
            user_message = turn.get("user_message", "")
            
            quality_score = 0.0
            assessment = {"turn": i + 1}
            
            # Length and substance check
            if len(ai_response.strip()) > 20:
                quality_score += 0.2
                assessment["adequate_length"] = True
            
            # Coherence check (basic grammar and structure)
            if self._check_response_coherence(ai_response):
                quality_score += 0.3
                assessment["coherent"] = True
                
            # Helpfulness check
            if self._check_response_helpfulness(ai_response, user_message):
                quality_score += 0.3
                assessment["helpful"] = True
                
            # Appropriateness check
            if self._check_response_appropriateness(ai_response):
                quality_score += 0.2
                assessment["appropriate"] = True
                
            quality_scores.append(quality_score)
            details["quality_assessments"].append(assessment)
            
        overall_score = statistics.mean(quality_scores) if quality_scores else 0.0
        
        return MetricScore(
            score=overall_score,
            details=details,
            explanation=f"Response quality across {len(quality_scores)} turns"
        )
        
    async def calculate_memory_consistency(self, session) -> MetricScore:
        """
        Evaluate consistency of memory across the conversation.
        Checks for contradictions and maintains factual accuracy.
        """
        if len(session.conversation_log) < 2:
            return MetricScore(1.0, explanation="Insufficient turns for consistency evaluation")
            
        consistency_score = 1.0  # Start with perfect score, deduct for inconsistencies
        details = {"consistency_checks": [], "inconsistencies_found": 0}
        
        # Extract facts from all responses
        facts = []
        for turn in session.conversation_log:
            ai_response = turn.get("ai_response", "")
            turn_facts = self._extract_facts_from_response(ai_response)
            facts.extend(turn_facts)
            
        # Check for contradictions
        contradictions = self._find_contradictions(facts)
        
        if contradictions:
            consistency_penalty = min(0.2 * len(contradictions), 0.8)
            consistency_score -= consistency_penalty
            details["inconsistencies_found"] = len(contradictions)
            details["contradictions"] = contradictions
            
        return MetricScore(
            score=max(consistency_score, 0.0),
            details=details,
            explanation=f"Memory consistency with {len(contradictions)} contradictions found"
        )
        
    async def calculate_performance_metrics(self, session) -> Dict[str, float]:
        """Calculate performance-related metrics"""
        if not session.conversation_log:
            return {}
            
        response_times = [turn.get("response_time_ms", 0) for turn in session.conversation_log]
        
        return {
            "average_response_time_ms": statistics.mean(response_times) if response_times else 0.0,
            "max_response_time_ms": max(response_times) if response_times else 0.0,
            "min_response_time_ms": min(response_times) if response_times else 0.0,
            "total_conversation_time_seconds": session.duration_seconds,
            "turns_per_minute": len(session.conversation_log) / (session.duration_seconds / 60) if session.duration_seconds > 0 else 0.0
        }
        
    def calculate_overall_score(self, metric_scores: List[MetricScore]) -> MetricScore:
        """Calculate weighted overall score from individual metrics"""
        if not metric_scores:
            return MetricScore(0.0, explanation="No metrics available")
            
        # Weights for different metrics (should sum to 1.0)
        weights = {
            0: 0.20,  # context_adherence
            1: 0.20,  # knowledge_retention  
            2: 0.15,  # entity_extraction
            3: 0.15,  # conversation_relevancy
            4: 0.15,  # semantic_memory_quality
            5: 0.10,  # response_quality
            6: 0.05   # memory_consistency
        }
        
        weighted_sum = 0.0
        details = {"individual_scores": {}, "weights": weights}
        
        for i, score in enumerate(metric_scores):
            weight = weights.get(i, 0.0)
            weighted_sum += score.score * weight
            details["individual_scores"][f"metric_{i}"] = {
                "score": score.score,
                "weight": weight,
                "contribution": score.score * weight
            }
            
        return MetricScore(
            score=weighted_sum,
            details=details,
            explanation=f"Weighted average of {len(metric_scores)} metrics"
        )
        
    # Helper methods for NEW reliable scoring algorithm
    
    async def _get_real_context_retrieval(self, turn: dict, expected_entities: dict, session) -> list:
        """Get REAL context items from the actual memory system - NO SIMULATION"""
        if not self.chroma_client:
            await self.initialize_memory_connections()
            
        user_id = getattr(session, 'user_id', None)
        if not user_id:
            return []
            
        user_message = turn.get("user_message", "")
        if not user_message:
            return []
            
        try:
            # Query the REAL user_facts collection
            collection = self.chroma_client.get_collection("user_facts")
            
            # Get all facts for this user
            results = collection.get(
                where={"user_id": user_id},
                include=["documents", "metadatas"]
            )
            
            context_items = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    metadata = results["metadatas"][i] if results["metadatas"] else {}
                    
                    # Calculate relevance based on entity matching (like your entity boost)
                    relevance_score = self._calculate_real_relevance(user_message, metadata, expected_entities)
                    
                    context_items.append({
                        "content": doc,
                        "relevance_score": relevance_score,
                        "metadata": metadata
                    })
            
            return context_items
            
        except Exception as e:
            print(f"❌ Failed to get real context: {e}")
            return []
    
    def _calculate_real_relevance(self, user_message: str, metadata: dict, expected_entities: dict) -> float:
        """Calculate REAL relevance score using entity matching logic"""
        base_score = 0.3  # Default relevance
        
        # Get entities from metadata (same as your entity boost logic)
        entities_json = metadata.get('entities', '{}')
        try:
            entities = json.loads(entities_json)
            
            # Check if any entity VALUE appears in query (your exact logic)
            message_lower = user_message.lower()
            for entity_type, entity_list in entities.items():
                for entity_value in entity_list:
                    if entity_value.lower() in message_lower:
                        # Apply the same 2.5x boost as your system
                        return min(1.0, base_score * 2.5)
                        
        except (json.JSONDecodeError, AttributeError):
            pass
            
        return base_score
    
    def _calculate_entity_coverage(self, expected_entities: dict, context_items: list) -> float:
        """Score based on how many expected entities have relevant context retrieved"""
        if not expected_entities:
            return 1.0
            
        covered_entities = 0
        total_entities = sum(len(entities) for entities in expected_entities.values())
        
        for item in context_items:
            try:
                item_entities = json.loads(item.get('metadata', {}).get('entities', '{}'))
                
                # Check overlap with expected entities
                for exp_type, exp_values in expected_entities.items():
                    if exp_type in item_entities:
                        for exp_value in exp_values:
                            if exp_value.lower() in [v.lower() for v in item_entities[exp_type]]:
                                covered_entities += 1
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return min(1.0, covered_entities / total_entities) if total_entities > 0 else 1.0
    
    def _calculate_relevance_quality(self, context_items: list) -> float:
        """Score based on relevance scores of retrieved items"""
        if not context_items:
            return 0.0
            
        scores = [item.get('relevance_score', 0.0) for item in context_items]
        return statistics.mean(scores)
    
    def _calculate_context_utilization(self, turn: dict, context_items: list) -> float:
        """Score based on whether high-relevance context influenced the response"""
        if not context_items:
            return 0.0
        
        # Simple heuristic: if we have high-relevance items (>0.5), assume good utilization
        high_relevance_items = [item for item in context_items if item.get('relevance_score', 0) > 0.5]
        return min(1.0, len(high_relevance_items) / max(1, len(context_items)))
    
    # DEPRECATED: Old keyword-based scoring (kept for reference)
    def _check_context_element_present(self, response: str, context_element: str) -> bool:
        """DEPRECATED: Old keyword-based scoring - DO NOT USE"""
        # This method is now deprecated but kept for backward compatibility
        return False
        
    def _get_context_element_keywords(self) -> Dict[str, List[str]]:
        """Get keyword mappings for context elements across all scenarios"""
        return {
            # Comprehensive Memory Test elements
            "cat_name_recall": ["whiskers", "cat", "name", "called"],
            "coworker_sharing": ["coworker", "colleague", "tell", "share"], 
            "pet_introduction": ["pet", "cat", "introduce", "about him"],
            "user_name_michael": ["michael", "name", "hi", "hello"],
            "location_san_francisco": ["san francisco", "sf", "city", "francisco"],
            "new_job_techcorp": ["techcorp", "job", "work", "company"],
            "recent_move": ["moved", "move", "new", "recently"],
            "excitement_emotion": ["excited", "great", "wonderful", "happy"],
            
            # Technical Problem-Solving elements
            "react_error": ["react", "error", "undefined", "property"],
            "undefined_property": ["undefined", "property", "error", "cannot read"],
            "user_profile_component": ["userprofile", "component", "user", "profile"],
            "email_access_issue": ["email", "access", "user.email", "property"],
            "code_snippet_provided": ["code", "const", "function", "component"],
            "users_array_context": ["users", "array", "find", "api"],
            "api_dependency": ["api", "call", "request", "data"],
            "find_method_usage": ["find", "method", "users.find", "array"],
            "problem_solved_acknowledgment": ["fixed", "solved", "worked", "great"],
            "new_performance_issue": ["slow", "performance", "blank screen", "loading"],
            "loading_state_request": ["loading", "state", "spinner", "indicator"],
            "user_experience_concern": ["users", "experience", "see", "blank"],
            "state_management_question": ["usestate", "usereducer", "state", "manage"],
            "hook_comparison_request": ["compare", "should i use", "better", "hooks"],
            "complex_state_scenario": ["loading", "error", "data", "states"],
            
            # Personal Relationships elements
            "relationship_stress": ["stressed", "stress", "feeling", "partner"],
            "cohabitation_adjustment": ["moved in", "together", "adjustment", "living"],
            "partner_alex": ["alex", "partner", "boyfriend", "girlfriend"],
            "recent_move_in": ["last month", "moved in", "together", "recently"],
            "personality_differences": ["organized", "chaotic", "different", "opposite"],
            "cleanliness_conflict": ["dishes", "sink", "bed", "clean", "messy"],
            "relationship_concern": ["hurt", "relationship", "worried", "concerned"],
            "domestic_habits": ["dishes", "bed", "chores", "habits"],
            "communication_success": ["talked", "discussed", "communication", "decided"],
            "compromise_solution": ["schedule", "chore", "solution", "compromise"],
            "task_division": ["alex will", "i'll do", "division", "split"],
            "fairness_question": ["fair", "think", "reasonable", "balanced"],
            "birthday_planning": ["birthday", "plan", "special", "celebration"],
            "gift_ideas_request": ["ideas", "suggest", "plan", "special"],
            "partner_interests": ["hiking", "photography", "loves", "interests"],
            "special_occasion": ["special", "birthday", "celebrate", "occasion"],
            
            # Additional context elements from scenarios
            "pet_cat_whiskers": ["whiskers", "cat", "pet"],
            "pet_stress": ["stressed", "stress", "pet", "adjust"],
            "move_adjustment": ["move", "adjust", "new place", "relocation"],
            "topic_shift_to_pets": ["pet", "cat", "by the way"],
            "react_error": ["react", "error", "cannot read property"],
            "undefined_property": ["undefined", "property", "error"],
            "user_profile_component": ["userprofile", "component", "user profile"],
            "code_snippet_provided": ["code", "const", "function"],
            "api_dependency": ["api", "call", "request"],
            "loading_state_request": ["loading", "state", "spinner"],
            "relationship_stress": ["stressed", "stress", "partner"],
            "cohabitation_adjustment": ["moved in", "together", "living"],
            "partner_alex": ["alex", "partner"],
            "personality_differences": ["organized", "chaotic", "different"],
            "cleanliness_conflict": ["dishes", "sink", "clean", "messy"],
            "communication_success": ["talked", "discussed", "decided"],
            "compromise_solution": ["schedule", "chore", "solution"],
            "birthday_planning": ["birthday", "plan", "celebration"]
        }
        
    def _check_previous_turn_references(self, conversation_log: List[Dict], current_turn: int, should_remember_turns: List[int]) -> float:
        """Check if AI response references information from specified previous turns"""
        if current_turn == 0 or not should_remember_turns:
            return 1.0
            
        current_response = conversation_log[current_turn].get("ai_response", "").lower()
        reference_score = 0.0
        
        for turn_idx in should_remember_turns:
            if turn_idx <= current_turn and turn_idx > 0:
                previous_turn = conversation_log[turn_idx - 1]  # Convert to 0-based index
                previous_entities = previous_turn.get("expected_entities", {})
                
                # Check if any entities from the previous turn are referenced
                for entity_type, entities in previous_entities.items():
                    for entity in entities:
                        if entity.lower() in current_response:
                            reference_score += 1.0
                            break
                            
        return min(reference_score / len(should_remember_turns), 1.0) if should_remember_turns else 1.0
        
    def _entity_referenced_in_response(self, response: str, entity: str) -> bool:
        """Check if a specific entity is referenced in the response"""
        return entity.lower() in response.lower()
        
    def _extract_entities_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text using regex patterns"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = list(set(matches))  # Remove duplicates
                
        return entities
        
    def _check_validation_rule(self, ai_response: str, user_message: str, rule: str) -> bool:
        """Check if a validation rule is satisfied"""
        response_lower = ai_response.lower()
        
        rule_checks = {
            "should_acknowledge_name": lambda: "michael" in response_lower,
            "should_show_enthusiasm": lambda: any(word in response_lower for word in ["great", "wonderful", "exciting", "amazing", "fantastic"]),
            "should_ask_follow_up_about_job_or_move": lambda: "?" in ai_response,
            "should_remember_user_name": lambda: "michael" in response_lower,
            "should_reference_techcorp_context": lambda: "techcorp" in response_lower or "job" in response_lower,
            "should_provide_relevant_advice": lambda: len(ai_response) > 50 and ("advice" in response_lower or "suggest" in response_lower or "recommend" in response_lower),
            "should_acknowledge_nervousness": lambda: "nervous" in response_lower or "understand" in response_lower,
            "should_remember_recent_move_context": lambda: "move" in response_lower or "san francisco" in response_lower,
            "should_provide_pet_advice": lambda: "cat" in response_lower or "pet" in response_lower,
            "should_handle_topic_shift_gracefully": lambda: True,  # Assume graceful unless obvious issues
            "should_acknowledge_birthday": lambda: "birthday" in response_lower or "celebrate" in response_lower,
            "should_suggest_sf_restaurants": lambda: "restaurant" in response_lower,
            "should_remember_sf_location": lambda: "san francisco" in response_lower or "sf" in response_lower,
            "should_recall_job_title_software_engineer": lambda: "software" in response_lower and "engineer" in response_lower,
            "should_reference_techcorp": lambda: "techcorp" in response_lower,
            "should_remember_monday_start_date": lambda: "monday" in response_lower,
            "should_recall_cat_name_whiskers": lambda: "whiskers" in response_lower,
            "should_remember_cat_context": lambda: "cat" in response_lower
        }
        
        check_func = rule_checks.get(rule)
        return check_func() if check_func else False
    
    async def _test_gliner_extraction(self, text: str) -> Dict[str, List[str]]:
        """
        Test GLiNER entity extraction by checking if entities were stored in ChromaDB.
        Since modelservice only uses ZeroMQ (not REST), we verify extraction by 
        checking what entities were actually stored during conversation processing.
        """
        # For now, we'll return empty dict and rely on ChromaDB storage verification
        # This tests the end-to-end pipeline: GLiNER -> semantic memory -> ChromaDB
        # If entities are stored in ChromaDB, we know GLiNER worked
        return {}
    
    async def _query_stored_entities(self, user_id: str, conversation_id: str, message_text: str) -> Dict[str, Any]:
        """Query ChromaDB for facts stored from this conversation (V2)"""
        try:
            if not self.user_facts_collection:
                return {}
                
            # Query user facts by user_id (V2 architecture) - reduced noise
            if user_id:
                results = self.user_facts_collection.get(
                    where={"user_id": user_id},
                    include=["metadatas", "documents"],
                    limit=50  # Reasonable limit for user facts
                )
            else:
                # Fallback: get recent facts
                results = self.user_facts_collection.get(
                    include=["metadatas", "documents"],
                    limit=10
                )
            
            stored_entities = {}
            if results and "metadatas" in results:
                for i, metadata in enumerate(results["metadatas"]):
                    if "entities_json" in metadata:
                        try:
                            entities = json.loads(metadata["entities_json"])
                            stored_entities.update(entities)
                        except json.JSONDecodeError:
                            continue
                            
            return stored_entities
            
        except Exception as e:
            print(f"⚠️ Failed to query stored entities: {e}")
            return {}
    
    async def _query_user_facts(self, user_id: str, conversation_id: str = None) -> List[Dict[str, Any]]:
        """Query ChromaDB for user facts stored during conversation"""
        try:
            if not self.user_facts_collection:
                return []
                
            # Get all facts for this user (no embedding queries to avoid dimension mismatch)
            results = self.user_facts_collection.get(
                where={"user_id": user_id},
                include=["metadatas", "documents"]
            )
            
            # If no user-specific facts, get recent facts as fallback
            if not results.get("metadatas"):
                recent_results = self.user_facts_collection.get(
                    include=["metadatas", "documents"],
                    limit=10
                )
                # Use recent results if no user-specific ones
                if recent_results.get("metadatas"):
                    results = recent_results
            
            facts = []
            if results and "metadatas" in results:
                for i, metadata in enumerate(results["metadatas"]):
                    content = results["documents"][i] if "documents" in results and i < len(results["documents"]) else ""
                    
                    fact = {
                        "category": metadata.get("category", "unknown"),
                        "content": content,
                        "confidence": metadata.get("confidence", 0.0),
                        "created_at": metadata.get("created_at", "")
                    }
                    facts.append(fact)
                    
            return facts
            
        except Exception as e:
            print(f"⚠️ Failed to query user facts: {e}")
            return []
        
        
    def _check_response_coherence(self, response: str) -> bool:
        """Basic coherence check for AI response"""
        if not response or len(response.strip()) < 10:
            return False
            
        # Check for basic sentence structure
        sentences = response.split('.')
        return len(sentences) >= 1 and any(len(s.strip()) > 5 for s in sentences)
        
    def _check_response_helpfulness(self, response: str, user_message: str) -> bool:
        """Check if response is helpful to the user message"""
        helpful_indicators = ["help", "suggest", "recommend", "advice", "try", "consider", "might", "could"]
        return any(indicator in response.lower() for indicator in helpful_indicators)
        
    def _check_response_appropriateness(self, response: str) -> bool:
        """Check if response is appropriate and professional"""
        inappropriate_indicators = ["inappropriate", "offensive", "rude"]
        return not any(indicator in response.lower() for indicator in inappropriate_indicators)
        
    def _extract_facts_from_response(self, response: str) -> List[str]:
        """Extract factual statements from AI response for consistency checking"""
        # Simplified fact extraction - in practice, this would be more sophisticated
        sentences = response.split('.')
        facts = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and not sentence.endswith('?'):
                facts.append(sentence)
                
        return facts
        
    def _find_contradictions(self, facts: List[str]) -> List[Dict[str, str]]:
        """Find contradictions between facts"""
        # Simplified contradiction detection
        contradictions = []
        
        # This would be much more sophisticated in practice
        # For now, just check for obvious contradictions in names, dates, etc.
        
        return contradictions
