#!/usr/bin/env python3
"""
Generate properly ordered PostgreSQL schema from V1_SCHEMA.

Handles circular dependencies by:
1. Creating all tables without foreign key constraints
2. Adding all foreign key constraints afterward
"""

import re
from schema import V1_SCHEMA


def extract_table_name(stmt: str) -> str:
    """Extract table name from CREATE TABLE statement."""
    # Handle both quoted and unquoted table names
    match = re.search(r'CREATE TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+["]?(\w+)["]?\s*\(', stmt, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def remove_foreign_keys(stmt: str) -> tuple[str, list[str]]:
    """
    Remove FOREIGN KEY constraints from CREATE TABLE statement.
    Returns (modified_statement, list_of_foreign_key_constraints).
    """
    lines = stmt.split('\n')
    table_lines = []
    fk_constraints = []
    table_name = extract_table_name(stmt)
    
    for line in lines:
        stripped = line.strip()
        if 'FOREIGN KEY' in line:
            # Extract the foreign key constraint
            fk_constraints.append((table_name, stripped.rstrip(',')))
        elif stripped and not (stripped.startswith('--') and 'foreign key' in stripped.lower()):
            # Skip empty lines and FK-related comments
            table_lines.append(line)
    
    # Find the last line that's not a closing paren and remove trailing comma
    for i in range(len(table_lines) - 1, -1, -1):
        stripped = table_lines[i].strip()
        if stripped and not stripped.startswith(')'):
            # Remove trailing comma from the last field definition
            # Handle comma before comment: "field TEXT,  -- comment" -> "field TEXT  -- comment"
            table_lines[i] = re.sub(r',(\s+--.*?)$', r'\1', table_lines[i])
            # Handle comma at end: "field TEXT," -> "field TEXT"
            table_lines[i] = re.sub(r',\s*$', '', table_lines[i])
            break
    
    modified_stmt = '\n'.join(table_lines)
    
    return modified_stmt, fk_constraints


def generate_alter_table_statements(fk_constraints: list[tuple[str, str]]) -> list[str]:
    """Generate ALTER TABLE statements to add foreign key constraints."""
    alter_statements = []
    
    for table_name, fk_line in fk_constraints:
        # Parse the foreign key constraint
        # Example: FOREIGN KEY (lesson_id) REFERENCES agency_lessons(lesson_id) ON DELETE CASCADE
        match = re.search(
            r'FOREIGN KEY\s*\(([^)]+)\)\s*REFERENCES\s+["]?(\w+)["]?\s*\(([^)]+)\)(.*)$',
            fk_line,
            re.IGNORECASE
        )
        
        if match:
            column = match.group(1).strip()
            ref_table = match.group(2).strip()
            ref_column = match.group(3).strip()
            on_clause = match.group(4).strip()
            
            constraint_name = f"fk_{table_name}_{column}_{ref_table}"
            
            alter_stmt = (
                f"ALTER TABLE {table_name} "
                f"ADD CONSTRAINT {constraint_name} "
                f"FOREIGN KEY ({column}) "
                f"REFERENCES {ref_table}({ref_column})"
            )
            
            if on_clause:
                alter_stmt += f" {on_clause}"
            
            alter_stmt += ";"
            alter_statements.append(alter_stmt)
    
    return alter_statements


def convert_to_postgres(stmt: str) -> str:
    """Convert SQLite-specific syntax to PostgreSQL."""
    # INTEGER PRIMARY KEY AUTOINCREMENT -> BIGSERIAL PRIMARY KEY
    stmt = re.sub(
        r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT',
        'BIGSERIAL PRIMARY KEY',
        stmt,
        flags=re.IGNORECASE
    )
    
    # REAL -> DOUBLE PRECISION
    stmt = re.sub(r'\bREAL\b', 'DOUBLE PRECISION', stmt, flags=re.IGNORECASE)
    
    # DATETIME -> TIMESTAMPTZ (must come before TIMESTAMP conversion)
    stmt = re.sub(
        r"DATETIME\s+DEFAULT\s+CURRENT_TIMESTAMP",
        "TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
        stmt,
        flags=re.IGNORECASE
    )
    stmt = re.sub(
        r"DATETIME\s+NOT\s+NULL",
        "TIMESTAMPTZ NOT NULL",
        stmt,
        flags=re.IGNORECASE
    )
    stmt = re.sub(r'\bDATETIME\b', 'TIMESTAMPTZ', stmt, flags=re.IGNORECASE)
    
    # TIMESTAMP -> TIMESTAMPTZ (only when used as a type, not as a field name)
    # Match: field_name TIMESTAMP [constraints]
    # Don't match: timestamp TEXT (where timestamp is the field name)
    stmt = re.sub(
        r"TIMESTAMP\s+DEFAULT\s+CURRENT_TIMESTAMP",
        "TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
        stmt,
        flags=re.IGNORECASE
    )
    stmt = re.sub(
        r"TIMESTAMP\s+NOT\s+NULL",
        "TIMESTAMPTZ NOT NULL",
        stmt,
        flags=re.IGNORECASE
    )
    # Only convert TIMESTAMP when it's followed by a comma, closing paren, or constraint keyword
    # This avoids converting field names like "timestamp"
    stmt = re.sub(
        r'\bTIMESTAMP\b(\s*[,)]|\s+(?:DEFAULT|CHECK|UNIQUE|REFERENCES))',
        r'TIMESTAMPTZ\1',
        stmt,
        flags=re.IGNORECASE
    )
    
    # Convert SQLite TIMESTAMPTZ('now', 'utc') to PostgreSQL CURRENT_TIMESTAMP
    stmt = re.sub(
        r"TIMESTAMPTZ\s*\(\s*['\"]now['\"]\s*,\s*['\"]utc['\"]\s*\)",
        "CURRENT_TIMESTAMP",
        stmt,
        flags=re.IGNORECASE
    )
    
    # Add IF NOT EXISTS to CREATE TABLE
    stmt = re.sub(
        r'CREATE TABLE\s+',
        'CREATE TABLE IF NOT EXISTS ',
        stmt,
        flags=re.IGNORECASE
    )
    
    # Add IF NOT EXISTS to CREATE INDEX
    stmt = re.sub(
        r'CREATE INDEX\s+',
        'CREATE INDEX IF NOT EXISTS ',
        stmt,
        flags=re.IGNORECASE
    )
    
    # Fix BOOLEAN defaults (SQLite uses 0/1, PostgreSQL uses FALSE/TRUE)
    stmt = re.sub(
        r'BOOLEAN\s+DEFAULT\s+0',
        'BOOLEAN DEFAULT FALSE',
        stmt,
        flags=re.IGNORECASE
    )
    stmt = re.sub(
        r'BOOLEAN\s+DEFAULT\s+1',
        'BOOLEAN DEFAULT TRUE',
        stmt,
        flags=re.IGNORECASE
    )
    
    # Fix INTEGER defaults for BOOLEAN columns (only for specific boolean-like columns)
    # active, archived, enabled, etc. with DEFAULT 0/1
    stmt = re.sub(
        r'(active|archived|enabled|disabled|deleted|is_\w+)\s+INTEGER\s+DEFAULT\s+0',
        r'\1 BOOLEAN DEFAULT FALSE',
        stmt,
        flags=re.IGNORECASE
    )
    stmt = re.sub(
        r'(active|archived|enabled|disabled|deleted|is_\w+)\s+INTEGER\s+DEFAULT\s+1',
        r'\1 BOOLEAN DEFAULT TRUE',
        stmt,
        flags=re.IGNORECASE
    )
    
    # Fix WHERE clauses in indexes for boolean comparisons
    # WHERE active = 1 -> WHERE active IS TRUE
    # WHERE active = 0 -> WHERE active IS FALSE
    stmt = re.sub(
        r'WHERE\s+(\w+)\s*=\s*1',
        r'WHERE \1 IS TRUE',
        stmt,
        flags=re.IGNORECASE
    )
    stmt = re.sub(
        r'WHERE\s+(\w+)\s*=\s*0',
        r'WHERE \1 IS FALSE',
        stmt,
        flags=re.IGNORECASE
    )
    
    # Skip indexes with json_extract - they need to be rewritten for PostgreSQL
    # These indexes are problematic and should be handled separately
    if 'CREATE INDEX' in stmt.upper() and 'json_extract' in stmt.lower():
        # Return empty string to skip this index
        return ''
    
    # Convert BLOB to BYTEA
    stmt = re.sub(r'\bBLOB\b', 'BYTEA', stmt, flags=re.IGNORECASE)
    
    # Convert JSON type to JSONB
    # Match: whitespace + JSON + (whitespace or comma or closing paren)
    # This catches: "field JSON,", "field JSON)", "field JSON NOT NULL", etc.
    stmt = re.sub(r'(\s+)JSON(\s|,|\))', r'\1JSONB\2', stmt, flags=re.IGNORECASE)
    
    # Convert TEXT columns that store JSON to JSONB for better performance
    # Look for columns with _json suffix or json in name
    stmt = re.sub(
        r'(\w*json\w*)\s+TEXT',
        r'\1 JSONB',
        stmt,
        flags=re.IGNORECASE
    )
    
    return stmt


def main():
    """Generate PostgreSQL schema file."""
    
    output_lines = [
        "-- AICO Postgres Core Schema",
        "--",
        "-- Auto-generated from shared/aico/data/schemas/schema.py",
        "-- DO NOT EDIT MANUALLY - regenerate using generate_postgres_schema.py",
        "--",
        "-- Database: aico",
        "-- Schema:   aico_core",
        "",
        "CREATE SCHEMA IF NOT EXISTS aico_core;",
        "SET search_path TO aico_core, public;",
        "",
        "-- Tables created without foreign key constraints to avoid dependency ordering issues",
        ""
    ]
    
    all_fk_constraints = []
    
    # Process each statement
    for stmt in V1_SCHEMA:
        stmt = stmt.strip()
        
        if not stmt:
            continue
        
        # Skip otel_* tables - they're OpenTelemetry metrics that go to InfluxDB
        if 'CREATE TABLE' in stmt.upper():
            table_name = extract_table_name(stmt)
            if table_name and table_name.startswith('otel_'):
                continue
        
        # Skip indices on otel_* tables
        if 'CREATE INDEX' in stmt.upper() and 'otel_' in stmt:
            continue
        
        # Skip indices with json_extract - they're replaced by PostgreSQL-compatible versions
        if 'CREATE INDEX' in stmt.upper() and 'json_extract' in stmt.lower():
            continue
        
        if 'CREATE TABLE' in stmt.upper():
            # Convert to PostgreSQL syntax (type conversions, etc.)
            stmt = convert_to_postgres(stmt)
            # Remove foreign keys and collect them
            modified_stmt, fk_constraints = remove_foreign_keys(stmt)
            all_fk_constraints.extend(fk_constraints)
            # Ensure statement ends with semicolon
            if not modified_stmt.rstrip().endswith(';'):
                modified_stmt = modified_stmt.rstrip() + ';'
            output_lines.append(modified_stmt)
            output_lines.append("")
        elif 'CREATE INDEX' in stmt.upper():
            # Add IF NOT EXISTS to CREATE INDEX (but don't apply type conversions)
            stmt = re.sub(
                r'CREATE INDEX\s+',
                'CREATE INDEX IF NOT EXISTS ',
                stmt,
                flags=re.IGNORECASE
            )
            # Fix partial index predicates for BOOLEAN columns
            # Convert WHERE field = 1 to WHERE field = TRUE
            # Convert WHERE field = 0 to WHERE field = FALSE
            stmt = re.sub(
                r'WHERE\s+(\w+)\s*=\s*1\b',
                r'WHERE \1 = TRUE',
                stmt,
                flags=re.IGNORECASE
            )
            stmt = re.sub(
                r'WHERE\s+(\w+)\s*=\s*0\b',
                r'WHERE \1 = FALSE',
                stmt,
                flags=re.IGNORECASE
            )
            # Ensure statement ends with semicolon
            if not stmt.rstrip().endswith(';'):
                stmt = stmt.rstrip() + ';'
            output_lines.append(stmt)
            output_lines.append("")
        else:
            # Other statement - add as-is
            # Ensure statement ends with semicolon
            if not stmt.rstrip().endswith(';'):
                stmt = stmt.rstrip() + ';'
            output_lines.append(stmt)
            output_lines.append("")
    
    # Add foreign key constraints at the end
    output_lines.append("")
    output_lines.append("-- Foreign key constraints added after all tables are created")
    output_lines.append("")
    
    alter_statements = generate_alter_table_statements(all_fk_constraints)
    for alter_stmt in alter_statements:
        output_lines.append(alter_stmt)
    
    # Add PostgreSQL-specific JSONB functions and indexes
    output_lines.append("-- Immutable wrapper functions for JSONB extraction (required for functional indexes)")
    output_lines.append("CREATE OR REPLACE FUNCTION jsonb_extract_text_immutable(data TEXT, path TEXT)")
    output_lines.append("RETURNS TEXT AS $$")
    output_lines.append("BEGIN")
    output_lines.append("  RETURN (data::jsonb)->>path;")
    output_lines.append("END;")
    output_lines.append("$$ LANGUAGE plpgsql IMMUTABLE;")
    output_lines.append("")
    output_lines.append("CREATE OR REPLACE FUNCTION jsonb_extract_timestamptz_immutable(data TEXT, path TEXT)")
    output_lines.append("RETURNS TIMESTAMPTZ AS $$")
    output_lines.append("BEGIN")
    output_lines.append("  RETURN ((data::jsonb)->>path)::timestamptz;")
    output_lines.append("END;")
    output_lines.append("$$ LANGUAGE plpgsql IMMUTABLE;")
    output_lines.append("")
    output_lines.append("CREATE OR REPLACE FUNCTION jsonb_extract_double_immutable(data TEXT, path TEXT)")
    output_lines.append("RETURNS DOUBLE PRECISION AS $$")
    output_lines.append("BEGIN")
    output_lines.append("  RETURN ((data::jsonb)->>path)::double precision;")
    output_lines.append("END;")
    output_lines.append("$$ LANGUAGE plpgsql IMMUTABLE;")
    output_lines.append("")
    output_lines.append("-- PostgreSQL-compatible indexes for ams_user_memories JSON fields")
    output_lines.append("-- These replace the 2 skipped json_extract() indexes from SQLite")
    output_lines.append("")
    output_lines.append("CREATE INDEX IF NOT EXISTS idx_user_memories_superseded ")
    output_lines.append("  ON ams_user_memories(jsonb_extract_text_immutable(temporal_metadata, 'superseded_by'))")
    output_lines.append("  WHERE temporal_metadata IS NOT NULL;")
    output_lines.append("")
    output_lines.append("CREATE INDEX IF NOT EXISTS idx_user_memories_temporal ")
    output_lines.append("  ON ams_user_memories(")
    output_lines.append("    jsonb_extract_timestamptz_immutable(temporal_metadata, 'last_accessed'),")
    output_lines.append("    jsonb_extract_double_immutable(temporal_metadata, 'confidence')")
    output_lines.append("  )")
    output_lines.append("  WHERE temporal_metadata IS NOT NULL;")
    output_lines.append("")
    
    # Write to file
    output_file = "../postgres/schema.sql"
    with open(output_file, 'w') as f:
        f.write('\n'.join(output_lines))
    
    print(f"Generated {output_file}")
    print(f"Total tables: {len([s for s in V1_SCHEMA if 'CREATE TABLE' in s])}")
    print(f"Total foreign keys: {len(all_fk_constraints)}")


if __name__ == "__main__":
    main()
