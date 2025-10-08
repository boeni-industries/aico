"""
Memory System Diagnostics and Improvement Recommendations

Provides detailed analysis of evaluation results with specific, actionable
recommendations for improving the memory system.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import json

@dataclass
class DiagnosticInsight:
    """A specific diagnostic insight with recommendations"""
    category: str
    severity: str  # "critical", "warning", "info"
    issue: str
    recommendations: List[str]
    affected_scenarios: List[str]
    metric_scores: Dict[str, float]

class MemorySystemDiagnostics:
    """Analyzes evaluation results and provides actionable insights"""
    
    def __init__(self):
        self.insights = []
    
    def analyze_results(self, results: List[Tuple[str, Any]]) -> List[DiagnosticInsight]:
        """Analyze evaluation results and generate actionable insights"""
        self.insights = []
        
        # Extract metrics across all scenarios
        metrics_data = self._extract_metrics_data(results)
        
        # Analyze each metric area
        self._analyze_context_adherence(metrics_data, results)
        self._analyze_knowledge_retention(metrics_data, results)
        self._analyze_entity_extraction(metrics_data, results)
        self._analyze_cross_scenario_patterns(metrics_data, results)
        
        return self.insights
    
    def _extract_metrics_data(self, results: List[Tuple[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Extract metric scores organized by scenario and metric type"""
        metrics_data = {}
        
        for scenario_name, result in results:
            metrics_data[scenario_name] = {
                'context_adherence': result.context_adherence.percentage,
                'knowledge_retention': result.knowledge_retention.percentage,
                'entity_extraction': result.entity_extraction.percentage,
                'overall': result.overall_score.percentage
            }
        
        return metrics_data
    
    def _analyze_context_adherence(self, metrics_data: Dict, results: List[Tuple[str, Any]]):
        """Analyze context adherence issues and provide recommendations"""
        low_context_scenarios = []
        
        for scenario_name, result in results:
            score = result.context_adherence.percentage
            if score < 70:
                low_context_scenarios.append(scenario_name)
                
                # Analyze specific context adherence details
                if hasattr(result.context_adherence, 'details') and result.context_adherence.details:
                    details = result.context_adherence.details
                    
                    if 'turn_scores' in details:
                        failed_turns = [t for t in details['turn_scores'] if t['score'] < 0.5]
                        if failed_turns:
                            recommendations = [
                                f"Context retrieval failed in {len(failed_turns)} turns",
                                "Check semantic memory embedding quality",
                                "Review context relevance scoring thresholds",
                                "Verify entity boost logic in context assembly",
                                "Analyze LLM context window utilization"
                            ]
                            
                            self.insights.append(DiagnosticInsight(
                                category="Context Adherence",
                                severity="critical" if score < 50 else "warning",
                                issue=f"Poor context utilization in {scenario_name} ({score:.1f}%)",
                                recommendations=recommendations,
                                affected_scenarios=[scenario_name],
                                metric_scores={'context_adherence': score}
                            ))
    
    def _analyze_knowledge_retention(self, metrics_data: Dict, results: List[Tuple[str, Any]]):
        """Analyze knowledge retention issues"""
        for scenario_name, result in results:
            score = result.knowledge_retention.percentage
            if score < 70:
                recommendations = [
                    "Check entity extraction pipeline (GLiNER → ChromaDB)",
                    "Verify user_facts collection indexing",
                    "Review conversation segmentation logic",
                    "Analyze fact storage timing and async processing",
                    "Test memory retrieval query performance"
                ]
                
                # Add specific recommendations based on details
                if hasattr(result.knowledge_retention, 'details') and result.knowledge_retention.details:
                    details = result.knowledge_retention.details
                    if details.get('successful_references', 0) == 0:
                        recommendations.insert(0, "CRITICAL: No entity references found in AI responses")
                        recommendations.insert(1, "Check if memory context is reaching the LLM")
                
                self.insights.append(DiagnosticInsight(
                    category="Knowledge Retention",
                    severity="critical" if score < 50 else "warning",
                    issue=f"Poor knowledge retention in {scenario_name} ({score:.1f}%)",
                    recommendations=recommendations,
                    affected_scenarios=[scenario_name],
                    metric_scores={'knowledge_retention': score}
                ))
    
    def _analyze_entity_extraction(self, metrics_data: Dict, results: List[Tuple[str, Any]]):
        """Analyze entity extraction issues with precision/recall insights"""
        for scenario_name, result in results:
            score = result.entity_extraction.percentage
            if score < 70:
                recommendations = [
                    "Review GLiNER model performance for this conversation type",
                    "Check NER request/response pipeline",
                    "Verify entity storage in ChromaDB user_facts collection",
                    "Analyze entity type coverage (PERSON, GPE, ORG, etc.)"
                ]
                
                # Add specific recommendations based on precision/recall
                if hasattr(result.entity_extraction, 'details') and result.entity_extraction.details:
                    details = result.entity_extraction.details
                    if 'gliner_tests' in details:
                        low_precision = [t for t in details['gliner_tests'] if t.get('precision', 1) < 0.7]
                        low_recall = [t for t in details['gliner_tests'] if t.get('recall', 1) < 0.7]
                        
                        if low_precision:
                            recommendations.insert(0, f"Low precision in {len(low_precision)} turns - too many false positives")
                        if low_recall:
                            recommendations.insert(0, f"Low recall in {len(low_recall)} turns - missing expected entities")
                
                self.insights.append(DiagnosticInsight(
                    category="Entity Extraction",
                    severity="critical" if score < 50 else "warning",
                    issue=f"Poor entity extraction in {scenario_name} ({score:.1f}%)",
                    recommendations=recommendations,
                    affected_scenarios=[scenario_name],
                    metric_scores={'entity_extraction': score}
                ))
    
    def _analyze_cross_scenario_patterns(self, metrics_data: Dict, results: List[Tuple[str, Any]]):
        """Analyze patterns across multiple scenarios"""
        # Find consistently weak metrics across scenarios
        metric_averages = {}
        for metric in ['context_adherence', 'knowledge_retention', 'entity_extraction']:
            scores = [data[metric] for data in metrics_data.values()]
            metric_averages[metric] = sum(scores) / len(scores)
        
        # Identify systemic issues
        weakest_metric = min(metric_averages, key=metric_averages.get)
        weakest_score = metric_averages[weakest_metric]
        
        if weakest_score < 60:
            affected_scenarios = [
                scenario for scenario, data in metrics_data.items() 
                if data[weakest_metric] < 70
            ]
            
            systemic_recommendations = {
                'context_adherence': [
                    "SYSTEMIC ISSUE: Context retrieval system needs overhaul",
                    "Review semantic memory embedding model quality",
                    "Optimize context relevance scoring algorithm",
                    "Check context assembly deduplication logic",
                    "Analyze LLM context window management"
                ],
                'knowledge_retention': [
                    "SYSTEMIC ISSUE: Memory storage/retrieval pipeline broken",
                    "Audit ChromaDB user_facts collection integrity",
                    "Review entity extraction → storage pipeline",
                    "Check async memory processing timing",
                    "Verify conversation segmentation logic"
                ],
                'entity_extraction': [
                    "SYSTEMIC ISSUE: Entity extraction system needs attention",
                    "Evaluate GLiNER model performance across domains",
                    "Review NER service integration",
                    "Check entity storage format and indexing",
                    "Analyze entity type coverage gaps"
                ]
            }
            
            self.insights.append(DiagnosticInsight(
                category="Systemic Issue",
                severity="critical",
                issue=f"Consistent {weakest_metric.replace('_', ' ')} failures across scenarios ({weakest_score:.1f}% avg)",
                recommendations=systemic_recommendations[weakest_metric],
                affected_scenarios=affected_scenarios,
                metric_scores=metric_averages
            ))
    
    def generate_report(self, results: List[Tuple[str, Any]], output_file: str = None) -> str:
        """Generate a comprehensive diagnostic report"""
        insights = self.analyze_results(results)
        
        report = []
        report.append("# AICO Memory System Diagnostic Report")
        report.append("=" * 50)
        report.append("")
        
        # Summary
        critical_issues = [i for i in insights if i.severity == "critical"]
        warning_issues = [i for i in insights if i.severity == "warning"]
        
        report.append(f"## Summary")
        report.append(f"- Critical Issues: {len(critical_issues)}")
        report.append(f"- Warning Issues: {len(warning_issues)}")
        report.append(f"- Total Insights: {len(insights)}")
        report.append("")
        
        # Detailed insights
        for insight in insights:
            severity_icon = "🚨" if insight.severity == "critical" else "⚠️" if insight.severity == "warning" else "ℹ️"
            report.append(f"## {severity_icon} {insight.category}: {insight.issue}")
            report.append("")
            report.append("**Affected Scenarios:**")
            for scenario in insight.affected_scenarios:
                report.append(f"- {scenario}")
            report.append("")
            report.append("**Recommendations:**")
            for rec in insight.recommendations:
                report.append(f"- {rec}")
            report.append("")
            report.append("**Metric Scores:**")
            for metric, score in insight.metric_scores.items():
                report.append(f"- {metric.replace('_', ' ').title()}: {score:.1f}%")
            report.append("")
            report.append("-" * 40)
            report.append("")
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
        
        return report_text
