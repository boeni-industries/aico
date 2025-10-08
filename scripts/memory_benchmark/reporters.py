"""
Memory Evaluation Reporters

Beautiful reporting formats using Rich for stunning visual output, plus JSON and 
Markdown reports for automation and detailed analysis.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from dataclasses import asdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.tree import Tree
from rich import box
from rich.live import Live
from rich.layout import Layout

# Add shared path for AICO modules
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

# Skip logging for now to avoid initialization issues
# from aico.core.logging import get_logger

from .metrics import EvaluationResult, MetricScore
from .scenarios import ConversationScenario


class RichReporter:
    """Award-winning Rich-based reporter with stunning visual output"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.console = Console()
        
    def print_scenario_start(self, scenario: ConversationScenario):
        """Print beautiful scenario start information"""
        
        # Get test areas
        test_areas = self._get_test_areas(scenario)
        
        # Create scenario info panel
        scenario_info = f"""
[bold cyan]Scenario:[/bold cyan] {scenario.name}
[bold cyan]Description:[/bold cyan] {scenario.description}

[bold yellow]Configuration:[/bold yellow]
• Conversation Turns: {len(scenario.conversation_turns)}
• Difficulty Level: {scenario.difficulty_level}
• Estimated Duration: ~{scenario.estimated_duration_minutes} minutes

[bold green]Memory Systems Tested:[/bold green]
{chr(10).join([f"• {area}" for area in test_areas])}
        """.strip()
        
        self.console.print(Panel(
            scenario_info,
            title="🧠 [bold magenta]Memory Evaluation Starting[/bold magenta]",
            border_style="bright_blue",
            padding=(1, 2),
            expand=False
        ))
        
    def print_turn_result(self, turn_number: int, turn_log: Dict[str, Any]):
        """Print beautiful individual turn results with Rich formatting"""
        
        user_msg = turn_log.get("user_message", "")
        ai_response = turn_log.get("ai_response", "")
        response_time = turn_log.get("response_time_ms", 0)
        thread_action = turn_log.get("thread_action", "unknown")
        
        # Truncate messages for display
        user_display = user_msg[:77] + "..." if len(user_msg) > 80 else user_msg
        ai_display = ai_response[:77] + "..." if len(ai_response) > 80 else ai_response
        
        # Create turn table
        turn_table = Table.grid(padding=1)
        turn_table.add_column(style="bold cyan", width=12)
        turn_table.add_column(style="white", width=68)
        
        turn_table.add_row("👤 User:", f"[white]{user_display}[/white]")
        turn_table.add_row("🤖 AICO:", f"[dim white]{ai_display}[/dim white]")
        
        # Performance indicators
        time_color = "green" if response_time < 1500 else "yellow" if response_time < 2500 else "red"
        thread_color = "green" if thread_action in ["continue", "created"] else "yellow"
        
        turn_table.add_row("⚡ Metrics:", f"[{time_color}]{response_time:.0f}ms[/{time_color}] | [{thread_color}]{thread_action}[/{thread_color}]")
        
        # Show entities if available
        entities = turn_log.get("entities_extracted", {})
        if entities:
            entities_str = ", ".join([f"[yellow]{k}[/yellow]:{len(v)}" for k, v in entities.items() if v])
            turn_table.add_row("🏷️  Entities:", entities_str)
        
        self.console.print()  # Add newline before panel
        self.console.print(Panel(
            turn_table,
            title=f"💬 [bold blue]Turn {turn_number}[/bold blue]",
            border_style="dim blue",
            padding=(0, 1),
            expand=False
        ))
        
    def print_evaluation_summary(self, result: EvaluationResult):
        """Print comprehensive evaluation summary"""
        print(f"\n{'='*60}")
        print(f"📊 EVALUATION RESULTS")
        print(f"{'='*60}")
        
        # Overall score with visual indicator
        overall_pct = result.overall_score.percentage
        score_indicator = self._get_score_indicator(overall_pct)
        print(f"🎯 Overall Score: {overall_pct:.1f}% {score_indicator}")
        print()
        
        # Individual metrics
        metrics = [
            ("Context Adherence", result.context_adherence),
            ("Knowledge Retention", result.knowledge_retention),
            ("Entity Extraction", result.entity_extraction),
            ("Conversation Relevancy", result.conversation_relevancy),
            ("Semantic Memory Quality", result.semantic_memory_quality),
            ("Response Quality", result.response_quality),
            ("Memory Consistency", result.memory_consistency)
        ]
        
        print("📈 Detailed Metrics:")
        for name, metric in metrics:
            pct = metric.percentage
            indicator = self._get_score_indicator(pct)
            print(f"  {name:.<25} {pct:>6.1f}% {indicator}")
            
        print()
        
        # Performance metrics
        perf = result.performance_metrics
        print("⚡ Performance:")
        print(f"  Average Response Time........ {perf.get('average_response_time_ms', 0):.0f}ms")
        print(f"  Max Response Time............ {perf.get('max_response_time_ms', 0):.0f}ms")
        print(f"  Total Duration............... {result.total_duration_seconds:.1f}s")
        print(f"  Turns per Minute............. {perf.get('turns_per_minute', 0):.1f}")
        print()
        
        # Errors and issues
        if result.errors:
            print("⚠️  Issues Found:")
            for error in result.errors:
                print(f"  • {error}")
            print()
            
        # Success criteria check
        self._print_success_criteria_check(result)
        
        print(f"{'='*60}\n")
        
    def print_iteration_start(self, iteration: int, total_iterations: int):
        """Print iteration start for continuous evaluation"""
        print(f"\n🔄 ITERATION {iteration}/{total_iterations}")
        
    def print_error(self, error_message: str):
        """Print error message"""
        print(f"❌ ERROR: {error_message}")
        
    def _get_test_areas(self, scenario):
        """Get list of V2 test areas for scenario"""
        areas = []
        if scenario.tests_working_memory: areas.append("Working Memory (LMDB)")
        if scenario.tests_semantic_memory: areas.append("Semantic Memory (ChromaDB)")
        if scenario.tests_fact_extraction: areas.append("Fact Extraction (GLiNER + LLM)")
        if scenario.tests_entity_extraction: areas.append("Entity Extraction")
        if scenario.tests_conversation_strength: areas.append("Conversation Strength")
        return areas
        
    def _get_score_indicator(self, percentage: float) -> str:
        """Get visual indicator for score percentage"""
        if percentage >= 90: return "🟢Excellent"
        elif percentage >= 80: return "🟡 Good"
        elif percentage >= 70: return "🟠 Fair"
        elif percentage >= 60: return "🔴 Poor"
        else: return "💀 Critical"
        
    def _print_success_criteria_check(self, result: EvaluationResult):
        """Print success criteria evaluation"""
        # This would check against scenario success criteria
        # For now, use general thresholds
        print("✅ Success Criteria:")
        
        criteria = [
            ("Overall Performance", result.overall_score.percentage, 85.0),
            ("Context Adherence", result.context_adherence.percentage, 85.0),
            ("Knowledge Retention", result.knowledge_retention.percentage, 90.0),
            ("Entity Extraction", result.entity_extraction.percentage, 80.0)
        ]
        
        for name, actual, threshold in criteria:
            status = "✅ PASS" if actual >= threshold else "❌ FAIL"
            print(f"  {name:.<25} {actual:>6.1f}% (≥{threshold:.0f}%) {status}")


class JSONReporter:
    """JSON reporter for automation and data analysis"""
    
    def generate_report(self, result: EvaluationResult) -> Dict[str, Any]:
        """Generate JSON report from evaluation result"""
        
        # Convert dataclass to dict with custom serialization
        report = {
            "metadata": {
                "session_id": result.session_id,
                "scenario_name": result.scenario_name,
                "timestamp": result.timestamp.isoformat(),
                "conversation_turns": result.conversation_turns,
                "total_duration_seconds": result.total_duration_seconds,
                "version": "1.0.0"
            },
            "scores": {
                "overall": self._metric_to_dict(result.overall_score),
                "context_adherence": self._metric_to_dict(result.context_adherence),
                "knowledge_retention": self._metric_to_dict(result.knowledge_retention),
                "entity_extraction": self._metric_to_dict(result.entity_extraction),
                "conversation_relevancy": self._metric_to_dict(result.conversation_relevancy),
                "semantic_memory_quality": self._metric_to_dict(result.semantic_memory_quality),
                "response_quality": self._metric_to_dict(result.response_quality),
                "memory_consistency": self._metric_to_dict(result.memory_consistency)
            },
            "performance": result.performance_metrics,
            "errors": result.errors,
            "summary": {
                "passed": result.overall_score.percentage >= 85.0,
                "grade": self._calculate_grade(result.overall_score.percentage),
                "key_strengths": self._identify_strengths(result),
                "improvement_areas": self._identify_weaknesses(result)
            }
        }
        
        return report
        
    def _metric_to_dict(self, metric: MetricScore) -> Dict[str, Any]:
        """Convert MetricScore to dictionary"""
        return {
            "score": metric.score,
            "percentage": metric.percentage,
            "max_score": metric.max_score,
            "explanation": metric.explanation,
            "details": metric.details
        }
        
    def _calculate_grade(self, percentage: float) -> str:
        """Calculate letter grade from percentage"""
        if percentage >= 95: return "A+"
        elif percentage >= 90: return "A"
        elif percentage >= 85: return "B+"
        elif percentage >= 80: return "B"
        elif percentage >= 75: return "C+"
        elif percentage >= 70: return "C"
        elif percentage >= 65: return "D+"
        elif percentage >= 60: return "D"
        else: return "F"
        
    def _identify_strengths(self, result: EvaluationResult) -> List[str]:
        """Identify key strengths from evaluation"""
        strengths = []
        
        metrics = [
            ("Context Adherence", result.context_adherence.percentage),
            ("Knowledge Retention", result.knowledge_retention.percentage),
            ("Entity Extraction", result.entity_extraction.percentage),
            ("Conversation Relevancy", result.conversation_relevancy.percentage),
            ("Semantic Memory Quality", result.semantic_memory_quality.percentage),
            ("Response Quality", result.response_quality.percentage),
            ("Memory Consistency", result.memory_consistency.percentage)
        ]
        
        for name, score in metrics:
            if score >= 90:
                strengths.append(name)
                
        return strengths
        
    def _identify_weaknesses(self, result: EvaluationResult) -> List[str]:
        """Identify areas needing improvement"""
        weaknesses = []
        
        metrics = [
            ("Context Adherence", result.context_adherence.percentage),
            ("Knowledge Retention", result.knowledge_retention.percentage),
            ("Entity Extraction", result.entity_extraction.percentage),
            ("Conversation Relevancy", result.conversation_relevancy.percentage),
            ("Semantic Memory Quality", result.semantic_memory_quality.percentage),
            ("Response Quality", result.response_quality.percentage),
            ("Memory Consistency", result.memory_consistency.percentage)
        ]
        
        for name, score in metrics:
            if score < 80:
                weaknesses.append(name)
                
        return weaknesses


class DetailedReporter:
    """Detailed analysis reporter for in-depth evaluation review"""
    
    def generate_report(self, result: EvaluationResult, conversation_log: List[Dict[str, Any]]) -> str:
        """Generate detailed markdown report"""
        
        report_lines = []
        
        # Header
        report_lines.extend([
            f"# AICO Memory System Evaluation Report",
            f"",
            f"**Session ID:** {result.session_id}",
            f"**Scenario:** {result.scenario_name}",
            f"**Timestamp:** {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {result.total_duration_seconds:.1f} seconds",
            f"**Conversation Turns:** {result.conversation_turns}",
            f"",
            f"## Executive Summary",
            f"",
            f"Overall Score: **{result.overall_score.percentage:.1f}%** ({self._get_grade(result.overall_score.percentage)})",
            f"",
            f"{result.overall_score.explanation}",
            f""
        ])
        
        # Detailed metrics analysis
        report_lines.extend([
            f"## Detailed Metrics Analysis",
            f"",
            self._generate_metric_section("Context Adherence", result.context_adherence),
            self._generate_metric_section("Knowledge Retention", result.knowledge_retention),
            self._generate_metric_section("Entity Extraction", result.entity_extraction),
            self._generate_metric_section("Conversation Relevancy", result.conversation_relevancy),
            self._generate_metric_section("Semantic Memory Quality", result.semantic_memory_quality),
            self._generate_metric_section("Response Quality", result.response_quality),
            self._generate_metric_section("Memory Consistency", result.memory_consistency)
        ])
        
        # Performance analysis
        report_lines.extend([
            f"## Performance Analysis",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Average Response Time | {result.performance_metrics.get('average_response_time_ms', 0):.0f}ms |",
            f"| Maximum Response Time | {result.performance_metrics.get('max_response_time_ms', 0):.0f}ms |",
            f"| Minimum Response Time | {result.performance_metrics.get('min_response_time_ms', 0):.0f}ms |",
            f"| Turns per Minute | {result.performance_metrics.get('turns_per_minute', 0):.1f} |",
            f""
        ])
        
        # Conversation analysis
        report_lines.extend([
            f"## Conversation Flow Analysis",
            f""
        ])
        
        for i, turn in enumerate(conversation_log):
            turn_num = i + 1
            user_msg = turn.get("user_message", "")
            ai_response = turn.get("ai_response", "")
            response_time = turn.get("response_time_ms", 0)
            thread_action = turn.get("thread_action", "unknown")
            
            report_lines.extend([
                f"### Turn {turn_num}",
                f"",
                f"**User:** {user_msg}",
                f"",
                f"**AICO:** {ai_response}",
                f"",
                f"**Metadata:**",
                f"- Response Time: {response_time:.0f}ms",
                f"- Thread Action: {thread_action}",
                f"- Expected Entities: {', '.join(f'{k}:{v}' for k, v in turn.get('expected_entities', {}).items())}",
                f""
            ])
            
        # Issues and recommendations
        if result.errors:
            report_lines.extend([
                f"## Issues Identified",
                f""
            ])
            for error in result.errors:
                report_lines.append(f"- {error}")
            report_lines.append("")
            
        # Recommendations
        report_lines.extend([
            f"## Recommendations",
            f"",
            *self._generate_recommendations(result),
            f"",
            f"## Conclusion",
            f"",
            self._generate_conclusion(result),
            f"",
            f"---",
            f"*Report generated by AICO Memory Intelligence Evaluator v1.0.0*"
        ])
        
        return "\n".join(report_lines)
        
    def _generate_metric_section(self, name: str, metric: MetricScore) -> str:
        """Generate detailed section for a metric"""
        lines = [
            f"### {name}",
            f"",
            f"**Score:** {metric.percentage:.1f}% ({metric.score:.3f}/{metric.max_score:.3f})",
            f"",
            f"**Analysis:** {metric.explanation}",
            f""
        ]
        
        if metric.details:
            lines.extend([
                f"**Details:**",
                f"```json",
                json.dumps(metric.details, indent=2),
                f"```",
                f""
            ])
            
        return "\n".join(lines)
        
    def _get_grade(self, percentage: float) -> str:
        """Get letter grade for percentage"""
        if percentage >= 95: return "A+"
        elif percentage >= 90: return "A"
        elif percentage >= 85: return "B+"
        elif percentage >= 80: return "B"
        elif percentage >= 75: return "C+"
        elif percentage >= 70: return "C"
        else: return "D/F"
        
    def _generate_recommendations(self, result: EvaluationResult) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Check each metric and provide specific recommendations
        if result.context_adherence.percentage < 85:
            recommendations.append("- **Context Adherence:** Improve context assembly and relevance scoring in memory system")
            
        if result.knowledge_retention.percentage < 90:
            recommendations.append("- **Knowledge Retention:** Enhance episodic memory storage and retrieval mechanisms")
            
        if result.entity_extraction.percentage < 80:
            recommendations.append("- **Entity Extraction:** Review NER model performance and entity recognition patterns")
            
        if result.conversation_relevancy.percentage < 85:
            recommendations.append("- **Conversation Relevancy:** Improve response generation and topic coherence")
            
        if result.semantic_memory_quality.percentage < 95:
            recommendations.append("- **Semantic Memory Quality:** Fine-tune semantic memory retrieval and relevance scoring")
            
        if result.response_quality.percentage < 80:
            recommendations.append("- **Response Quality:** Enhance LLM prompting and response validation")
            
        if result.memory_consistency.percentage < 95:
            recommendations.append("- **Memory Consistency:** Implement better contradiction detection and fact verification")
            
        # Performance recommendations
        avg_response_time = result.performance_metrics.get('average_response_time_ms', 0)
        if avg_response_time > 2000:
            recommendations.append(f"- **Performance:** Optimize response time (current: {avg_response_time:.0f}ms)")
            
        if not recommendations:
            recommendations.append("- System performance is excellent across all metrics")
            
        return recommendations
        
    def _generate_conclusion(self, result: EvaluationResult) -> str:
        """Generate evaluation conclusion"""
        overall_pct = result.overall_score.percentage
        
        if overall_pct >= 90:
            return "The AICO memory system demonstrates excellent performance across all evaluation criteria. The system successfully maintains context, retains knowledge, and provides coherent conversational experiences."
        elif overall_pct >= 80:
            return "The AICO memory system shows good overall performance with some areas for improvement. The core memory functionality is solid but could benefit from targeted optimizations."
        elif overall_pct >= 70:
            return "The AICO memory system has acceptable performance but requires significant improvements in several key areas to meet production quality standards."
        else:
            return "The AICO memory system requires substantial improvements across multiple areas before it can provide reliable conversational AI experiences."
