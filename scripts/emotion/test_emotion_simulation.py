#!/usr/bin/env python3
"""
Emotion Simulation Test Script

Runs a predefined multi-turn conversation to test and benchmark AICO's emotion simulation.
Tests emotional state transitions, persistence, and LLM conditioning.

Usage:
    python scripts/emotion/test_emotion_simulation.py <user_uuid> <pin>
    
Example:
    python scripts/emotion/test_emotion_simulation.py user_123 1234
"""

import sys
import json
import argparse
import base64
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import nacl.utils
import nacl.signing
import nacl.public
import nacl.encoding
from nacl.public import Box
from nacl.secret import SecretBox

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "shared"))
sys.path.insert(0, str(project_root / "backend"))

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class TestResult(Enum):
    """Test result status"""
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARN = "⚠️  WARN"
    SKIP = "⏭️  SKIP"


@dataclass
class EmotionExpectation:
    """Expected emotional state for a conversation turn"""
    feeling: str  # Expected primary feeling
    valence_range: tuple[float, float]  # (min, max) expected valence
    arousal_range: tuple[float, float]  # (min, max) expected arousal
    intensity_range: tuple[float, float]  # (min, max) expected intensity
    description: str  # Human-readable expectation description


@dataclass
class ConversationTurn:
    """Single conversation turn with expectations"""
    turn_number: int
    user_message: str
    expectation: EmotionExpectation
    context: str  # Context/rationale for this turn


@dataclass
class TurnResult:
    """Result of testing a single turn"""
    turn_number: int
    status: TestResult
    actual_feeling: Optional[str]
    actual_valence: Optional[float]
    actual_arousal: Optional[float]
    actual_intensity: Optional[float]
    expected: EmotionExpectation
    ai_response: Optional[str]
    errors: List[str]
    warnings: List[str]


class EmotionTestScenario:
    """Defines a test scenario with multiple conversation turns"""
    
    def __init__(self, name: str, description: str, turns: List[ConversationTurn]):
        self.name = name
        self.description = description
        self.turns = turns
    
    def to_dict(self) -> Dict[str, Any]:
        """Export scenario for analysis"""
        return {
            "name": self.name,
            "description": self.description,
            "turns": [
                {
                    "turn": t.turn_number,
                    "message": t.user_message,
                    "expectation": asdict(t.expectation),
                    "context": t.context
                }
                for t in self.turns
            ]
        }


class EmotionSimulationTester:
    """Tests emotion simulation through multi-turn conversations"""
    
    def __init__(self, base_url: str, user_uuid: str, pin: str, skip_encryption: bool = False):
        self.base_url = base_url.rstrip('/')
        self.user_uuid = user_uuid
        self.pin = pin
        self.skip_encryption = skip_encryption
        # Use requests.Session() to maintain cookies and connection
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AICO-Emotion-Test/1.0",
            "Content-Type": "application/json"
        })
        self.jwt_token: Optional[str] = None
        self.conversation_id: Optional[str] = None
        
        # Encryption keys
        self.signing_key: Optional[nacl.signing.SigningKey] = None
        self.verify_key: Optional[nacl.signing.VerifyKey] = None
        self.ephemeral_keypair: Optional[nacl.public.PrivateKey] = None
        self.server_public_key: Optional[nacl.public.PublicKey] = None
        self.session_box: Optional[SecretBox] = None
        
        # Generate client identity
        if not skip_encryption:
            self._generate_client_identity()
        
    def _generate_client_identity(self):
        """Generate Ed25519 signing keypair for client identity"""
        self.signing_key = nacl.signing.SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        self.ephemeral_keypair = nacl.public.PrivateKey.generate()
    
    def perform_handshake(self) -> bool:
        """Perform encryption handshake with proper libsodium crypto"""
        try:
            console.print(f"[dim]Performing encryption handshake...[/dim]")
            
            # Generate challenge
            challenge_bytes = nacl.utils.random(32)
            
            # Create handshake request
            handshake_request = {
                "component": "emotion_test_script",
                "identity_key": base64.b64encode(bytes(self.verify_key)).decode('utf-8'),
                "public_key": base64.b64encode(bytes(self.ephemeral_keypair.public_key)).decode('utf-8'),
                "timestamp": int(time.time()),
                "challenge": base64.b64encode(challenge_bytes).decode('utf-8')
            }
            
            # Sign the challenge with Ed25519
            signed = self.signing_key.sign(challenge_bytes)
            signature = signed.signature
            handshake_request["signature"] = base64.b64encode(signature).decode('utf-8')
            
            handshake_payload = {
                "handshake_request": handshake_request
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/handshake",
                json=handshake_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'session_established':
                    # Extract server public key and derive session key
                    handshake_response = data.get('handshake_response', {})
                    server_public_key_b64 = handshake_response.get('public_key')
                    if server_public_key_b64:
                        self.server_public_key = nacl.public.PublicKey(base64.b64decode(server_public_key_b64))
                        
                        # Derive shared session key using X25519
                        shared_box = Box(self.ephemeral_keypair, self.server_public_key)
                        session_key = shared_box.shared_key()
                        self.session_box = SecretBox(session_key)
                        
                    console.print(f"[dim]✓ Handshake complete: session established[/dim]")
                    return True
                else:
                    console.print(f"[yellow]Handshake rejected: {data.get('error', 'Unknown')}[/yellow]")
                    return False
            else:
                console.print(f"[yellow]Handshake failed: {response.status_code}[/yellow]")
                try:
                    error_data = response.json()
                    console.print(f"[yellow]Details: {error_data}[/yellow]")
                except:
                    console.print(f"[yellow]Response: {response.text}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[red]Handshake error: {type(e).__name__}: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False
    
    def encrypt_message(self, payload: Dict[str, Any]) -> str:
        """Encrypt JSON payload using session key"""
        if not self.session_box:
            raise RuntimeError("No active session - perform handshake first")
        
        plaintext = json.dumps(payload).encode()
        encrypted = self.session_box.encrypt(plaintext)
        return base64.b64encode(encrypted).decode()
    
    def decrypt_message(self, encrypted_b64: str) -> Dict[str, Any]:
        """Decrypt base64-encoded encrypted message"""
        if not self.session_box:
            raise RuntimeError("No active session - perform handshake first")
        
        encrypted = base64.b64decode(encrypted_b64)
        plaintext = self.session_box.decrypt(encrypted)
        return json.loads(plaintext.decode())
    
    def send_encrypted_request(self, endpoint: str, payload: Dict[str, Any], method: str = "POST") -> Optional[Dict[str, Any]]:
        """Send encrypted request to backend"""
        if not self.session_box:
            console.print("❌ No active session - perform handshake first")
            return None
        
        try:
            # Encrypt the payload
            encrypted_payload = self.encrypt_message(payload)
            
            # Create encrypted request envelope
            request_envelope = {
                "encrypted": True,
                "payload": encrypted_payload,
                "client_id": bytes(self.verify_key).hex()[:16]
            }
            
            # Prepare headers with JWT token for authenticated endpoints
            headers = {"Content-Type": "application/json"}
            if self.jwt_token:
                headers["Authorization"] = f"Bearer {self.jwt_token}"
            
            if method == "POST":
                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    json=request_envelope,
                    headers=headers,
                    timeout=30
                )
            else:  # GET
                response = self.session.get(
                    f"{self.base_url}{endpoint}",
                    json=request_envelope,
                    headers=headers,
                    timeout=30
                )
            
            if response.status_code != 200:
                # Try to parse and decrypt the response even if status code is not 200
                try:
                    response_data = response.json()
                    if response_data.get("encrypted"):
                        decrypted = self.decrypt_message(response_data["payload"])
                        console.print(f"❌ Request failed - HTTP {response.status_code}: {decrypted.get('message', 'Unknown error')}")
                        return decrypted
                except:
                    console.print(f"❌ Request failed - HTTP {response.status_code}: {response.text}")
                return None
            
            # Parse successful response
            response_data = response.json()
            if response_data.get("encrypted"):
                return self.decrypt_message(response_data["payload"])
            else:
                return response_data
                
        except Exception as e:
            console.print(f"❌ Request error: {e}")
            return None
    
    def authenticate(self) -> bool:
        """Authenticate and get JWT token"""
        try:
            # Perform handshake unless skipped
            if not self.skip_encryption:
                if not self.perform_handshake():
                    console.print("[red]Handshake failed - encryption is required[/red]")
                    return False
            else:
                console.print("[dim]Skipping encryption handshake (--skip-encryption)[/dim]")
            
            console.print(f"[dim]Attempting authentication at {self.base_url}/api/v1/users/authenticate[/dim]")
            
            # Use encrypted request
            auth_payload = {
                "user_uuid": self.user_uuid,
                "pin": self.pin,
                "timestamp": int(time.time())
            }
            
            response_data = self.send_encrypted_request("/api/v1/users/authenticate", auth_payload)
            
            if response_data and response_data.get("success", False):
                self.jwt_token = response_data.get("token") or response_data.get("jwt_token")
                if self.jwt_token:
                    console.print(f"✅ [green]Authenticated as {self.user_uuid}[/green]")
                    return True
                else:
                    console.print(f"❌ [red]No token in response: {response_data}[/red]")
                    return False
            else:
                error_msg = response_data.get('message', 'Unknown error') if response_data else 'No response'
                console.print(f"❌ [red]Authentication failed: {error_msg}[/red]")
                return False
                
        except requests.exceptions.ConnectionError as e:
            console.print(f"❌ [red]Connection error: Cannot connect to {self.base_url}[/red]")
            console.print(f"[yellow]Is the backend running? Try: curl {self.base_url}/health[/yellow]")
            return False
        except Exception as e:
            console.print(f"❌ [red]Authentication error: {type(e).__name__}: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False
    
    def send_message(self, message: str) -> Dict[str, Any]:
        """Send a message and get response"""
        payload = {
            "message": message,
            "user_uuid": self.user_uuid
        }
        
        if self.conversation_id:
            payload["conversation_id"] = self.conversation_id
        
        response_data = self.send_encrypted_request("/api/v1/conversation/messages", payload)
        
        if response_data:
            # Store conversation_id for subsequent turns
            if not self.conversation_id and "conversation_id" in response_data:
                self.conversation_id = response_data["conversation_id"]
            return response_data
        else:
            raise Exception("Message failed: No response")
    
    def get_emotion_state(self) -> Dict[str, Any]:
        """Get current emotional state"""
        response_data = self.send_encrypted_request("/api/v1/emotion/current", {}, method="GET")
        
        if response_data:
            return response_data
        else:
            raise Exception("Emotion state fetch failed: No response")
    
    def validate_emotion_state(
        self,
        actual: Dict[str, Any],
        expected: EmotionExpectation
    ) -> tuple[TestResult, List[str], List[str]]:
        """Validate actual emotion state against expectations"""
        errors = []
        warnings = []
        
        # Check feeling
        actual_feeling = actual.get("primary", "").lower()
        expected_feeling = expected.feeling.lower()
        
        if actual_feeling != expected_feeling:
            errors.append(
                f"Feeling mismatch: expected '{expected_feeling}', got '{actual_feeling}'"
            )
        
        # Check valence range
        actual_valence = actual.get("valence", 0.0)
        if not (expected.valence_range[0] <= actual_valence <= expected.valence_range[1]):
            errors.append(
                f"Valence out of range: expected {expected.valence_range}, got {actual_valence:.2f}"
            )
        
        # Check arousal range
        actual_arousal = actual.get("arousal", 0.0)
        if not (expected.arousal_range[0] <= actual_arousal <= expected.arousal_range[1]):
            warnings.append(
                f"Arousal out of range: expected {expected.arousal_range}, got {actual_arousal:.2f}"
            )
        
        # Check intensity range
        actual_intensity = actual.get("confidence", 0.0)  # API uses 'confidence' for intensity
        if not (expected.intensity_range[0] <= actual_intensity <= expected.intensity_range[1]):
            warnings.append(
                f"Intensity out of range: expected {expected.intensity_range}, got {actual_intensity:.2f}"
            )
        
        # Determine result
        if errors:
            return TestResult.FAIL, errors, warnings
        elif warnings:
            return TestResult.WARN, errors, warnings
        else:
            return TestResult.PASS, errors, warnings
    
    def run_turn(self, turn: ConversationTurn) -> TurnResult:
        """Execute a single conversation turn and validate"""
        try:
            # Send message
            response_data = self.send_message(turn.user_message)
            ai_response = response_data.get("response", "")
            
            # Small delay to allow emotion processing
            time.sleep(0.5)
            
            # Get emotion state
            emotion_state = self.get_emotion_state()
            
            # Validate
            status, errors, warnings = self.validate_emotion_state(
                emotion_state,
                turn.expectation
            )
            
            return TurnResult(
                turn_number=turn.turn_number,
                status=status,
                actual_feeling=emotion_state.get("primary"),
                actual_valence=emotion_state.get("valence"),
                actual_arousal=emotion_state.get("arousal"),
                actual_intensity=emotion_state.get("confidence"),
                expected=turn.expectation,
                ai_response=ai_response,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            return TurnResult(
                turn_number=turn.turn_number,
                status=TestResult.FAIL,
                actual_feeling=None,
                actual_valence=None,
                actual_arousal=None,
                actual_intensity=None,
                expected=turn.expectation,
                ai_response=None,
                errors=[f"Turn execution failed: {str(e)}"],
                warnings=[]
            )
    
    def run_scenario(self, scenario: EmotionTestScenario) -> List[TurnResult]:
        """Run complete test scenario"""
        console.print(f"\n[bold cyan]Running Scenario: {scenario.name}[/bold cyan]")
        console.print(f"[dim]{scenario.description}[/dim]\n")
        
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for turn in scenario.turns:
                task = progress.add_task(
                    f"Turn {turn.turn_number}: {turn.user_message[:50]}...",
                    total=None
                )
                
                result = self.run_turn(turn)
                results.append(result)
                
                progress.remove_task(task)
                
                # Display result
                status_icon = result.status.value
                console.print(f"\n{status_icon} Turn {turn.turn_number}: {turn.expectation.description}")
                
                # Show emotional state
                if result.actual_feeling:
                    console.print(f"   [cyan]Emotion:[/cyan] {result.actual_feeling} "
                                f"(valence: {result.actual_valence:.2f}, "
                                f"arousal: {result.actual_arousal:.2f})")
                
                # Show AI response snippet
                if result.ai_response:
                    response_preview = result.ai_response[:150] + "..." if len(result.ai_response) > 150 else result.ai_response
                    console.print(f"   [dim]AI:[/dim] {response_preview}")
                
                if result.errors:
                    for error in result.errors:
                        console.print(f"   [red]• {error}[/red]")
                
                if result.warnings:
                    for warning in result.warnings:
                        console.print(f"   [yellow]• {warning}[/yellow]")
        
        return results
    
    def cleanup(self):
        """Cleanup resources"""
        self.session.close()


def create_default_scenario() -> EmotionTestScenario:
    """Create the default emotion test scenario"""
    return EmotionTestScenario(
        name="Emotional Journey: Support Through Crisis",
        description="Tests emotional transitions from neutral through concern, empathy, and back to calm",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="Hi! How are you today?",
                expectation=EmotionExpectation(
                    feeling="neutral",
                    valence_range=(-0.1, 0.2),
                    arousal_range=(0.4, 0.6),
                    intensity_range=(0.4, 0.6),
                    description="Neutral greeting response"
                ),
                context="Initial greeting should maintain neutral baseline"
            ),
            ConversationTurn(
                turn_number=2,
                user_message="I'm feeling really stressed about work. My boss is putting a lot of pressure on me.",
                expectation=EmotionExpectation(
                    feeling="warm_concern",
                    valence_range=(0.1, 0.5),
                    arousal_range=(0.5, 0.7),
                    intensity_range=(0.6, 0.8),
                    description="Warm concern for user's stress"
                ),
                context="User expressing stress should trigger empathetic concern"
            ),
            ConversationTurn(
                turn_number=3,
                user_message="I'm worried I might lose my job if I don't meet these impossible deadlines.",
                expectation=EmotionExpectation(
                    feeling="protective",
                    valence_range=(0.0, 0.4),
                    arousal_range=(0.6, 0.8),
                    intensity_range=(0.7, 0.9),
                    description="Protective concern for user's wellbeing"
                ),
                context="Escalation to job loss fear should increase protective response"
            ),
            ConversationTurn(
                turn_number=4,
                user_message="Thank you for listening. It helps to talk about it. What do you think I should do?",
                expectation=EmotionExpectation(
                    feeling="warm_concern",
                    valence_range=(0.2, 0.5),
                    arousal_range=(0.5, 0.7),
                    intensity_range=(0.6, 0.8),
                    description="Supportive warmth with problem-solving"
                ),
                context="User seeking advice should maintain warm supportive state"
            ),
            ConversationTurn(
                turn_number=5,
                user_message="You're right. I talked to my boss and we worked out a more realistic timeline. I feel much better now!",
                expectation=EmotionExpectation(
                    feeling="calm",
                    valence_range=(0.3, 0.6),
                    arousal_range=(0.4, 0.6),
                    intensity_range=(0.5, 0.7),
                    description="Calm relief at positive resolution"
                ),
                context="Positive resolution should transition to calm satisfaction"
            ),
        ]
    )


def display_summary(scenario: EmotionTestScenario, results: List[TurnResult]):
    """Display test summary"""
    console.print("\n" + "="*80)
    console.print("[bold cyan]Test Summary[/bold cyan]")
    console.print("="*80 + "\n")
    
    # Calculate statistics
    total = len(results)
    passed = sum(1 for r in results if r.status == TestResult.PASS)
    warned = sum(1 for r in results if r.status == TestResult.WARN)
    failed = sum(1 for r in results if r.status == TestResult.FAIL)
    
    # Summary table
    summary_table = Table(title="Results Overview", box=box.ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="bold")
    
    summary_table.add_row("Total Turns", str(total))
    summary_table.add_row("✅ Passed", f"[green]{passed}[/green]")
    summary_table.add_row("⚠️  Warnings", f"[yellow]{warned}[/yellow]")
    summary_table.add_row("❌ Failed", f"[red]{failed}[/red]")
    summary_table.add_row("Success Rate", f"{(passed/total)*100:.1f}%")
    
    console.print(summary_table)
    
    # Detailed results table
    console.print("\n")
    detail_table = Table(title="Detailed Results", box=box.ROUNDED, show_lines=True)
    detail_table.add_column("Turn", justify="center", style="cyan", width=6)
    detail_table.add_column("Status", justify="center", width=10)
    detail_table.add_column("Expected", style="dim", width=15)
    detail_table.add_column("Actual", style="bold", width=15)
    detail_table.add_column("Valence", justify="right", width=8)
    detail_table.add_column("Arousal", justify="right", width=8)
    detail_table.add_column("AI Response Preview", style="dim", width=50)
    
    for result in results:
        status_color = {
            TestResult.PASS: "green",
            TestResult.WARN: "yellow",
            TestResult.FAIL: "red",
            TestResult.SKIP: "dim"
        }[result.status]
        
        # Truncate AI response for table
        ai_preview = "N/A"
        if result.ai_response:
            ai_preview = result.ai_response[:80] + "..." if len(result.ai_response) > 80 else result.ai_response
        
        detail_table.add_row(
            str(result.turn_number),
            f"[{status_color}]{result.status.value}[/{status_color}]",
            result.expected.feeling,
            result.actual_feeling or "N/A",
            f"{result.actual_valence:.2f}" if result.actual_valence is not None else "N/A",
            f"{result.actual_arousal:.2f}" if result.actual_arousal is not None else "N/A",
            ai_preview
        )
    
    console.print(detail_table)
    
    # Overall result
    console.print("\n")
    if failed == 0 and warned == 0:
        console.print(Panel(
            "[bold green]✅ ALL TESTS PASSED[/bold green]\n"
            "Emotion simulation is working as expected!",
            border_style="green"
        ))
    elif failed == 0:
        console.print(Panel(
            f"[bold yellow]⚠️  TESTS PASSED WITH {warned} WARNINGS[/bold yellow]\n"
            "Emotion simulation is mostly working but has minor deviations.",
            border_style="yellow"
        ))
    else:
        console.print(Panel(
            f"[bold red]❌ {failed} TESTS FAILED[/bold red]\n"
            "Emotion simulation has significant issues that need attention.",
            border_style="red"
        ))


def export_results(
    scenario: EmotionTestScenario,
    results: List[TurnResult],
    output_path: Path
):
    """Export test results to JSON"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "scenario": scenario.to_dict(),
        "results": [
            {
                "turn": r.turn_number,
                "status": r.status.name,
                "actual": {
                    "feeling": r.actual_feeling,
                    "valence": r.actual_valence,
                    "arousal": r.actual_arousal,
                    "intensity": r.actual_intensity
                },
                "expected": asdict(r.expected),
                "ai_response": r.ai_response,
                "errors": r.errors,
                "warnings": r.warnings
            }
            for r in results
        ],
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.status == TestResult.PASS),
            "warned": sum(1 for r in results if r.status == TestResult.WARN),
            "failed": sum(1 for r in results if r.status == TestResult.FAIL)
        }
    }
    
    output_path.write_text(json.dumps(data, indent=2))
    console.print(f"\n📄 Results exported to: [cyan]{output_path}[/cyan]")


def main():
    """Main test execution"""
    parser = argparse.ArgumentParser(
        description="Test AICO emotion simulation with multi-turn conversation"
    )
    parser.add_argument("user_uuid", help="User UUID for authentication")
    parser.add_argument("pin", help="User PIN for authentication")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8771",
        help="Backend API base URL (default: http://localhost:8771)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Export results to JSON file"
    )
    parser.add_argument(
        "--scenario",
        choices=["default"],
        default="default",
        help="Test scenario to run (default: default)"
    )
    parser.add_argument(
        "--skip-encryption",
        action="store_true",
        help="Skip encryption handshake (for testing without encryption)"
    )
    
    args = parser.parse_args()
    
    # Create tester
    tester = EmotionSimulationTester(
        args.base_url, 
        args.user_uuid, 
        args.pin,
        skip_encryption=args.skip_encryption
    )
    
    try:
        # Authenticate
        if not tester.authenticate():
            sys.exit(1)
        
        # Load scenario
        if args.scenario == "default":
            scenario = create_default_scenario()
        
        # Run tests
        results = tester.run_scenario(scenario)
        
        # Display summary
        display_summary(scenario, results)
        
        # Export if requested
        if args.output:
            export_results(scenario, results, args.output)
        
        # Exit code based on results
        failed = sum(1 for r in results if r.status == TestResult.FAIL)
        sys.exit(1 if failed > 0 else 0)
        
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
