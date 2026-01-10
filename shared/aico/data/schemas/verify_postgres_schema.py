#!/usr/bin/env python3
"""
Verify that the generated PostgreSQL schema matches the SQLite schema.
Performs table-by-table, field-by-field, and type conversion verification.
"""

import re
from pathlib import Path

# Read the SQLite schema
from schema import V1_SCHEMA

# Read the generated Postgres schema
postgres_schema_path = Path(__file__).parent / "../postgres/schema.sql"
with open(postgres_schema_path, 'r') as f:
    postgres_schema = f.read()


def extract_sqlite_tables(schema_statements):
    """Extract table definitions from SQLite schema."""
    tables = {}
    for stmt in schema_statements:
        if 'CREATE TABLE' in stmt.upper():
            # Extract table name
            match = re.search(r'CREATE TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+["]?(\w+)["]?\s*\(', stmt, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                # Skip otel_* tables - they should not be in Postgres
                if table_name.startswith('otel_'):
                    continue
                tables[table_name] = stmt
    return tables


def extract_postgres_tables(schema_text):
    """Extract table definitions from Postgres schema."""
    tables = {}
    # Split by CREATE TABLE statements
    pattern = r'CREATE TABLE IF NOT EXISTS\s+"?(\w+)"?\s*\((.*?)\);'
    matches = re.finditer(pattern, schema_text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        table_name = match.group(1)
        table_def = match.group(0)
        tables[table_name] = table_def
    
    return tables


def extract_fields(table_def):
    """Extract field definitions from a table."""
    fields = {}
    lines = table_def.split('\n')
    
    for line in lines:
        stripped = line.strip()
        # Skip CREATE TABLE line, closing paren, empty lines, comments, constraints
        if (not stripped or 
            stripped.startswith('CREATE TABLE') or 
            stripped.startswith(')') or
            stripped.startswith('--') or
            'PRIMARY KEY' in stripped and ',' not in stripped or
            'FOREIGN KEY' in stripped or
            'UNIQUE' in stripped and '(' in stripped):
            continue
        
        # Extract field name and type
        # Match: field_name TYPE [constraints]
        match = re.match(r'(\w+)\s+(\w+(?:\s+\w+)*)', stripped)
        if match:
            field_name = match.group(1)
            field_type = match.group(2).split()[0]  # Get just the type, not constraints
            fields[field_name] = field_type
    
    return fields


def verify_type_conversion(sqlite_type, postgres_type, field_name=''):
    """Verify that SQLite type was correctly converted to PostgreSQL type."""
    conversions = {
        'INTEGER': ['BIGSERIAL', 'INTEGER', 'BIGINT', 'BOOLEAN'],  # BOOLEAN is valid for 0/1 fields
        'TEXT': ['TEXT', 'JSONB'],  # JSONB is valid for *_json fields
        'REAL': ['DOUBLE'],
        'BLOB': ['BYTEA'],
        'JSON': ['JSONB'],
        'TIMESTAMP': ['TIMESTAMPTZ', 'TEXT'],  # TEXT is acceptable for timestamp fields
        'DATETIME': ['TIMESTAMPTZ', 'TEXT'],
        'BOOLEAN': ['BOOLEAN', 'INTEGER'],
    }
    
    sqlite_base = sqlite_type.upper().split()[0]
    postgres_base = postgres_type.upper().split()[0]
    
    # Special case: INTEGER → BOOLEAN is valid for boolean-like fields
    if sqlite_base == 'INTEGER' and postgres_base == 'BOOLEAN':
        # Common boolean field names
        boolean_indicators = ['active', 'enabled', 'is_', 'has_', 'success', 'processed', 'current']
        if any(indicator in field_name.lower() for indicator in boolean_indicators):
            return True
    
    # Special case: TEXT → JSONB is valid for *_json fields
    if sqlite_base == 'TEXT' and postgres_base == 'JSONB':
        if field_name.endswith('_json') or 'json' in field_name.lower():
            return True
    
    if sqlite_base in conversions:
        return postgres_base in conversions[sqlite_base]
    
    # If not in our conversion map, they should match
    return sqlite_base == postgres_base


def main():
    print("=" * 80)
    print("PostgreSQL Schema Verification")
    print("=" * 80)
    print()
    
    # Extract tables
    sqlite_tables = extract_sqlite_tables(V1_SCHEMA)
    postgres_tables = extract_postgres_tables(postgres_schema)
    
    print(f"📊 SQLite tables (excluding otel_*): {len(sqlite_tables)}")
    print(f"📊 Postgres tables: {len(postgres_tables)}")
    print()
    
    # Check for missing tables
    missing_tables = set(sqlite_tables.keys()) - set(postgres_tables.keys())
    extra_tables = set(postgres_tables.keys()) - set(sqlite_tables.keys())
    
    if missing_tables:
        print("❌ Missing tables in Postgres:")
        for table in sorted(missing_tables):
            print(f"   - {table}")
        print()
    
    if extra_tables:
        print("⚠️  Extra tables in Postgres (not in SQLite):")
        for table in sorted(extra_tables):
            print(f"   - {table}")
        print()
    
    # Verify each table
    errors = []
    warnings = []
    
    for table_name in sorted(sqlite_tables.keys()):
        if table_name not in postgres_tables:
            continue
        
        sqlite_fields = extract_fields(sqlite_tables[table_name])
        postgres_fields = extract_fields(postgres_tables[table_name])
        
        # Check for missing fields
        missing_fields = set(sqlite_fields.keys()) - set(postgres_fields.keys())
        extra_fields = set(postgres_fields.keys()) - set(sqlite_fields.keys())
        
        if missing_fields:
            errors.append(f"❌ {table_name}: Missing fields: {', '.join(sorted(missing_fields))}")
        
        if extra_fields:
            warnings.append(f"⚠️  {table_name}: Extra fields: {', '.join(sorted(extra_fields))}")
        
        # Verify field types
        for field_name in sqlite_fields:
            if field_name not in postgres_fields:
                continue
            
            sqlite_type = sqlite_fields[field_name]
            postgres_type = postgres_fields[field_name]
            
            if not verify_type_conversion(sqlite_type, postgres_type, field_name):
                errors.append(
                    f"❌ {table_name}.{field_name}: Type mismatch - "
                    f"SQLite: {sqlite_type}, Postgres: {postgres_type}"
                )
    
    # Check for JSONB functions
    if 'jsonb_extract_text_immutable' in postgres_schema:
        print("✅ JSONB immutable functions present")
    else:
        errors.append("❌ Missing JSONB immutable functions")
    
    # Check for custom indices
    if 'idx_user_memories_superseded' in postgres_schema:
        print("✅ Custom JSONB indices present")
    else:
        errors.append("❌ Missing custom JSONB indices")
    
    # Check that otel_* tables are NOT present
    otel_tables_found = [t for t in postgres_tables.keys() if t.startswith('otel_')]
    if otel_tables_found:
        errors.append(f"❌ Found otel_* tables that should have been excluded: {', '.join(otel_tables_found)}")
    else:
        print("✅ No otel_* tables found (correctly excluded)")
    
    print()
    
    # Print results
    if errors:
        print("=" * 80)
        print("ERRORS:")
        print("=" * 80)
        for error in errors:
            print(error)
        print()
    
    if warnings:
        print("=" * 80)
        print("WARNINGS:")
        print("=" * 80)
        for warning in warnings:
            print(warning)
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    
    if not errors and not warnings:
        print("✅ All checks passed! Schema is correctly generated.")
        return 0
    elif not errors:
        print(f"⚠️  {len(warnings)} warnings found, but no errors.")
        return 0
    else:
        print(f"❌ {len(errors)} errors found!")
        if warnings:
            print(f"⚠️  {len(warnings)} warnings found.")
        return 1


if __name__ == '__main__':
    exit(main())
