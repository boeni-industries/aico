#!/usr/bin/env python3
"""
Schema Validation Script

Validates that the live PostgreSQL database schema matches the authoritative schema.sql file.
Reports any discrepancies between expected and actual table structures.
"""

import subprocess
import sys
import re
from typing import Dict, List, Set, Tuple


def get_live_tables() -> Set[str]:
    """Get list of tables from live database."""
    result = subprocess.run(
        [
            "docker", "exec", "-i", "aico-postgres", "sh", "-c",
            'PGPASSWORD="$POSTGRES_PASSWORD" psql -U postgres -d aico -t -c '
            '"SELECT table_name FROM information_schema.tables WHERE table_schema = \'aico_core\' ORDER BY table_name;"'
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return {line.strip() for line in result.stdout.strip().split('\n') if line.strip()}


def get_schema_tables(schema_file: str) -> Set[str]:
    """Extract table names from schema.sql."""
    tables = set()
    with open(schema_file, 'r') as f:
        content = f.read()
        # Match CREATE TABLE statements
        pattern = r'CREATE TABLE IF NOT EXISTS\s+["\']?(\w+)["\']?\s*\('
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            tables.add(match.group(1))
    return tables


def get_live_columns(table_name: str) -> Dict[str, Dict]:
    """Get column definitions from live database table."""
    result = subprocess.run(
        [
            "docker", "exec", "-i", "aico-postgres", "sh", "-c",
            f'PGPASSWORD="$POSTGRES_PASSWORD" psql -U postgres -d aico -t -c '
            f'"SELECT column_name, data_type, column_default FROM information_schema.columns '
            f'WHERE table_schema = \'aico_core\' AND table_name = \'{table_name}\' ORDER BY ordinal_position;"'
        ],
        capture_output=True,
        text=True,
        check=True
    )
    
    columns = {}
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 2:
            col_name = parts[0]
            col_type = parts[1]
            col_default = parts[2] if len(parts) > 2 else None
            columns[col_name] = {
                'type': col_type,
                'default': col_default
            }
    return columns


def get_schema_columns(schema_file: str, table_name: str) -> Dict[str, Dict]:
    """Extract column definitions from schema.sql for a specific table."""
    columns = {}
    with open(schema_file, 'r') as f:
        content = f.read()
        
        # Find the CREATE TABLE block for this table
        pattern = rf'CREATE TABLE IF NOT EXISTS\s+["\']?{table_name}["\']?\s*\((.*?)\);'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        
        if not match:
            return columns
        
        table_def = match.group(1)
        
        # Parse column definitions (simplified - doesn't handle all edge cases)
        lines = table_def.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('--') or line.upper().startswith(('PRIMARY KEY', 'FOREIGN KEY', 'CONSTRAINT', 'UNIQUE', 'CHECK')):
                continue
            
            # Remove trailing comma
            line = line.rstrip(',')
            
            # Extract column name and type
            parts = line.split()
            if len(parts) >= 2:
                col_name = parts[0].strip('"')
                col_type = parts[1].upper()
                
                # Map PostgreSQL types
                type_mapping = {
                    'TEXT': 'text',
                    'DOUBLE': 'double precision',
                    'TIMESTAMPTZ': 'timestamp with time zone',
                    'BIGSERIAL': 'bigint',
                    'JSONB': 'jsonb',
                    'BOOLEAN': 'boolean',
                    'INTEGER': 'integer',
                    'BIGINT': 'bigint',
                }
                
                mapped_type = type_mapping.get(col_type, col_type.lower())
                
                # Extract default value
                default = None
                if 'DEFAULT' in line.upper():
                    default_match = re.search(r'DEFAULT\s+(.+?)(?:\s+--|$)', line, re.IGNORECASE)
                    if default_match:
                        default = default_match.group(1).strip().rstrip(',')
                
                columns[col_name] = {
                    'type': mapped_type,
                    'default': default
                }
    
    return columns


def validate_table(schema_file: str, table_name: str) -> List[str]:
    """Validate a single table against schema.sql."""
    issues = []
    
    try:
        live_cols = get_live_columns(table_name)
        schema_cols = get_schema_columns(schema_file, table_name)
        
        # Check for missing columns in live DB
        for col_name, col_def in schema_cols.items():
            if col_name not in live_cols:
                issues.append(f"  ❌ Missing column: {col_name} {col_def['type']}")
        
        # Check for extra columns in live DB
        for col_name in live_cols:
            if col_name not in schema_cols:
                issues.append(f"  ⚠️  Extra column: {col_name} (not in schema.sql)")
        
        # Check for type mismatches
        for col_name in set(live_cols.keys()) & set(schema_cols.keys()):
            live_type = live_cols[col_name]['type']
            schema_type = schema_cols[col_name]['type']
            
            # Normalize types for comparison
            if live_type != schema_type:
                # Some acceptable variations
                if not (live_type == 'bigint' and schema_type == 'bigint'):
                    issues.append(f"  ⚠️  Type mismatch for {col_name}: live={live_type}, schema={schema_type}")
    
    except Exception as e:
        issues.append(f"  ❌ Error validating table: {e}")
    
    return issues


def main():
    schema_file = "/Users/mbo/Documents/dev/aico/shared/aico/data/postgres/schema.sql"
    
    print("🔍 Validating PostgreSQL schema against schema.sql\n")
    print("=" * 70)
    
    # Get tables from both sources
    print("\n📋 Checking table existence...")
    live_tables = get_live_tables()
    schema_tables = get_schema_tables(schema_file)
    
    print(f"   Live DB: {len(live_tables)} tables")
    print(f"   schema.sql: {len(schema_tables)} tables")
    
    # Check for missing tables
    missing_in_live = schema_tables - live_tables
    extra_in_live = live_tables - schema_tables
    
    if missing_in_live:
        print(f"\n❌ Tables in schema.sql but missing in live DB:")
        for table in sorted(missing_in_live):
            print(f"   - {table}")
    
    if extra_in_live:
        print(f"\n⚠️  Tables in live DB but not in schema.sql:")
        for table in sorted(extra_in_live):
            print(f"   - {table}")
    
    # Validate column structure for common tables
    common_tables = live_tables & schema_tables
    print(f"\n🔬 Validating {len(common_tables)} common tables...")
    
    tables_with_issues = []
    for table in sorted(common_tables):
        issues = validate_table(schema_file, table)
        if issues:
            tables_with_issues.append((table, issues))
    
    if tables_with_issues:
        print(f"\n❌ Found issues in {len(tables_with_issues)} tables:\n")
        for table, issues in tables_with_issues:
            print(f"📦 {table}:")
            for issue in issues:
                print(issue)
            print()
    else:
        print("\n✅ All common tables match schema.sql!")
    
    print("=" * 70)
    
    # Summary
    total_issues = len(missing_in_live) + len(extra_in_live) + len(tables_with_issues)
    if total_issues > 0:
        print(f"\n⚠️  Found {total_issues} discrepancies between live DB and schema.sql")
        sys.exit(1)
    else:
        print("\n✅ Schema validation passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
