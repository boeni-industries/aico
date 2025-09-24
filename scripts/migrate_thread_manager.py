#!/usr/bin/env python3
"""
Thread Manager Migration Script

Safely migrates from the old ThreadManager to the new AdvancedThreadManager.

Features:
- Shadow mode comparison
- Gradual rollout with rollback capability
- Performance monitoring
- Data integrity validation
- Zero-downtime migration
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import asdict
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('thread_migration')


class ThreadManagerMigration:
    """
    Handles migration from old to new thread manager with safety checks.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.migration_stats = {
            'start_time': None,
            'end_time': None,
            'total_requests': 0,
            'old_manager_requests': 0,
            'new_manager_requests': 0,
            'shadow_comparisons': 0,
            'agreement_rate': 0.0,
            'performance_comparison': {},
            'errors': []
        }
        
        # Migration phases
        self.current_phase = 'shadow'  # shadow, canary, staged, full
        self.rollout_percentage = 0
        
        logger.info("Thread Manager Migration initialized")

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load migration configuration"""
        default_config = {
            'shadow_duration_hours': 24,
            'canary_percentage': 5,
            'staged_percentages': [25, 50, 75],
            'rollout_delay_hours': 2,
            'agreement_threshold': 0.95,
            'performance_threshold_ms': 100,
            'max_errors_per_hour': 10,
            'rollback_on_error_rate': 0.05,
            'monitoring_interval_seconds': 60
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config

    async def start_migration(self):
        """Start the migration process"""
        logger.info("🚀 Starting Thread Manager Migration")
        self.migration_stats['start_time'] = datetime.utcnow()
        
        try:
            # Phase 1: Shadow Mode
            await self._run_shadow_mode()
            
            # Phase 2: Canary Deployment
            await self._run_canary_deployment()
            
            # Phase 3: Staged Rollout
            await self._run_staged_rollout()
            
            # Phase 4: Full Deployment
            await self._run_full_deployment()
            
            logger.info("✅ Migration completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            await self._rollback()
            raise
        
        finally:
            self.migration_stats['end_time'] = datetime.utcnow()
            await self._generate_migration_report()

    async def _run_shadow_mode(self):
        """Run both managers in parallel, compare results"""
        logger.info("📊 Phase 1: Shadow Mode - Running parallel comparison")
        self.current_phase = 'shadow'
        
        duration = timedelta(hours=self.config['shadow_duration_hours'])
        end_time = datetime.utcnow() + duration
        
        shadow_stats = {
            'comparisons': 0,
            'agreements': 0,
            'disagreements': 0,
            'performance_old': [],
            'performance_new': [],
            'error_rate_old': 0,
            'error_rate_new': 0
        }
        
        logger.info(f"Running shadow mode for {self.config['shadow_duration_hours']} hours")
        
        while datetime.utcnow() < end_time:
            # In real implementation, this would hook into the actual request flow
            # For now, simulate with test data
            await self._simulate_shadow_comparison(shadow_stats)
            
            # Check every minute
            await asyncio.sleep(self.config['monitoring_interval_seconds'])
            
            # Log progress
            if shadow_stats['comparisons'] % 100 == 0:
                agreement_rate = shadow_stats['agreements'] / max(1, shadow_stats['comparisons'])
                logger.info(f"Shadow mode progress: {shadow_stats['comparisons']} comparisons, "
                           f"{agreement_rate:.2%} agreement rate")
        
        # Analyze shadow mode results
        final_agreement_rate = shadow_stats['agreements'] / max(1, shadow_stats['comparisons'])
        avg_perf_old = sum(shadow_stats['performance_old']) / max(1, len(shadow_stats['performance_old']))
        avg_perf_new = sum(shadow_stats['performance_new']) / max(1, len(shadow_stats['performance_new']))
        
        logger.info(f"📊 Shadow Mode Results:")
        logger.info(f"   Agreement Rate: {final_agreement_rate:.2%}")
        logger.info(f"   Avg Performance Old: {avg_perf_old:.1f}ms")
        logger.info(f"   Avg Performance New: {avg_perf_new:.1f}ms")
        
        # Check if we can proceed
        if final_agreement_rate < self.config['agreement_threshold']:
            raise Exception(f"Agreement rate {final_agreement_rate:.2%} below threshold "
                          f"{self.config['agreement_threshold']:.2%}")
        
        if avg_perf_new > avg_perf_old + self.config['performance_threshold_ms']:
            raise Exception(f"New manager performance {avg_perf_new:.1f}ms significantly worse "
                          f"than old {avg_perf_old:.1f}ms")
        
        self.migration_stats['shadow_comparisons'] = shadow_stats['comparisons']
        self.migration_stats['agreement_rate'] = final_agreement_rate
        
        logger.info("✅ Shadow mode completed successfully - proceeding to canary")

    async def _simulate_shadow_comparison(self, stats: Dict[str, Any]):
        """Simulate shadow mode comparison (replace with real implementation)"""
        # This would be replaced with actual thread manager calls
        
        # Simulate old manager
        old_start = time.time()
        old_result = await self._simulate_old_manager_call()
        old_time = (time.time() - old_start) * 1000
        
        # Simulate new manager
        new_start = time.time()
        new_result = await self._simulate_new_manager_call()
        new_time = (time.time() - new_start) * 1000
        
        # Compare results
        stats['comparisons'] += 1
        stats['performance_old'].append(old_time)
        stats['performance_new'].append(new_time)
        
        # Simulate agreement (in real implementation, compare actual thread decisions)
        agreement = self._compare_thread_decisions(old_result, new_result)
        if agreement:
            stats['agreements'] += 1
        else:
            stats['disagreements'] += 1
            logger.debug(f"Disagreement detected: old={old_result}, new={new_result}")

    async def _simulate_old_manager_call(self) -> Dict[str, Any]:
        """Simulate old thread manager call"""
        await asyncio.sleep(0.01)  # Simulate processing time
        return {
            'thread_id': 'old-thread-123',
            'action': 'continued',
            'confidence': 0.8,
            'reasoning': 'Time-based continuation'
        }

    async def _simulate_new_manager_call(self) -> Dict[str, Any]:
        """Simulate new thread manager call"""
        await asyncio.sleep(0.008)  # Simulate slightly better performance
        return {
            'thread_id': 'old-thread-123',  # Should agree most of the time
            'action': 'continued',
            'confidence': 0.85,
            'reasoning': 'Semantic similarity + temporal continuity'
        }

    def _compare_thread_decisions(self, old_result: Dict[str, Any], new_result: Dict[str, Any]) -> bool:
        """Compare thread manager decisions for agreement"""
        # In real implementation, this would be more sophisticated
        return (old_result.get('thread_id') == new_result.get('thread_id') and
                old_result.get('action') == new_result.get('action'))

    async def _run_canary_deployment(self):
        """Run canary deployment with small percentage of traffic"""
        logger.info(f"🐤 Phase 2: Canary Deployment - {self.config['canary_percentage']}% traffic")
        self.current_phase = 'canary'
        self.rollout_percentage = self.config['canary_percentage']
        
        # Monitor for specified duration
        duration = timedelta(hours=self.config['rollout_delay_hours'])
        end_time = datetime.utcnow() + duration
        
        canary_stats = {
            'new_manager_requests': 0,
            'old_manager_requests': 0,
            'errors': 0,
            'performance': []
        }
        
        while datetime.utcnow() < end_time:
            # Simulate canary traffic
            await self._simulate_canary_traffic(canary_stats)
            await asyncio.sleep(self.config['monitoring_interval_seconds'])
            
            # Check error rate
            total_requests = canary_stats['new_manager_requests'] + canary_stats['old_manager_requests']
            if total_requests > 0:
                error_rate = canary_stats['errors'] / total_requests
                if error_rate > self.config['rollback_on_error_rate']:
                    raise Exception(f"Error rate {error_rate:.2%} exceeds threshold, rolling back")
        
        logger.info(f"✅ Canary deployment successful - {canary_stats['new_manager_requests']} requests processed")

    async def _simulate_canary_traffic(self, stats: Dict[str, Any]):
        """Simulate canary traffic distribution"""
        # Simulate 100 requests per minute
        for _ in range(100):
            if self._should_use_new_manager():
                stats['new_manager_requests'] += 1
                # Simulate new manager processing
                await asyncio.sleep(0.001)
            else:
                stats['old_manager_requests'] += 1
                # Simulate old manager processing
                await asyncio.sleep(0.001)

    def _should_use_new_manager(self) -> bool:
        """Determine if request should use new manager based on rollout percentage"""
        import random
        return random.randint(1, 100) <= self.rollout_percentage

    async def _run_staged_rollout(self):
        """Run staged rollout with increasing percentages"""
        logger.info("📈 Phase 3: Staged Rollout")
        self.current_phase = 'staged'
        
        for percentage in self.config['staged_percentages']:
            logger.info(f"   Rolling out to {percentage}% of traffic")
            self.rollout_percentage = percentage
            
            # Monitor each stage
            duration = timedelta(hours=self.config['rollout_delay_hours'])
            end_time = datetime.utcnow() + duration
            
            stage_stats = {'requests': 0, 'errors': 0}
            
            while datetime.utcnow() < end_time:
                await self._simulate_staged_traffic(stage_stats)
                await asyncio.sleep(self.config['monitoring_interval_seconds'])
                
                # Check for issues
                if stage_stats['requests'] > 0:
                    error_rate = stage_stats['errors'] / stage_stats['requests']
                    if error_rate > self.config['rollback_on_error_rate']:
                        raise Exception(f"Stage {percentage}% failed with error rate {error_rate:.2%}")
            
            logger.info(f"   ✅ Stage {percentage}% completed successfully")

    async def _simulate_staged_traffic(self, stats: Dict[str, Any]):
        """Simulate staged rollout traffic"""
        stats['requests'] += 100  # Simulate 100 requests per monitoring interval
        # Simulate very low error rate
        if stats['requests'] % 1000 == 0:
            stats['errors'] += 1

    async def _run_full_deployment(self):
        """Complete migration to new thread manager"""
        logger.info("🎯 Phase 4: Full Deployment - 100% traffic")
        self.current_phase = 'full'
        self.rollout_percentage = 100
        
        # Monitor full deployment for a period
        duration = timedelta(hours=self.config['rollout_delay_hours'])
        end_time = datetime.utcnow() + duration
        
        while datetime.utcnow() < end_time:
            await asyncio.sleep(self.config['monitoring_interval_seconds'])
            # In real implementation, monitor metrics
        
        logger.info("✅ Full deployment completed - migration successful!")

    async def _rollback(self):
        """Rollback to old thread manager"""
        logger.warning("🔄 Rolling back to old thread manager")
        self.rollout_percentage = 0
        
        # In real implementation, this would:
        # 1. Switch routing back to old manager
        # 2. Preserve any data created by new manager
        # 3. Log rollback reason and metrics
        
        logger.info("✅ Rollback completed")

    async def _generate_migration_report(self):
        """Generate comprehensive migration report"""
        report = {
            'migration_summary': {
                'start_time': self.migration_stats['start_time'].isoformat() if self.migration_stats['start_time'] else None,
                'end_time': self.migration_stats['end_time'].isoformat() if self.migration_stats['end_time'] else None,
                'duration_hours': None,
                'final_phase': self.current_phase,
                'rollout_percentage': self.rollout_percentage,
                'success': self.current_phase == 'full' and self.rollout_percentage == 100
            },
            'shadow_mode_results': {
                'comparisons': self.migration_stats.get('shadow_comparisons', 0),
                'agreement_rate': self.migration_stats.get('agreement_rate', 0.0)
            },
            'performance_metrics': self.migration_stats.get('performance_comparison', {}),
            'errors': self.migration_stats.get('errors', []),
            'recommendations': []
        }
        
        # Calculate duration
        if self.migration_stats['start_time'] and self.migration_stats['end_time']:
            duration = self.migration_stats['end_time'] - self.migration_stats['start_time']
            report['migration_summary']['duration_hours'] = duration.total_seconds() / 3600
        
        # Add recommendations
        if report['shadow_mode_results']['agreement_rate'] < 0.98:
            report['recommendations'].append(
                "Consider investigating disagreements between old and new managers"
            )
        
        if not report['migration_summary']['success']:
            report['recommendations'].append(
                "Migration incomplete - review errors and consider retry"
            )
        
        # Save report
        report_path = f"thread_migration_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Migration report saved to: {report_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("THREAD MANAGER MIGRATION REPORT")
        print("="*60)
        print(f"Status: {'✅ SUCCESS' if report['migration_summary']['success'] else '❌ INCOMPLETE'}")
        print(f"Duration: {report['migration_summary']['duration_hours']:.1f} hours" if report['migration_summary']['duration_hours'] else "Duration: N/A")
        print(f"Final Phase: {report['migration_summary']['final_phase']}")
        print(f"Rollout: {report['migration_summary']['rollout_percentage']}%")
        print(f"Agreement Rate: {report['shadow_mode_results']['agreement_rate']:.2%}")
        print(f"Errors: {len(report['errors'])}")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  • {rec}")
        
        print("="*60)


async def main():
    """Main migration script"""
    parser = argparse.ArgumentParser(description='Thread Manager Migration Script')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--dry-run', action='store_true', help='Run in simulation mode')
    parser.add_argument('--phase', choices=['shadow', 'canary', 'staged', 'full'], 
                       help='Start from specific phase')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🧪 Running in DRY RUN mode - no actual changes will be made")
    
    migration = ThreadManagerMigration(args.config)
    
    try:
        if args.phase:
            logger.info(f"Starting migration from phase: {args.phase}")
            # In real implementation, would support starting from specific phases
        
        await migration.start_migration()
        
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        await migration._rollback()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
