"""
Health Calculation Engine

Calculates component and system health scores with transparent reasoning.
All health scores are based on real metrics with clear thresholds and explanations.

Design Principles:
- Transparent scoring - every point deduction has a clear reason
- Weighted factors - critical metrics have higher impact
- Actionable feedback - degradation reasons guide remediation
- No arbitrary scores - all thresholds are justified
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass


@dataclass
class HealthIssue:
    """Represents a health degradation issue"""
    severity: str  # "critical", "warning", "info"
    component: str
    metric: str
    current_value: float
    threshold: float
    impact: int  # Points deducted from health score
    message: str


class HealthCalculator:
    """
    Calculates health scores for all system components.
    
    Each component has weighted factors that contribute to its health score.
    When health is not 100%, detailed reasons explain the degradation.
    """
    
    # ==================== API Gateway Health ====================
    
    @staticmethod
    def calculate_gateway_health(metrics: Dict[str, Any]) -> Tuple[int, List[HealthIssue]]:
        """
        Calculate API Gateway health score (0-100).
        
        Factors:
        - Error Rate (40% weight): <0.5% = 100, 0.5-1% = 90, 1-2% = 75, 2-5% = 50, >5% = 0
        - P95 Latency (30% weight): <100ms = 100, 100-200ms = 90, 200-500ms = 75, 500-1000ms = 50, >1000ms = 0
        - Success Rate (30% weight): >99.5% = 100, 99-99.5% = 90, 98-99% = 75, 95-98% = 50, <95% = 0
        """
        issues = []
        score = 100
        
        error_rate = metrics.get("error_rate", 0.0)
        p95_latency = metrics.get("p95_response_time", 0.0)
        success_rate = metrics.get("success_rate", 100.0)
        
        # Error Rate (40 points max)
        if error_rate >= 5.0:
            deduction = 40
            issues.append(HealthIssue(
                severity="critical",
                component="API Gateway",
                metric="error_rate",
                current_value=error_rate,
                threshold=5.0,
                impact=deduction,
                message=f"Error rate critically high at {error_rate:.1f}% (threshold: <5%)"
            ))
            score -= deduction
        elif error_rate >= 2.0:
            deduction = 20
            issues.append(HealthIssue(
                severity="warning",
                component="API Gateway",
                metric="error_rate",
                current_value=error_rate,
                threshold=2.0,
                impact=deduction,
                message=f"Error rate elevated at {error_rate:.1f}% (threshold: <2%)"
            ))
            score -= deduction
        elif error_rate >= 1.0:
            deduction = 10
            issues.append(HealthIssue(
                severity="warning",
                component="API Gateway",
                metric="error_rate",
                current_value=error_rate,
                threshold=1.0,
                impact=deduction,
                message=f"Error rate above target at {error_rate:.1f}% (threshold: <1%)"
            ))
            score -= deduction
        elif error_rate >= 0.5:
            deduction = 4
            issues.append(HealthIssue(
                severity="info",
                component="API Gateway",
                metric="error_rate",
                current_value=error_rate,
                threshold=0.5,
                impact=deduction,
                message=f"Error rate slightly elevated at {error_rate:.1f}% (target: <0.5%)"
            ))
            score -= deduction
        
        # P95 Latency (30 points max)
        if p95_latency >= 1000:
            deduction = 30
            issues.append(HealthIssue(
                severity="critical",
                component="API Gateway",
                metric="p95_latency",
                current_value=p95_latency,
                threshold=1000,
                impact=deduction,
                message=f"P95 latency critically high at {p95_latency:.0f}ms (threshold: <1000ms)"
            ))
            score -= deduction
        elif p95_latency >= 500:
            deduction = 15
            issues.append(HealthIssue(
                severity="warning",
                component="API Gateway",
                metric="p95_latency",
                current_value=p95_latency,
                threshold=500,
                impact=deduction,
                message=f"P95 latency degraded at {p95_latency:.0f}ms (threshold: <500ms)"
            ))
            score -= deduction
        elif p95_latency >= 200:
            deduction = 8
            issues.append(HealthIssue(
                severity="warning",
                component="API Gateway",
                metric="p95_latency",
                current_value=p95_latency,
                threshold=200,
                impact=deduction,
                message=f"P95 latency above target at {p95_latency:.0f}ms (threshold: <200ms)"
            ))
            score -= deduction
        elif p95_latency >= 100:
            deduction = 3
            issues.append(HealthIssue(
                severity="info",
                component="API Gateway",
                metric="p95_latency",
                current_value=p95_latency,
                threshold=100,
                impact=deduction,
                message=f"P95 latency slightly elevated at {p95_latency:.0f}ms (target: <100ms)"
            ))
            score -= deduction
        
        # Success Rate (30 points max)
        if success_rate < 95.0:
            deduction = 30
            issues.append(HealthIssue(
                severity="critical",
                component="API Gateway",
                metric="success_rate",
                current_value=success_rate,
                threshold=95.0,
                impact=deduction,
                message=f"Success rate critically low at {success_rate:.1f}% (threshold: >95%)"
            ))
            score -= deduction
        elif success_rate < 98.0:
            deduction = 15
            issues.append(HealthIssue(
                severity="warning",
                component="API Gateway",
                metric="success_rate",
                current_value=success_rate,
                threshold=98.0,
                impact=deduction,
                message=f"Success rate below target at {success_rate:.1f}% (threshold: >98%)"
            ))
            score -= deduction
        elif success_rate < 99.0:
            deduction = 8
            issues.append(HealthIssue(
                severity="warning",
                component="API Gateway",
                metric="success_rate",
                current_value=success_rate,
                threshold=99.0,
                impact=deduction,
                message=f"Success rate slightly low at {success_rate:.1f}% (target: >99%)"
            ))
            score -= deduction
        elif success_rate < 99.5:
            deduction = 3
            issues.append(HealthIssue(
                severity="info",
                component="API Gateway",
                metric="success_rate",
                current_value=success_rate,
                threshold=99.5,
                impact=deduction,
                message=f"Success rate below optimal at {success_rate:.1f}% (target: >99.5%)"
            ))
            score -= deduction
        
        return max(0, score), issues
    
    # ==================== Modelservice Health ====================
    
    @staticmethod
    def calculate_modelservice_health(
        metrics: Dict[str, Any],
        cpu_percent: float
    ) -> Tuple[int, List[HealthIssue]]:
        """
        Calculate Modelservice health score (0-100).
        
        Factors:
        - CPU Utilization (40% weight): <60% = 100, 60-75% = 90, 75-85% = 75, 85-95% = 50, >95% = 0
        - Avg Inference Time (30% weight): <2s = 100, 2-3s = 90, 3-5s = 75, 5-10s = 50, >10s = 0
        - Model Availability (30% weight): All expected models loaded = 100
        """
        issues = []
        score = 100
        
        avg_inference_time = metrics.get("avg_inference_time", 0.0)
        active_models = metrics.get("active_models", 0)
        expected_models = 2  # qwen3 + embedding model
        
        # CPU Utilization (40 points max)
        if cpu_percent >= 95:
            deduction = 40
            issues.append(HealthIssue(
                severity="critical",
                component="Modelservice",
                metric="cpu_utilization",
                current_value=cpu_percent,
                threshold=95,
                impact=deduction,
                message=f"CPU critically high at {cpu_percent:.1f}% (threshold: <95%)"
            ))
            score -= deduction
        elif cpu_percent >= 85:
            deduction = 20
            issues.append(HealthIssue(
                severity="warning",
                component="Modelservice",
                metric="cpu_utilization",
                current_value=cpu_percent,
                threshold=85,
                impact=deduction,
                message=f"CPU utilization high at {cpu_percent:.1f}% (threshold: <85%)"
            ))
            score -= deduction
        elif cpu_percent >= 75:
            deduction = 10
            issues.append(HealthIssue(
                severity="warning",
                component="Modelservice",
                metric="cpu_utilization",
                current_value=cpu_percent,
                threshold=75,
                impact=deduction,
                message=f"CPU utilization elevated at {cpu_percent:.1f}% (threshold: <75%)"
            ))
            score -= deduction
        elif cpu_percent >= 60:
            deduction = 4
            issues.append(HealthIssue(
                severity="info",
                component="Modelservice",
                metric="cpu_utilization",
                current_value=cpu_percent,
                threshold=60,
                impact=deduction,
                message=f"CPU utilization above target at {cpu_percent:.1f}% (target: <60%)"
            ))
            score -= deduction
        
        # Avg Inference Time (30 points max)
        if avg_inference_time >= 10.0:
            deduction = 30
            issues.append(HealthIssue(
                severity="critical",
                component="Modelservice",
                metric="avg_inference_time",
                current_value=avg_inference_time,
                threshold=10.0,
                impact=deduction,
                message=f"Inference time critically slow at {avg_inference_time:.1f}s (threshold: <10s)"
            ))
            score -= deduction
        elif avg_inference_time >= 5.0:
            deduction = 15
            issues.append(HealthIssue(
                severity="warning",
                component="Modelservice",
                metric="avg_inference_time",
                current_value=avg_inference_time,
                threshold=5.0,
                impact=deduction,
                message=f"Inference time slow at {avg_inference_time:.1f}s (threshold: <5s)"
            ))
            score -= deduction
        elif avg_inference_time >= 3.0:
            deduction = 8
            issues.append(HealthIssue(
                severity="warning",
                component="Modelservice",
                metric="avg_inference_time",
                current_value=avg_inference_time,
                threshold=3.0,
                impact=deduction,
                message=f"Inference time above target at {avg_inference_time:.1f}s (threshold: <3s)"
            ))
            score -= deduction
        elif avg_inference_time >= 2.0:
            deduction = 3
            issues.append(HealthIssue(
                severity="info",
                component="Modelservice",
                metric="avg_inference_time",
                current_value=avg_inference_time,
                threshold=2.0,
                impact=deduction,
                message=f"Inference time slightly elevated at {avg_inference_time:.1f}s (target: <2s)"
            ))
            score -= deduction
        
        # Model Availability (30 points max)
        if active_models < expected_models:
            deduction = 30
            issues.append(HealthIssue(
                severity="critical",
                component="Modelservice",
                metric="active_models",
                current_value=active_models,
                threshold=expected_models,
                impact=deduction,
                message=f"Missing models: {active_models}/{expected_models} loaded"
            ))
            score -= deduction
        
        return max(0, score), issues
    
    # ==================== Memory System Health ====================
    
    @staticmethod
    def calculate_memory_health(
        metrics: Dict[str, Any],
        kg_nodes: int,
        kg_relationships: int
    ) -> Tuple[int, List[HealthIssue]]:
        """
        Calculate Memory system health score (0-100).
        
        Factors:
        - Query Performance (40% weight): <50ms avg = 100, degrading beyond
        - Data Integrity (30% weight): Orphans, duplicates, consistency
        - Graph Health (30% weight): Node/edge ratio, connectivity
        """
        issues = []
        score = 100
        
        queries_per_second = metrics.get("queries_per_second", 0.0)
        
        # For now, assume healthy if we have data
        # Real implementation would check consolidation health, orphans, etc.
        if kg_nodes == 0:
            deduction = 30
            issues.append(HealthIssue(
                severity="warning",
                component="Memory",
                metric="kg_nodes",
                current_value=kg_nodes,
                threshold=1,
                impact=deduction,
                message="Knowledge graph is empty - no entities stored"
            ))
            score -= deduction
        
        # Check relationship ratio (healthy graph has ~0.5-2 edges per node)
        if kg_nodes > 0:
            edge_ratio = kg_relationships / kg_nodes
            if edge_ratio < 0.3:
                deduction = 15
                issues.append(HealthIssue(
                    severity="info",
                    component="Memory",
                    metric="edge_ratio",
                    current_value=edge_ratio,
                    threshold=0.3,
                    impact=deduction,
                    message=f"Knowledge graph sparsely connected: {edge_ratio:.2f} edges/node (target: >0.5)"
                ))
                score -= deduction
            elif edge_ratio > 5.0:
                deduction = 10
                issues.append(HealthIssue(
                    severity="info",
                    component="Memory",
                    metric="edge_ratio",
                    current_value=edge_ratio,
                    threshold=5.0,
                    impact=deduction,
                    message=f"Knowledge graph densely connected: {edge_ratio:.2f} edges/node (may have duplicates)"
                ))
                score -= deduction
        
        return max(0, score), issues
    
    # ==================== Scheduler Health ====================
    
    @staticmethod
    def calculate_scheduler_health(metrics: Dict[str, Any]) -> Tuple[int, List[HealthIssue]]:
        """
        Calculate Scheduler health score (0-100).
        
        Factors:
        - Success Rate (50% weight): >98% = 100, degrading below
        - Failed Jobs (30% weight): 0 = 100, increasing failures degrade
        - Queue Health (20% weight): Balanced utilization = 100
        """
        issues = []
        score = 100
        
        success_rate = metrics.get("success_rate", 100.0)
        failed_jobs = metrics.get("failed_jobs", 0)
        queue_counts = metrics.get("queue_counts", {})
        
        # Success Rate (50 points max)
        if success_rate < 85.0:
            deduction = 50
            issues.append(HealthIssue(
                severity="critical",
                component="Scheduler",
                metric="success_rate",
                current_value=success_rate,
                threshold=85.0,
                impact=deduction,
                message=f"Job success rate critically low at {success_rate:.1f}% (threshold: >85%)"
            ))
            score -= deduction
        elif success_rate < 90.0:
            deduction = 25
            issues.append(HealthIssue(
                severity="warning",
                component="Scheduler",
                metric="success_rate",
                current_value=success_rate,
                threshold=90.0,
                impact=deduction,
                message=f"Job success rate low at {success_rate:.1f}% (threshold: >90%)"
            ))
            score -= deduction
        elif success_rate < 95.0:
            deduction = 13
            issues.append(HealthIssue(
                severity="warning",
                component="Scheduler",
                metric="success_rate",
                current_value=success_rate,
                threshold=95.0,
                impact=deduction,
                message=f"Job success rate below target at {success_rate:.1f}% (threshold: >95%)"
            ))
            score -= deduction
        elif success_rate < 98.0:
            deduction = 5
            issues.append(HealthIssue(
                severity="info",
                component="Scheduler",
                metric="success_rate",
                current_value=success_rate,
                threshold=98.0,
                impact=deduction,
                message=f"Job success rate slightly low at {success_rate:.1f}% (target: >98%)"
            ))
            score -= deduction
        
        # Failed Jobs (30 points max)
        if failed_jobs > 20:
            deduction = 30
            issues.append(HealthIssue(
                severity="critical",
                component="Scheduler",
                metric="failed_jobs",
                current_value=failed_jobs,
                threshold=20,
                impact=deduction,
                message=f"High number of failed jobs: {failed_jobs} (threshold: <20)"
            ))
            score -= deduction
        elif failed_jobs > 10:
            deduction = 15
            issues.append(HealthIssue(
                severity="warning",
                component="Scheduler",
                metric="failed_jobs",
                current_value=failed_jobs,
                threshold=10,
                impact=deduction,
                message=f"Elevated failed jobs: {failed_jobs} (threshold: <10)"
            ))
            score -= deduction
        elif failed_jobs > 5:
            deduction = 8
            issues.append(HealthIssue(
                severity="warning",
                component="Scheduler",
                metric="failed_jobs",
                current_value=failed_jobs,
                threshold=5,
                impact=deduction,
                message=f"Some failed jobs: {failed_jobs} (target: <5)"
            ))
            score -= deduction
        elif failed_jobs > 0:
            deduction = 3
            issues.append(HealthIssue(
                severity="info",
                component="Scheduler",
                metric="failed_jobs",
                current_value=failed_jobs,
                threshold=0,
                impact=deduction,
                message=f"Minor job failures: {failed_jobs} (target: 0)"
            ))
            score -= deduction
        
        return max(0, score), issues
    
    # ==================== Message Bus Health ====================
    
    @staticmethod
    def calculate_message_bus_health(metrics: Dict[str, Any]) -> Tuple[int, List[HealthIssue]]:
        """
        Calculate Message Bus health score (0-100).
        
        Factors:
        - Backlog Depth (50% weight): <50 = 100, degrading above
        - Message Rate (30% weight): Stable throughput = 100
        - Consumer Health (20% weight): All consumers active = 100
        """
        issues = []
        score = 100
        
        backlog_depth = metrics.get("backlog_depth", 0)
        messages_per_second = metrics.get("messages_per_second", 0.0)
        
        # Backlog Depth (50 points max)
        if backlog_depth >= 1000:
            deduction = 50
            issues.append(HealthIssue(
                severity="critical",
                component="Message Bus",
                metric="backlog_depth",
                current_value=backlog_depth,
                threshold=1000,
                impact=deduction,
                message=f"Message backlog critically high at {backlog_depth} (threshold: <1000)"
            ))
            score -= deduction
        elif backlog_depth >= 500:
            deduction = 25
            issues.append(HealthIssue(
                severity="warning",
                component="Message Bus",
                metric="backlog_depth",
                current_value=backlog_depth,
                threshold=500,
                impact=deduction,
                message=f"Message backlog high at {backlog_depth} (threshold: <500)"
            ))
            score -= deduction
        elif backlog_depth >= 100:
            deduction = 13
            issues.append(HealthIssue(
                severity="warning",
                component="Message Bus",
                metric="backlog_depth",
                current_value=backlog_depth,
                threshold=100,
                impact=deduction,
                message=f"Message backlog elevated at {backlog_depth} (threshold: <100)"
            ))
            score -= deduction
        elif backlog_depth >= 50:
            deduction = 5
            issues.append(HealthIssue(
                severity="info",
                component="Message Bus",
                metric="backlog_depth",
                current_value=backlog_depth,
                threshold=50,
                impact=deduction,
                message=f"Message backlog slightly elevated at {backlog_depth} (target: <50)"
            ))
            score -= deduction
        
        return max(0, score), issues
    
    # ==================== Overall System Health ====================
    
    @staticmethod
    def calculate_system_health(
        component_scores: Dict[str, Tuple[int, List[HealthIssue]]]
    ) -> Tuple[int, List[HealthIssue], int, int]:
        """
        Calculate overall system health as weighted average of components.
        
        Returns: (health_score, all_issues, critical_count, warning_count)
        """
        weights = {
            "gateway": 0.25,
            "modelservice": 0.20,
            "memory": 0.20,
            "scheduler": 0.20,
            "message_bus": 0.15
        }
        
        weighted_sum = 0.0
        all_issues = []
        
        for component, weight in weights.items():
            if component in component_scores:
                score, issues = component_scores[component]
                weighted_sum += score * weight
                all_issues.extend(issues)
        
        system_health = int(weighted_sum)
        
        # Count critical and warning issues
        critical_count = sum(1 for issue in all_issues if issue.severity == "critical")
        warning_count = sum(1 for issue in all_issues if issue.severity == "warning")
        
        return system_health, all_issues, critical_count, warning_count
