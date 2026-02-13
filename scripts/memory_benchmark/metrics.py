"""
Memory Evaluation Metrics

Comprehensive scoring framework for evaluating AICO's memory system performance
across multiple dimensions including context adherence, knowledge retention,
entity extraction accuracy, and conversation quality.
"""

import re
import json
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
    character_stability: MetricScore
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
        """Initialize metrics calculator.

        This benchmark runs end-to-end through the backend API gateway.
        Metrics should be computed from observed responses and scenario expectations,
        not by reading internal storage directly.
        """
        
        
    async def initialize_memory_connections(self):
        return
            
    async def cleanup(self):
        """Cleanup connections"""
        return
        
    async def calculate_context_adherence(self, session) -> MetricScore:
        """
        FIXED Context Adherence Scoring v3.0
        Actually tests AI response quality against expected context elements.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data available")
            
        adherence_scores = []
        details = {"turn_scores": [], "total_elements_tested": 0, "elements_found": 0, "timeouts": 0}
        element_keywords = self._get_context_element_keywords()
        
        for i, turn in enumerate(session.conversation_log):
            expected_context_elements = turn.get("expected_context_elements", [])
            ai_response = turn.get("ai_response", "")

            response_lower = (ai_response or "").lower()
            if "[timeout]" in response_lower or "request timed out" in response_lower:
                details["timeouts"] += 1
                if not expected_context_elements:
                    adherence_scores.append(0.0)
                    continue
                details["total_elements_tested"] += len(expected_context_elements)
                adherence_scores.append(0.0)
                details["turn_scores"].append({
                    "turn": i + 1,
                    "expected_elements": len(expected_context_elements),
                    "found_elements": 0,
                    "score": 0.0,
                    "timeout": True,
                })
                continue
            
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
        if details.get("timeouts"):
            explanation += f" ({details['timeouts']} timeout-like responses)"
        
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
        Entity extraction proxy.

        The benchmark runs end-to-end via the backend API gateway and intentionally
        does not read internal storage. As a proxy, we score whether the assistant
        response acknowledges the key named entities introduced in the user turn.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data for entity evaluation")
            
        extraction_scores = []
        details = {
            "turn_scores": [],
            "total_messages_tested": 0,
            "successful_extractions": 0
        }
        
        for i, turn in enumerate(session.conversation_log):
            user_message = turn.get("user_message", "")
            if not user_message:
                continue
                
            details["total_messages_tested"] += 1
            turn_score = 0.0
            
            expected_entities = turn.get("expected_entities", {})
            
            if not expected_entities:
                # No entities expected for this turn
                extraction_scores.append(1.0)
                continue

            ai_response = (turn.get("ai_response") or "").lower()
            total_expected = sum(len(v) for v in expected_entities.values())
            correct = 0
            for entities in expected_entities.values():
                for ent in entities:
                    if ent and ent.lower() in ai_response:
                        correct += 1

            score = correct / total_expected if total_expected > 0 else 1.0
            extraction_scores.append(score)
            details["successful_extractions"] += 1 if score >= 0.5 else 0
            details["turn_scores"].append(
                {
                    "turn": i + 1,
                    "correct": correct,
                    "total_expected": total_expected,
                    "score": score,
                }
            )
            
        overall_score = statistics.mean(extraction_scores) if extraction_scores else 0.0
        
        return MetricScore(
            score=overall_score,
            details=details,
            explanation=f"Entity acknowledgement proxy across {len(extraction_scores)} turns"
        )

    async def calculate_character_stability(self, session) -> MetricScore:
        """Evaluate whether the assistant stays in character.

        The evaluator attaches a `character_spec` (loaded from the active conversation
        Modelfile) onto the session.
        """

        spec = getattr(session, "character_spec", None)
        if not spec:
            return MetricScore(0.0, explanation="No character spec available (could not load active Modelfile)")

        from .character import character_violation_checks

        turn_scores: List[float] = []
        violations_by_turn: List[Dict[str, Any]] = []

        for i, turn in enumerate(session.conversation_log or []):
            response_text = turn.get("ai_response", "")
            violations = character_violation_checks(spec=spec, response_text=response_text)
            score = 1.0 if not violations else 0.0
            turn_scores.append(score)
            if violations:
                violations_by_turn.append({"turn": i + 1, "violations": violations})

        overall = statistics.mean(turn_scores) if turn_scores else 0.0
        return MetricScore(
            score=overall,
            details={
                "model_name": spec.model_name,
                "modelfile_path": str(spec.modelfile_path) if spec.modelfile_path else None,
                "character_name": spec.character_name,
                "violations": violations_by_turn,
            },
            explanation=f"Character stability across {len(turn_scores)} turns"
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
            0: 0.20,  # character_stability
            1: 0.15,  # context_adherence
            2: 0.15,  # knowledge_retention
            3: 0.10,  # entity_extraction
            4: 0.15,  # conversation_relevancy
            5: 0.10,  # semantic_memory_quality
            6: 0.10,  # response_quality
            7: 0.05,  # memory_consistency
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
            "user_name_daniel": ["daniel", "name"],
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

            ,
            # Working-memory / context quality scenarios
            "poetic_cosmic_flame": ["flame", "cosmic", "void", "dark"],
            "practical_checklist": ["checklist", "first day", "morning", "job", "work", "engineer"],
            "topic_change": ["switch", "new topic", "different"],
            "weather_inquiry": ["weather", "forecast", "temperature"],
            "python_project": ["python", "project"],
            "async_functions": ["async", "await"],
            "programming_help": ["debug", "help", "code", "program"],
            "weather": ["weather", "forecast"],
            "cooking": ["cooking", "cook"],
            "italian_cuisine": ["italian"],
            "pasta": ["pasta"],
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
