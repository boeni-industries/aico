"""
Main Memory Intelligence Evaluator

Orchestrates comprehensive memory system evaluation through realistic conversation
scenarios and multi-dimensional scoring metrics.
"""

import asyncio
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
import uuid
 

# Add shared path for AICO modules
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

# Import AICO modules (avoid logging initialization issues)
try:
    from aico.core.config import ConfigurationManager
except ImportError:
    ConfigurationManager = None

# We'll use simple print statements instead of logging for now
# from aico.core.logging import get_logger
# from aico.core.bus import MessageBusClient
# from aico.proto.aico_conversation_pb2 import ConversationMessage

from .scenarios import ConversationScenario, ScenarioLibrary
from .metrics import MemoryMetrics, EvaluationResult, MetricScore
from .reporters import RichReporter, JSONReporter, DetailedReporter
from .api_client import EncryptedBenchmarkClient
from .character import load_active_character_spec


@dataclass
class EvaluationSession:
    """Represents a complete evaluation session"""
    session_id: str
    scenario: ConversationScenario
    start_time: datetime
    end_time: Optional[datetime] = None
    conversation_log: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    evaluation_result: Optional['EvaluationResult'] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    character_spec: Optional[Any] = None
    
    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class MemoryIntelligenceEvaluator:
    """
    End-to-end memory/context evaluator.
    
    This runner drives the *real* backend API through the API gateway:
    - Transport encryption (handshake + encrypted JSON envelopes)
    - JWT authentication
    - Conversation processing via ConversationEngine + modelservice + Ollama
    
    The evaluator intentionally avoids direct DB access to ensure the full chain is exercised.
    """
    
    def __init__(self, 
                 backend_url: str = "http://localhost:8771",
                 auth_token: Optional[str] = None,
                 timeout_seconds: int = 30,
                 reuse_user: bool = False,
                 user_id: Optional[str] = None,
                 pin: Optional[str] = None):
        """
        Initialize the Memory Intelligence Evaluator.
        
        Args:
            backend_url: AICO backend API URL
            auth_token: Authentication token (if None, will attempt auto-login)
            timeout_seconds: Request timeout for API calls
            reuse_user: If True, reuse the same user across all scenarios (for deduplication testing)
            user_id: If provided, use this existing user instead of creating a new one
        """
        self.backend_url = backend_url
        self.auth_token = auth_token
        self.timeout_seconds = timeout_seconds
        self.reuse_user = reuse_user
        self.persistent_user_id = user_id  # Use existing user if provided
        self._pin = pin
        
        # Initialize AICO components (optional)
        self.config = ConfigurationManager() if ConfigurationManager else None
        self.conversation_timeout_seconds: float = float(timeout_seconds)
        if self.config is not None:
            try:
                self.config.initialize(lightweight=True)
                configured_timeout = self.config.get("conversation.response_timeout_seconds", None)
                if configured_timeout is not None:
                    self.conversation_timeout_seconds = float(configured_timeout)
            except Exception:
                # If config is unavailable for any reason, keep CLI-provided timeout
                self.conversation_timeout_seconds = float(timeout_seconds)

        # Ensure HTTP client timeout is always >= conversation timeout (+buffer)
        # so the client-side HTTP layer doesn't abort earlier than the backend.
        self.timeout_seconds = int(max(float(self.timeout_seconds), self.conversation_timeout_seconds + 10.0))
        
        # Initialize evaluation components
        self.metrics = MemoryMetrics()
        self.scenario_library = ScenarioLibrary()
        
        # Reporters using Rich for beautiful output
        self.rich_reporter = RichReporter()
        self.json_reporter = JSONReporter()
        self.detailed_reporter = DetailedReporter()
        
        self._client: Optional[EncryptedBenchmarkClient] = None
        self._test_user_uuid: Optional[str] = None
        
        # Session tracking
        self.current_session: Optional[EvaluationSession] = None
        self.session_history: List[EvaluationSession] = []
        
    async def wait_for_backend_ready(self, max_wait_seconds: int = 60) -> bool:
        """Wait for AICO backend to be ready"""
        if not self._client:
            self._client = EncryptedBenchmarkClient(self.backend_url, timeout_seconds=max(self.timeout_seconds, 30.0))
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            try:
                # Health is public and not encrypted
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{self.backend_url}/api/v1/health")
                if resp.status_code == 200:
                    print("✅ AICO backend is ready")
                    return True
            except Exception as e:
                # Silently continue checking
                pass
                
            await asyncio.sleep(2)
            
        print(f"⚠️ Backend not ready after {max_wait_seconds}s")
        return False
        
    async def cleanup(self):
        """Clean up resources and test user"""
        await self._cleanup_test_user()
        if self._client:
            await self._client.close()
            self._client = None
            
    async def _cleanup_test_user(self):
        """Clean up the test user created during testing"""
        if not self._test_user_uuid:
            return
        
        # NEVER delete persistent user
        if self.persistent_user_id:
            print(f"🔒 Skipping cleanup of persistent user: {self._test_user_uuid}")
            return
            
        # Only try to delete if we actually created a real user (not a fake UUID)
        if len(self._test_user_uuid) != 36 or '-' not in self._test_user_uuid:
            print(f"⚠️ Skipping cleanup of invalid UUID: {self._test_user_uuid}")
            self._test_user_uuid = None
            return
            
        # Benchmarks should not mutate user data or require admin privileges.
        # Cleanup is intentionally a no-op.
        print(f"🔒 Skipping cleanup of test user: {self._test_user_uuid}")
        self._test_user_uuid = None

    async def _authenticate_user(self):
        """Authenticate with a test user for API access"""
        if not self._client:
            self._client = EncryptedBenchmarkClient(self.backend_url, timeout_seconds=max(self.timeout_seconds, 30.0))

        if not self.persistent_user_id:
            raise ValueError("Benchmark requires --user-id (existing user UUID) for end-to-end auth")
        if not self._pin:
            raise ValueError("Benchmark requires --pin for /api/v1/users/authenticate")

        print("🔐 Authenticating user...")
        auth = await self._client.authenticate_user(user_uuid=self.persistent_user_id, pin=self._pin)
        self.auth_token = auth.jwt_token
        self._test_user_uuid = self.persistent_user_id
        if self.current_session:
            self.current_session.user_id = self.persistent_user_id
            
    def _generate_test_uuid(self, seed: str) -> str:
        """Generate deterministic UUID from seed for testing"""
        import hashlib
        hash_object = hashlib.md5(seed.encode())
        hex_dig = hash_object.hexdigest()
        return f"{hex_dig[:8]}-{hex_dig[8:12]}-{hex_dig[12:16]}-{hex_dig[16:20]}-{hex_dig[20:32]}"
        
    async def _send_encrypted_request(self, endpoint: str, payload: Dict[str, Any], *, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self._client:
            self._client = EncryptedBenchmarkClient(self.backend_url, timeout_seconds=max(self.timeout_seconds, 30.0))
        try:
            return await self._client.request("POST", endpoint, json_body=payload, params=params)
        except Exception as e:
            print(f"❌ Encrypted request error: {e}")
            return None
            
        
    async def run_comprehensive_evaluation(self, 
                                         scenario_name: Optional[str] = None,
                                         custom_scenario: Optional[ConversationScenario] = None) -> EvaluationResult:
        """
        Run a complete memory evaluation session.
        
        Args:
            scenario_name: Name of predefined scenario to run
            custom_scenario: Custom scenario to evaluate
            
        Returns:
            Complete evaluation results with scores and analysis
        """
        # Select scenario
        if custom_scenario:
            scenario = custom_scenario
        elif scenario_name:
            scenario = self.scenario_library.get_scenario(scenario_name)
        else:
            scenario = self.scenario_library.get_scenario("comprehensive_memory_test")
            
        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_name}")
            
        try:
            # Execute conversation scenario (creates and returns session)
            session = await self._execute_conversation_scenario(scenario)
            self.current_session = session
            
            # Evaluate memory performance
            evaluation_result = await self._evaluate_memory_performance(session)
            session.evaluation_result = evaluation_result
            
            # Generate reports
            await self._generate_reports(session)
            
            return evaluation_result
            
        except Exception as e:
            if 'session' in locals():
                session.errors.append(f"Evaluation failed: {str(e)}")
            raise
        finally:
            # Clean up memory connections
            if hasattr(self.metrics, 'cleanup'):
                await self.metrics.cleanup()
                
            # Clean up test user (only if not reusing AND not using persistent user)
            if not self.reuse_user and not self.persistent_user_id:
                await self._cleanup_test_user()
                
            if 'session' in locals():
                session.end_time = datetime.now()
                self.session_history.append(session)
            # Clean up HTTP session (only if not reusing user AND not using persistent user)
            if not self.reuse_user and not self.persistent_user_id:
                await self.cleanup()
        
    # Removed duplicate method - using complete implementation below
        
    def get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trends from session history"""
        
        if not self.session_history:
            return {
                "total_sessions": 0,
                "average_overall_score": 0.0,
                "score_trend": []
            }
            
        scores = []
        for session in self.session_history:
            if hasattr(session, 'evaluation_result') and session.evaluation_result:
                scores.append(session.evaluation_result.overall_score.percentage)
                
        return {
            "total_sessions": len(self.session_history),
            "average_overall_score": sum(scores) / len(scores) if scores else 0.0,
            "score_trend": scores
        }
            
    async def _execute_conversation_scenario(self, scenario: ConversationScenario) -> EvaluationSession:
        """Execute a conversation scenario using AICO's native API"""
        
        session = EvaluationSession(
            session_id=str(uuid.uuid4()),
            scenario=scenario,
            start_time=datetime.now()
        )
        
        # Set as current session so authentication can set user_id
        self.current_session = session

        # Load active character spec from runtime configuration
        try:
            session.character_spec = load_active_character_spec()
            print(
                f"🎭 Active character: {session.character_spec.character_id} "
                f"(model: {session.character_spec.model_name})"
            )
        except Exception as e:
            session.character_spec = None
            print(f"⚠️ Failed to load active character spec: {e}")
        
        print(f"🧠 Starting conversation scenario: {scenario.name}")
        
        if not self._client:
            self._client = EncryptedBenchmarkClient(self.backend_url, timeout_seconds=max(self.timeout_seconds, 30.0))
        await self._authenticate_user()
        
        try:
            # Execute each conversation turn
            conversation_id = None
            
            for i, turn in enumerate(scenario.conversation_turns):
                turn_start = time.time()
                
                # Send message to AICO backend
                message_data = {
                    "message": turn.user_message,
                    "conversation_id": conversation_id,
                }
                # Reduced noise - only show turn progress
                print(f"💬 Turn {i+1}: {turn.user_message[:50]}...")
                
                # Send encrypted message request with timeout (match backend timeout)
                # Allow for unoptimized LLM processing + buffer
                timeout_seconds = float(self.conversation_timeout_seconds) + 10.0

                async def _attempt_send() -> dict:
                    return await asyncio.wait_for(
                        self._send_encrypted_request(
                            "/api/v1/conversation/messages",
                            message_data,
                            params={"stream": "false"},
                        ),
                        timeout=timeout_seconds,
                    )

                response_data = None
                attempt_backoffs = [0.0, 2.0]  # initial attempt + one retry
                for attempt_idx, backoff_seconds in enumerate(attempt_backoffs, start=1):
                    if backoff_seconds:
                        await asyncio.sleep(backoff_seconds)

                    try:
                        response_data = await _attempt_send()
                        if not response_data:
                            raise Exception("No response from conversation API")

                        # Backend may return a soft-timeout payload (within 15s)
                        ai_message_probe = (response_data.get("ai_response") or response_data.get("message") or "")
                        if "request timed out" in ai_message_probe.lower():
                            if attempt_idx < len(attempt_backoffs):
                                print(f"⏰ Turn {i+1} got backend timeout response; retrying once...")
                                # Preserve conversation id if backend created one
                                conversation_id = response_data.get("conversation_id", conversation_id)
                                message_data["conversation_id"] = conversation_id
                                continue
                        break

                    except asyncio.TimeoutError:
                        if attempt_idx < len(attempt_backoffs):
                            print(f"⏰ Turn {i+1} timed out after {timeout_seconds}s; retrying once...")
                            continue
                        print(f"⏰ Turn {i+1} timed out after {timeout_seconds}s")
                        response_data = {
                            "success": False,
                            "message": "[TIMEOUT] Request timed out",
                            "conversation_id": conversation_id,
                            "conversation_action": "timeout",
                            "ai_response": "[TIMEOUT] The AI response timed out",
                        }
                        break
                
                turn_end = time.time()
                response_time_ms = (turn_end - turn_start) * 1000
                
                # Extract response information
                ai_message = response_data.get("ai_response", response_data.get("message", ""))
                conversation_id = response_data.get("conversation_id", conversation_id)
                conversation_action = response_data.get("conversation_action", "continue")
                
                # Extract entities if available
                entities = response_data.get("entities_extracted", {})
                
                # Log the conversation turn
                turn_log = {
                    "turn_number": i + 1,
                    "user_message": turn.user_message,
                    "ai_response": ai_message,
                    "response_time_ms": response_time_ms,
                    "conversation_action": conversation_action,
                    "entities_extracted": entities,
                    "conversation_id": conversation_id,
                    # Include scenario expectations for evaluation
                    "expected_entities": turn.expected_entities or {},
                    "expected_context_elements": turn.expected_context_elements or [],
                    "should_remember_from_turns": turn.should_remember_from_turns or [],
                    "should_reference_entities": turn.should_reference_entities or []
                }
                
                status = "✅" if response_time_ms < 5000 else "⏰" if response_time_ms < 10000 else "🐌"
                print(f"{status} Turn {i+1}: {response_time_ms}ms | {conversation_action}")
                session.conversation_log.append(turn_log)
                
                # Print real-time feedback using Rich reporter
                self.rich_reporter.print_turn_result(i + 1, turn_log)
                
                # Small delay between turns to simulate natural conversation
                await asyncio.sleep(0.5)
                
        except Exception as e:
            print(f"❌ Conversation scenario failed: {e}")
            raise
            
        finally:
            # Keep session open for potential reuse
            pass
            
        session.end_time = datetime.now()
        session.conversation_id = conversation_id
        
        # Collect all conversation_ids used during the conversation for entity lookup
        all_conversation_ids = set()
        for turn_log in session.conversation_log:
            if turn_log.get("conversation_id"):
                all_conversation_ids.add(turn_log["conversation_id"])
        session.all_conversation_ids = list(all_conversation_ids)
        
        print(f"✅ Completed conversation scenario: {scenario.name}")
        return session

    # Removed duplicate method - using complete implementation below

    async def _evaluate_memory_performance(self, session: EvaluationSession) -> EvaluationResult:
        """Evaluate memory system performance based on conversation data"""
        
        # Initialize real memory system connections
        print("🔗 Connecting to AICO memory systems...")
        await self.metrics.initialize_memory_connections()
        
        # Calculate metrics based on observed responses and scenario expectations
        character_stability = await self.metrics.calculate_character_stability(session)
        context_adherence = await self.metrics.calculate_context_adherence(session)
        knowledge_retention = await self.metrics.calculate_knowledge_retention(session)
        entity_extraction = await self.metrics.calculate_entity_extraction_accuracy(session)
        conversation_relevancy = await self.metrics.calculate_conversation_relevancy(session)
        semantic_memory_quality = await self.metrics.calculate_semantic_memory_quality(session)
        response_quality = await self.metrics.calculate_response_quality(session)
        memory_consistency = await self.metrics.calculate_memory_consistency(session)
        performance_metrics = await self.metrics.calculate_performance_metrics(session)
        
        # Calculate overall score
        overall_score = self.metrics.calculate_overall_score([
            character_stability,
            context_adherence,
            knowledge_retention, 
            entity_extraction,
            conversation_relevancy,
            semantic_memory_quality,
            response_quality,
            memory_consistency
        ])
        
        return EvaluationResult(
            session_id=session.session_id,
            scenario_name=session.scenario.name,
            overall_score=overall_score,
            character_stability=character_stability,
            context_adherence=context_adherence,
            knowledge_retention=knowledge_retention,
            entity_extraction=entity_extraction,
            conversation_relevancy=conversation_relevancy,
            semantic_memory_quality=semantic_memory_quality,
            response_quality=response_quality,
            memory_consistency=memory_consistency,
            performance_metrics=performance_metrics,
            conversation_turns=len(session.conversation_log),
            total_duration_seconds=session.duration_seconds,
            errors=session.errors.copy()
        )
        
    async def _generate_reports(self, session: EvaluationSession):
        """Generate evaluation reports in multiple formats"""
        if not session.evaluation_result:
            return
            
        # Console report
        self.rich_reporter.print_evaluation_summary(session.evaluation_result)
        
        # JSON report for automation
        json_report = self.json_reporter.generate_report(session.evaluation_result)
        with open(f"memory_eval_{session.session_id}.json", "w") as f:
            json.dump(json_report, f, indent=2)
            
        # Detailed analysis report
        detailed_report = self.detailed_reporter.generate_report(
            session.evaluation_result, 
            session.conversation_log
        )
        with open(f"memory_eval_detailed_{session.session_id}.md", "w") as f:
            f.write(detailed_report)
            
    async def run_continuous_evaluation(self, 
                                      scenarios: List[str],
                                      iterations: int = 5,
                                      delay_seconds: float = 2.0) -> List[EvaluationResult]:
        """
        Run continuous evaluation for system improvement tracking.
        
        Args:
            scenarios: List of scenario names to run
            iterations: Number of iterations per scenario
            delay_seconds: Delay between evaluations
            
        Returns:
            List of all evaluation results
        """
        results = []
        
        for iteration in range(iterations):
            self.rich_reporter.print_iteration_start(iteration + 1, iterations)
            
            for scenario_name in scenarios:
                try:
                    result = await self.run_comprehensive_evaluation(scenario_name)
                    results.append(result)
                    
                    # Brief delay between scenarios
                    if delay_seconds > 0:
                        await asyncio.sleep(delay_seconds)
                        
                except Exception as e:
                    self.rich_reporter.print_error(f"Scenario {scenario_name} failed: {e}")
                    
        return results
        
    def get_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends across evaluation sessions"""
        if not self.session_history:
            return {"error": "No evaluation sessions available"}
            
        trends = {
            "total_sessions": len(self.session_history),
            "average_overall_score": 0.0,
            "score_trend": [],
            "performance_over_time": [],
            "common_issues": []
        }
        
        scores = []
        for session in self.session_history:
            if session.evaluation_result:
                scores.append(session.evaluation_result.overall_score.score)
                trends["score_trend"].append({
                    "timestamp": session.start_time.isoformat(),
                    "score": session.evaluation_result.overall_score.score,
                    "scenario": session.scenario.name
                })
                
        if scores:
            trends["average_overall_score"] = sum(scores) / len(scores)
            
        return trends
