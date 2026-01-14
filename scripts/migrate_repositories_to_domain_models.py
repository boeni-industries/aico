#!/usr/bin/env python3
"""
Repository Migration Script

Migrates all repositories from using aico.data.*/models to aico.ai.*/models
with internal DB field mapping.

This implements the single domain model architecture decision.
"""

import os
import re
from pathlib import Path

# Mapping of data model imports to domain model imports
MODEL_MIGRATIONS = {
    # Main module imports
    'from aico.data.agency.models import': 'from aico.ai.agency.models import',
    'from aico.data.ams.models import': 'from aico.ai.ams.models import',
    'from aico.data.auth.models import': 'from aico.ai.auth.models import',
    'from aico.data.user.models import': 'from aico.ai.user.models import',
    'from aico.data.scheduler.models import': 'from aico.ai.scheduler.models import',
    'from aico.data.system.models import': 'from aico.ai.system.models import',
    'from aico.data.consent.models import': 'from aico.ai.consent.models import',
    'from aico.data.kg.models import': 'from aico.ai.knowledge_graph.models import',
    'from aico.data.conversation.models import': 'from aico.ai.conversation.models import',
    
    # Agency sub-modules
    'from aico.data.agency.reflection_models import': 'from aico.ai.agency.models import',
    'from aico.data.agency.skill_models import': 'from aico.ai.agency.models import',
    'from aico.data.agency.execution_models import': 'from aico.ai.agency.models import',
    'from aico.data.agency.goal_models import': 'from aico.ai.agency.models import',
    
    # Auth sub-modules
    'from aico.data.auth.device_models import': 'from aico.ai.auth.models import',
    'from aico.data.auth.session_models import': 'from aico.ai.auth.models import',
    'from aico.data.auth.credentials_models import': 'from aico.ai.auth.models import',
    'from aico.data.auth.access_models import': 'from aico.ai.auth.models import',
    
    # AMS sub-modules
    'from aico.data.ams.context_models import': 'from aico.ai.ams.models import',
    
    # User sub-modules
    'from aico.data.user.proactive_models import': 'from aico.ai.user.models import',
    'from aico.data.user.feedback_models import': 'from aico.ai.user.models import',
    'from aico.data.user.relationship_models import': 'from aico.ai.user.models import',
    
    # System sub-modules
    'from aico.data.system.event_models import': 'from aico.ai.system.models import',
    'from aico.data.system.metrics_models import': 'from aico.ai.system.models import',
    
    # Scheduler sub-modules
    'from aico.data.scheduler.lock_models import': 'from aico.ai.scheduler.models import',
    
    # KG sub-modules
    'from aico.data.kg.property_models import': 'from aico.ai.knowledge_graph.models import',
    
    # Agency additional sub-modules
    'from aico.data.agency.arbiter_models import': 'from aico.ai.agency.models import',
    'from aico.data.agency.intention_models import': 'from aico.ai.agency.models import',
    
    # AMS additional sub-modules
    'from aico.data.ams.consolidation_models import': 'from aico.ai.ams.models import',
    
    # Ethics sub-modules
    'from aico.data.ethics.models import': 'from aico.ai.ethics.models import',
    'from aico.data.ethics.value_models import': 'from aico.ai.ethics.models import',
    'from aico.data.ethics.cache_models import': 'from aico.ai.ethics.models import',
    'from aico.data.ethics.gate_models import': 'from aico.ai.ethics.models import',
    'from aico.data.ethics.policy_models import': 'from aico.ai.ethics.models import',
    
    # Arbiter sub-modules
    'from aico.data.arbiter.models import': 'from aico.ai.arbiter.models import',
    'from aico.data.arbiter.ab_test_models import': 'from aico.ai.arbiter.models import',
    'from aico.data.arbiter.bandit_models import': 'from aico.ai.arbiter.models import',
    
    # Workflow sub-modules
    'from aico.data.workflow.models import': 'from aico.ai.workflow.models import',
    'from aico.data.workflow.execution_models import': 'from aico.ai.workflow.models import',
    'from aico.data.workflow.stage_models import': 'from aico.ai.workflow.models import',
    
    # Proactive sub-modules
    'from aico.data.proactive.models import': 'from aico.ai.proactive.models import',
    'from aico.data.proactive.analytics_models import': 'from aico.ai.proactive.models import',
    'from aico.data.proactive.reminder_models import': 'from aico.ai.proactive.models import',
    
    # Emotion sub-modules
    'from aico.data.emotion.models import': 'from aico.ai.emotion.models import',
    'from aico.data.emotion.state_models import': 'from aico.ai.emotion.models import',
    'from aico.data.emotion.history_models import': 'from aico.ai.emotion.models import',
    
    # Consent sub-modules
    'from aico.data.consent.audit_models import': 'from aico.ai.consent.models import',
    'from aico.data.consent.record_models import': 'from aico.ai.consent.models import',
}

# Field mappings: DB column name -> domain model field name
FIELD_MAPPINGS = {
    'metadata_json': 'metadata',
    'steps_json': 'steps',
    'tags_json': 'tags',
    'context_json': 'context',
    'payload_json': 'payload',
    'entities_json': 'entities',
    'key_moments_json': 'key_moments',
}

def migrate_repository_file(filepath: Path):
    """Migrate a single repository file."""
    print(f"Processing: {filepath.name}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Step 1: Update imports
    for old_import, new_import in MODEL_MIGRATIONS.items():
        if old_import in content:
            content = content.replace(old_import, new_import)
            print(f"  ✓ Updated import: {old_import} -> {new_import}")
    
    # Step 2: Add json import if not present and needed
    if 'metadata_json' in content or 'steps_json' in content or any(field in content for field in FIELD_MAPPINGS.keys()):
        if 'import json' not in content:
            # Add after other imports
            import_section_end = content.find('\n\nclass')
            if import_section_end > 0:
                content = content[:import_section_end] + '\nimport json' + content[import_section_end:]
                print(f"  ✓ Added json import")
    
    # Step 3: Add enum handling for create/update methods
    # Look for .value patterns and add hasattr checks
    content = re.sub(
        r'(\w+)=entity\.(\w+)\.value,',
        r'\1=entity.\2.value if hasattr(entity.\2, "value") else entity.\2,',
        content
    )
    
    # Step 4: Convert metadata_json assignments to json.dumps(metadata)
    for db_field, domain_field in FIELD_MAPPINGS.items():
        # In insert/update values
        content = re.sub(
            rf'{db_field}=entity\.{db_field}',
            rf'{db_field}=json.dumps(entity.{domain_field}) if entity.{domain_field} else None',
            content
        )
    
    # Step 5: Convert field reads from DB to domain model construction
    # This is complex - would need AST parsing for safety
    # For now, document that manual review is needed
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✅ Migrated {filepath.name}")
        return True
    else:
        print(f"  ⏭️  No changes needed for {filepath.name}")
        return False

def main():
    """Main migration function."""
    repo_dir = Path(__file__).parent.parent / 'shared' / 'aico' / 'data' / 'repositories' / 'postgres'
    
    if not repo_dir.exists():
        print(f"❌ Repository directory not found: {repo_dir}")
        return
    
    print(f"🔍 Scanning repositories in: {repo_dir}\n")
    
    migrated_count = 0
    skipped_count = 0
    
    for repo_file in sorted(repo_dir.glob('*_repository.py')):
        if repo_file.name == '__init__.py':
            continue
        
        try:
            if migrate_repository_file(repo_file):
                migrated_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            print(f"  ❌ Error processing {repo_file.name}: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ Migration complete!")
    print(f"   Migrated: {migrated_count} files")
    print(f"   Skipped: {skipped_count} files")
    print(f"{'='*60}")
    print(f"\n⚠️  IMPORTANT: Manual review required for:")
    print(f"   1. Enum conversions in get_by_id/list methods")
    print(f"   2. JSON field deserialization")
    print(f"   3. Complex field mappings")
    print(f"\n📝 Next steps:")
    print(f"   1. Review git diff for all changes")
    print(f"   2. Run: python -m py_compile shared/aico/data/repositories/postgres/*.py")
    print(f"   3. Run integration tests")
    print(f"   4. Delete aico.data.*/models.py files")

if __name__ == '__main__':
    main()
