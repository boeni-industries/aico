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
import aiohttp

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
    
    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class MemoryIntelligenceEvaluator:
    """
    Comprehensive memory system evaluator that tests all aspects of AICO's memory
    capabilities through realistic conversation scenarios.
    
    Features:
    - Multi-turn conversation testing (6+ turns)
    - Context adherence evaluation
    - Entity extraction and retention testing
    - Semantic memory consistency checking
    - Thread management evaluation
    - Working memory persistence testing
    - Conversation continuity scoring
    - Performance benchmarking
    """
    
    def __init__(self, 
                 backend_url: str = "http://localhost:8771",
                 auth_token: Optional[str] = None,
                 timeout_seconds: int = 30):
        """
        Initialize the Memory Intelligence Evaluator.
        
        Args:
            backend_url: AICO backend API URL
            auth_token: Authentication token (if None, will attempt auto-login)
            timeout_seconds: Request timeout for API calls
        """
        self.backend_url = backend_url
        self.auth_token = auth_token
        self.timeout_seconds = timeout_seconds
        
        # Initialize AICO components (optional)
        self.config = ConfigurationManager() if ConfigurationManager else None
        
        # Initialize evaluation components
        self.metrics = MemoryMetrics()
        self.scenario_library = ScenarioLibrary()
        
        # Reporters using Rich for beautiful output
        self.rich_reporter = RichReporter()
        self.json_reporter = JSONReporter()
        self.detailed_reporter = DetailedReporter()
        
        # HTTP session for API calls
        self.session: Optional[aiohttp.ClientSession] = None
        self.encryption_context: Optional[Dict[str, Any]] = None
        self._client_private_key = None
        self._verify_key = None
        self._session_box = None
        self._test_user_uuid: Optional[str] = None
        
        # Session tracking
        self.current_session: Optional[EvaluationSession] = None
        self.session_history: List[EvaluationSession] = []
        
    async def wait_for_backend_ready(self, max_wait_seconds: int = 60) -> bool:
        """Wait for AICO backend to be ready"""
        
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)  # Short timeout for health checks
            )
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            try:
                async with self.session.get(f"{self.backend_url}/health") as response:
                    if response.status == 200:
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
        # Clean up test user first
        await self._cleanup_test_user()
        
        # Clean up HTTP session
        if self.session:
            await self.session.close()
            self.session = None
            
    async def _cleanup_test_user(self):
        """Clean up the test user created during testing"""
        if not self._test_user_uuid:
            return
            
        print(f"🧹 Cleaning up test user: {self._test_user_uuid}")
        
        try:
            import subprocess
            from pathlib import Path
            
            result = subprocess.run([
                "uv", "run", "python", "-m", "cli.aico_main", 
                "security", "user-delete", 
                self._test_user_uuid,
                "--hard",
                "--confirm"
            ], 
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True, 
            text=True,
            timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Test user cleaned up successfully")
            else:
                print(f"⚠️ Test user cleanup failed (exit code {result.returncode})")
                
        except Exception as e:
            print(f"⚠️ Test user cleanup error: {e}")
        finally:
            self._test_user_uuid = None
            
    async def _perform_handshake(self):
        """Perform encryption handshake with AICO backend"""
        try:
            print("🔐 Performing encryption handshake...")
            
            # Generate proper cryptographic keys like the working script
            from nacl.public import PrivateKey
            from nacl.signing import SigningKey
            from nacl.utils import random
            import base64
            
            # Generate ephemeral keys
            client_private_key = PrivateKey.generate()
            client_public_key = client_private_key.public_key
            signing_key = SigningKey.generate()
            verify_key = signing_key.verify_key
            
            # Generate challenge
            challenge_bytes = random(32)
            
            # Create handshake request with proper format
            handshake_request = {
                "component": "memory_evaluator",
                "identity_key": base64.b64encode(bytes(verify_key)).decode(),
                "public_key": base64.b64encode(bytes(client_public_key)).decode(),
                "timestamp": int(time.time()),
                "challenge": base64.b64encode(challenge_bytes).decode()
            }
            
            # Sign the challenge
            signature = signing_key.sign(challenge_bytes).signature
            handshake_request["signature"] = base64.b64encode(signature).decode()
            
            handshake_payload = {
                "handshake_request": handshake_request
            }
            
            # Perform handshake to get encryption keys
            async with self.session.post(
                f"{self.backend_url}/api/v1/handshake",
                json=handshake_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Handshake failed: {response.status} - {error_text}")
                
                handshake_data = await response.json()
                
                if handshake_data.get("status") != "session_established":
                    raise Exception(f"Handshake rejected: {handshake_data.get('error', 'Unknown error')}")
                
                # Store encryption context for subsequent requests
                self.encryption_context = handshake_data
                self._client_private_key = client_private_key
                self._verify_key = verify_key
                
                # Set up session encryption
                from nacl.public import PublicKey, Box
                from nacl.secret import SecretBox
                
                response_data = handshake_data["handshake_response"]
                server_public_key_b64 = response_data["public_key"]
                server_public_key = PublicKey(base64.b64decode(server_public_key_b64))
                
                # Derive shared session key
                shared_box = Box(client_private_key, server_public_key)
                session_key = shared_box.shared_key()
                self._session_box = SecretBox(session_key)
                
                print("✅ Encryption handshake successful")
                
        except Exception as e:
            print(f"❌ Handshake failed: {e}")
            raise
            
    async def _ensure_test_user(self) -> str:
        """Ensure test user exists using CLI"""
        try:
            import subprocess
            from pathlib import Path
            
            print("👤 Creating test user via CLI...")
            
            # Use the same approach as the working script
            result = subprocess.run([
                "uv", "run", "python", "-m", "cli.aico_main", 
                "security", "user-create", 
                "MemoryEvalUser",
                "--nickname", "Memory Evaluator",
                "--pin", "1234"
            ], 
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True, 
            text=True,
            timeout=30
            )
            
            if result.returncode == 0:
                # Extract UUID from output
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if line.startswith('UUID: '):
                        test_uuid = line.replace('UUID: ', '').strip()
                        print(f"✅ Test user created: {test_uuid}")
                        self._test_user_uuid = test_uuid  # Store for cleanup
                        return test_uuid
                        
            # Fallback to deterministic UUID if creation failed
            test_uuid = self._generate_test_uuid("memory_evaluator_user")
            self._test_user_uuid = test_uuid
            return test_uuid
            
        except Exception as e:
            print(f"⚠️ CLI user creation failed: {e}")
            return self._generate_test_uuid("memory_evaluator_user")

    async def _authenticate_user(self):
        """Authenticate with a test user for API access"""
        try:
            print("🔐 Authenticating user...")
            
            # Ensure test user exists
            test_user_uuid = await self._ensure_test_user()
            
            # Now authenticate
            auth_request = {
                "user_uuid": test_user_uuid,
                "pin": "1234",
                "timestamp": int(time.time())
            }
            
            # Send encrypted authentication request
            response_data = await self._send_encrypted_request("/api/v1/users/authenticate", auth_request)
            
            if response_data and response_data.get("success", False):
                self.auth_token = response_data.get("jwt_token", "")
                print("✅ Authentication successful")
            else:
                error_msg = response_data.get('message', 'Unknown error') if response_data else 'No response'
                print(f"❌ Authentication failed: {error_msg}")
                # Continue without auth for testing
                
        except Exception as e:
            print(f"⚠️ Authentication failed, continuing without auth: {e}")
            # Continue without authentication for testing
            
    def _generate_test_uuid(self, seed: str) -> str:
        """Generate deterministic UUID from seed for testing"""
        import hashlib
        hash_object = hashlib.md5(seed.encode())
        hex_dig = hash_object.hexdigest()
        return f"{hex_dig[:8]}-{hex_dig[8:12]}-{hex_dig[12:16]}-{hex_dig[16:20]}-{hex_dig[20:32]}"
        
    async def _send_encrypted_request(self, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send encrypted request and handle encrypted response"""
        if not self._session_box:
            raise RuntimeError("No active session - perform handshake first")
        
        try:
            import json
            import base64
            
            # Encrypt the payload
            plaintext = json.dumps(payload).encode()
            encrypted = self._session_box.encrypt(plaintext)
            encrypted_b64 = base64.b64encode(encrypted).decode()
            
            # Create encrypted request envelope
            request_envelope = {
                "encrypted": True,
                "payload": encrypted_b64,
                "client_id": self._verify_key.encode().hex()[:16] if self._verify_key else "memory_eval"
            }
            
            headers = {"Content-Type": "application/json"}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            async with self.session.post(
                f"{self.backend_url}{endpoint}",
                json=request_envelope,
                headers=headers
            ) as response:
                
                if response.status != 200:
                    # Try to decrypt error response
                    try:
                        error_data = await response.json()
                        if error_data.get("encrypted"):
                            encrypted_response = base64.b64decode(error_data["payload"])
                            decrypted = self._session_box.decrypt(encrypted_response)
                            error_info = json.loads(decrypted.decode())
                            raise Exception(f"Request failed ({response.status}): {error_info.get('message', 'Unknown error')}")
                    except:
                        error_text = await response.text()
                        raise Exception(f"Request failed: {response.status} - {error_text}")
                
                response_data = await response.json()
                
                # Decrypt response if encrypted
                if response_data.get("encrypted"):
                    encrypted_response = base64.b64decode(response_data["payload"])
                    decrypted = self._session_box.decrypt(encrypted_response)
                    return json.loads(decrypted.decode())
                else:
                    return response_data
                    
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
            if 'session' in locals():
                session.end_time = datetime.now()
                self.session_history.append(session)
            # Clean up HTTP session
            await self.cleanup()
        
    async def run_continuous_evaluation(self, 
                                      scenarios: List[str],
                                      iterations: int = 5,
                                      delay_seconds: float = 2.0) -> List[EvaluationResult]:
        """Run continuous evaluation for system improvement tracking"""
        
        results = []
        
        for iteration in range(iterations):
            print(f"\n🔄 Iteration {iteration + 1}/{iterations}")
            
            for scenario_name in scenarios:
                try:
                    result = await self.run_comprehensive_evaluation(scenario_name)
                    results.append(result)
                    
                    if delay_seconds > 0:
                        await asyncio.sleep(delay_seconds)
                        
                except Exception as e:
                    print(f"❌ Scenario {scenario_name} failed: {e}")
                    
        return results
        
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
        
        print(f"🧠 Starting conversation scenario: {scenario.name}")
        
        # Initialize HTTP session if not exists
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
            )
        
        # Try to perform encryption handshake (skip if it fails)
        try:
            await self._perform_handshake()
            # Authenticate user after successful handshake
            await self._authenticate_user()
        except Exception as e:
            print(f"⚠️ Handshake/auth failed, trying direct connection: {e}")
            # Continue without encryption for testing
        
        try:
            # Execute each conversation turn
            thread_id = None
            
            for i, turn in enumerate(scenario.conversation_turns):
                turn_start = time.time()
                
                # Send message to AICO backend
                message_data = {
                    "message": turn.user_message,
                    "thread_id": thread_id,
                    "context": turn.context_hints or {}
                }
                print(f"💬 Turn {i+1}: {turn.user_message[:50]}...")
                print(f"   🧠 Processing memory operations (may take up to 90s)...")
                
                # Send encrypted message request with timeout (generous for memory processing)
                try:
                    response_data = await asyncio.wait_for(
                        self._send_encrypted_request("/api/v1/conversation/messages", message_data),
                        timeout=90.0  # 90 second timeout for memory-intensive operations
                    )
                    
                    if not response_data:
                        raise Exception("No response from conversation API")
                        
                except asyncio.TimeoutError:
                    print(f"⏰ Turn {i+1} timed out after 90s")
                    # Create a timeout response for evaluation
                    response_data = {
                        "success": False,
                        "message": "[TIMEOUT] Request timed out",
                        "thread_id": thread_id,
                        "thread_action": "timeout",
                        "ai_response": "[TIMEOUT] The AI response timed out"
                    }
                
                turn_end = time.time()
                response_time_ms = (turn_end - turn_start) * 1000
                
                # Extract response information
                ai_message = response_data.get("ai_response", response_data.get("message", ""))
                thread_id = response_data.get("thread_id", thread_id)
                thread_action = response_data.get("thread_action", "continue")
                
                # Extract entities if available
                entities = response_data.get("entities_extracted", {})
                
                # Log the conversation turn
                turn_log = {
                    "turn_number": i + 1,
                    "user_message": turn.user_message,
                    "ai_response": ai_message,
                    "response_time_ms": response_time_ms,
                    "thread_action": thread_action,
                    "entities_extracted": entities,
                    "thread_id": thread_id
                }
                
                status = "✅" if response_time_ms < 10000 else "⏰" if response_time_ms < 30000 else "🐌"
                print(f"{status} Turn {i+1}: {response_time_ms:.0f}ms | {thread_action}")
                
                if response_time_ms > 30000:
                    print(f"   ⚠️ Slow response detected")
                if entities:
                    entity_summary = []
                    for entity_type, entity_list in entities.items():
                        if entity_list:
                            entity_summary.append(f"{entity_type}:{len(entity_list)}")
                    if entity_summary:
                        print(f"   🏷️ Entities: {', '.join(entity_summary)}")
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
        setattr(session, 'thread_id', thread_id)
        
        print(f"✅ Completed conversation scenario: {scenario.name}")
        return session

    async def _generate_reports(self, session: EvaluationSession):
        """Generate evaluation reports"""
        if hasattr(session, 'evaluation_result'):
            # Print beautiful results using Rich reporter
            self.rich_reporter.print_evaluation_summary(session.evaluation_result)

    async def _evaluate_memory_performance(self, session: EvaluationSession) -> EvaluationResult:
        """Evaluate memory system performance based on conversation data"""
        
        # Calculate all metrics
        context_adherence = await self.metrics.calculate_context_adherence(session)
        knowledge_retention = await self.metrics.calculate_knowledge_retention(session)
        entity_extraction = await self.metrics.calculate_entity_extraction_accuracy(session)
        conversation_relevancy = await self.metrics.calculate_conversation_relevancy(session)
        thread_management = await self.metrics.calculate_thread_management_score(session)
        response_quality = await self.metrics.calculate_response_quality(session)
        memory_consistency = await self.metrics.calculate_memory_consistency(session)
        performance_metrics = await self.metrics.calculate_performance_metrics(session)
        
        # Calculate overall score
        overall_score = self.metrics.calculate_overall_score([
            context_adherence,
            knowledge_retention, 
            entity_extraction,
            conversation_relevancy,
            thread_management,
            response_quality,
            memory_consistency
        ])
        
        return EvaluationResult(
            session_id=session.session_id,
            scenario_name=session.scenario.name,
            overall_score=overall_score,
            context_adherence=context_adherence,
            knowledge_retention=knowledge_retention,
            entity_extraction=entity_extraction,
            conversation_relevancy=conversation_relevancy,
            thread_management=thread_management,
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
