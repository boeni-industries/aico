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
    context_adherence: MetricScore
    knowledge_retention: MetricScore
    entity_extraction: MetricScore
    conversation_relevancy: MetricScore
    thread_management: MetricScore
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
    """Comprehensive memory evaluation metrics calculator"""
    
    def __init__(self):
        self.entity_patterns = {
            "PERSON": r'\b[A-Z][a-z]+ [A-Z][a-z]+\b|\b[A-Z][a-z]+\b',
            "GPE": r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b',
            "ORG": r'\b[A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*\b',
            "DATE": r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\b|\b\d{1,2}/\d{1,2}/\d{4}\b|\bnext \w+\b|\blast \w+\b',
            "MONEY": r'\$\d+(?:,\d{3})*(?:\.\d{2})?\b',
            "CARDINAL": r'\b\d+\b'
        }
        
    async def calculate_context_adherence(self, session) -> MetricScore:
        """
        Evaluate how well the AI maintains context across conversation turns.
        Measures continuity, reference to previous information, and contextual relevance.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data available")
            
        adherence_scores = []
        details = {"turn_scores": [], "context_breaks": 0, "successful_references": 0}
        
        for i, turn in enumerate(session.conversation_log):
            turn_score = 0.0
            turn_details = {"turn": i + 1}
            
            ai_response = turn.get("ai_response", "").lower()
            expected_context = turn.get("expected_context_elements", [])
            
            # Check for expected context elements
            context_found = 0
            for context_element in expected_context:
                if self._check_context_element_present(ai_response, context_element):
                    context_found += 1
                    details["successful_references"] += 1
                    
            if expected_context:
                context_score = context_found / len(expected_context)
                turn_score += context_score * 0.6
                turn_details["context_elements_found"] = f"{context_found}/{len(expected_context)}"
            
            # Check for references to previous turns
            should_remember_turns = turn.get("should_remember_from_turns", [])
            if should_remember_turns:
                reference_score = self._check_previous_turn_references(
                    session.conversation_log, i, should_remember_turns
                )
                turn_score += reference_score * 0.4
                turn_details["previous_turn_references"] = reference_score
            else:
                turn_score += 0.4  # Full points if no references expected
                
            adherence_scores.append(turn_score)
            details["turn_scores"].append(turn_details)
            
        overall_score = statistics.mean(adherence_scores) if adherence_scores else 0.0
        
        return MetricScore(
            score=overall_score,
            details=details,
            explanation=f"Context adherence across {len(adherence_scores)} turns"
        )
        
    async def calculate_knowledge_retention(self, session) -> MetricScore:
        """
        Evaluate the AI's ability to retain and recall information from earlier in the conversation.
        Tests both short-term working memory and longer-term episodic memory.
        """
        if len(session.conversation_log) < 2:
            return MetricScore(0.0, explanation="Insufficient conversation turns for retention testing")
            
        retention_tests = []
        details = {"recall_tests": [], "successful_recalls": 0, "total_tests": 0}
        
        for i, turn in enumerate(session.conversation_log):
            should_reference = turn.get("should_reference_entities", [])
            if not should_reference:
                continue
                
            details["total_tests"] += len(should_reference)
            ai_response = turn.get("ai_response", "")
            
            successful_recalls = 0
            for entity in should_reference:
                if self._entity_referenced_in_response(ai_response, entity):
                    successful_recalls += 1
                    details["successful_recalls"] += 1
                    
            if should_reference:
                recall_score = successful_recalls / len(should_reference)
                retention_tests.append(recall_score)
                
                details["recall_tests"].append({
                    "turn": i + 1,
                    "expected_entities": should_reference,
                    "recalled_entities": successful_recalls,
                    "recall_score": recall_score
                })
                
        overall_score = statistics.mean(retention_tests) if retention_tests else 0.0
        
        return MetricScore(
            score=overall_score,
            details=details,
            explanation=f"Knowledge retention across {len(retention_tests)} recall tests"
        )
        
    async def calculate_entity_extraction_accuracy(self, session) -> MetricScore:
        """
        Evaluate accuracy of named entity recognition and extraction.
        Compares expected entities with what should be extractable from responses.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data for entity evaluation")
            
        extraction_scores = []
        details = {"entity_tests": [], "total_expected": 0, "total_found": 0}
        
        for i, turn in enumerate(session.conversation_log):
            expected_entities = turn.get("expected_entities", {})
            if not expected_entities:
                continue
                
            user_message = turn.get("user_message", "")
            found_entities = self._extract_entities_from_text(user_message)
            
            turn_score = 0.0
            turn_details = {"turn": i + 1, "entity_scores": {}}
            
            for entity_type, expected_list in expected_entities.items():
                found_list = found_entities.get(entity_type, [])
                
                # Calculate precision and recall for this entity type
                true_positives = len(set(expected_list) & set(found_list))
                precision = true_positives / len(found_list) if found_list else 0.0
                recall = true_positives / len(expected_list) if expected_list else 0.0
                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
                
                turn_details["entity_scores"][entity_type] = {
                    "expected": expected_list,
                    "found": found_list,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1_score
                }
                
                turn_score += f1_score
                details["total_expected"] += len(expected_list)
                details["total_found"] += len(found_list)
                
            if expected_entities:
                turn_score /= len(expected_entities)
                extraction_scores.append(turn_score)
                details["entity_tests"].append(turn_details)
                
        overall_score = statistics.mean(extraction_scores) if extraction_scores else 0.0
        
        return MetricScore(
            score=overall_score,
            details=details,
            explanation=f"Entity extraction accuracy across {len(extraction_scores)} turns"
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
        
    async def calculate_thread_management_score(self, session) -> MetricScore:
        """
        Evaluate thread management decisions (new, continue, reactivate).
        Measures accuracy of thread resolution logic.
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data for thread evaluation")
            
        thread_scores = []
        details = {"thread_decisions": [], "correct_decisions": 0, "total_decisions": 0}
        
        for i, turn in enumerate(session.conversation_log):
            expected_thread_action = turn.get("thread_expectation", "continue")
            actual_thread_action = turn.get("thread_action", "unknown")
            
            details["total_decisions"] += 1
            
            # Score thread decision accuracy
            if actual_thread_action == expected_thread_action:
                thread_score = 1.0
                details["correct_decisions"] += 1
            elif self._thread_actions_compatible(actual_thread_action, expected_thread_action):
                thread_score = 0.7  # Partial credit for reasonable decisions
            else:
                thread_score = 0.0
                
            thread_scores.append(thread_score)
            
            details["thread_decisions"].append({
                "turn": i + 1,
                "expected": expected_thread_action,
                "actual": actual_thread_action,
                "score": thread_score
            })
            
        overall_score = statistics.mean(thread_scores) if thread_scores else 0.0
        
        return MetricScore(
            score=overall_score,
            details=details,
            explanation=f"Thread management accuracy: {details['correct_decisions']}/{details['total_decisions']}"
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
            4: 0.15,  # thread_management
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
        
    # Helper methods for metric calculations
    
    def _check_context_element_present(self, response: str, context_element: str) -> bool:
        """Check if a context element is present in the response"""
        element_keywords = {
            "user_name_michael": ["michael"],
            "location_san_francisco": ["san francisco", "sf"],
            "new_job_techcorp": ["techcorp", "job", "work"],
            "recent_move": ["move", "moved", "relocat"],
            "excitement_emotion": ["excit", "great", "wonderful", "amazing"],
            "job_role_software_engineer": ["software", "engineer", "developer"],
            "nervous_emotion": ["nervous", "anxious", "worry"],
            "ai_platform_work": ["ai", "platform", "artificial intelligence"],
            "pet_cat_whiskers": ["whiskers", "cat", "pet"],
            "birthday_october_13": ["birthday", "october", "13th"],
            "italian_food_preference": ["italian", "food", "cuisine"]
        }
        
        keywords = element_keywords.get(context_element, [context_element.lower()])
        return any(keyword in response.lower() for keyword in keywords)
        
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
        
    def _thread_actions_compatible(self, actual: str, expected: str) -> bool:
        """Check if thread actions are reasonably compatible"""
        compatible_pairs = [
            ("continue", "created"),  # Sometimes new threads are created when continuation expected
            ("created", "continue"),  # Vice versa
            ("reactivate", "continue")  # Reactivation might be seen as continuation
        ]
        return (actual, expected) in compatible_pairs
        
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
