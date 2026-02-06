#!/usr/bin/env python3
"""
CI/CD Script: Validate Configuration Schemas

This script validates all domain configurations against their JSON schemas.
Exits with non-zero code if any validation errors are found.

Usage:
    python scripts/ci_validate_schemas.py
    
Exit codes:
    0 - All schemas valid
    1 - Validation errors found
    2 - Script error (missing dependencies, etc.)
"""

import sys
from pathlib import Path

# Add shared to path
shared_path = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_path))

try:
    from aico.core.config import ConfigurationManager, ConfigurationError
except ImportError as e:
    print(f"❌ Failed to import ConfigurationManager: {e}")
    print("   Make sure dependencies are installed: pip install -r requirements.txt")
    sys.exit(2)


def main():
    """Run schema validation and report results."""
    print("=" * 70)
    print("Configuration Schema Validation")
    print("=" * 70)
    print()
    
    try:
        # Initialize configuration manager
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        print("✓ Configuration loaded")
        print()
        
        # Run validation
        print("Running schema validation...")
        errors = config.validate_schemas()
        print()
        
        if not errors:
            print("=" * 70)
            print("✅ SUCCESS: All domain configurations are valid!")
            print("=" * 70)
            return 0
        
        # Report errors
        print("=" * 70)
        print(f"❌ FAILURE: Found validation errors in {len(errors)} domain(s)")
        print("=" * 70)
        print()
        
        for domain, error_messages in errors:
            print(f"Domain: {domain}")
            print("-" * 70)
            for error_msg in error_messages:
                print(f"  {error_msg}")
            print()
        
        print("=" * 70)
        print(f"Total domains with errors: {len(errors)}")
        print("=" * 70)
        
        return 1
        
    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        return 2
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
