#!/usr/bin/env python3
"""
Initialize AICO credentials before any services start.

This ensures credentials exist in docker/.env BEFORE docker-compose reads them,
preventing password mismatches and initialization failures.

Run this ONCE before first deployment:
    python scripts/init_credentials.py
"""

import os
import secrets
from pathlib import Path


def generate_secure_password(length: int = 32) -> str:
    """Generate a cryptographically secure password."""
    return secrets.token_urlsafe(length)


def init_credentials():
    """Initialize all required credentials if they don't exist."""
    
    # Get repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    env_file = repo_root / "docker" / ".env"
    
    # Load existing credentials
    existing = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    existing[key] = value
    
    # Required credentials
    required_credentials = {
        'AICO_PG_PASSWORD': 32,
        'AICO_INFLUX_ADMIN_PASSWORD': 32,
        'AICO_INFLUX_ADMIN_TOKEN': 48,
    }
    
    # Generate missing credentials
    updated = False
    for key, length in required_credentials.items():
        if key not in existing or not existing[key]:
            existing[key] = generate_secure_password(length)
            updated = True
            print(f"✓ Generated {key}")
        else:
            print(f"✓ Using existing {key}")
    
    # Save credentials
    if updated or not env_file.exists():
        env_file.parent.mkdir(parents=True, exist_ok=True)
        with open(env_file, 'w') as f:
            for key, value in sorted(existing.items()):
                f.write(f"{key}={value}\n")
        
        # Set secure permissions
        try:
            os.chmod(env_file, 0o600)
        except Exception:
            pass
        
        print(f"\n✅ Credentials saved to {env_file}")
    else:
        print(f"\n✅ All credentials already exist in {env_file}")
    
    print("\nYou can now run: docker-compose -f docker/docker-compose.local.yml up -d")


if __name__ == "__main__":
    init_credentials()
