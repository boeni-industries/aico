#!/usr/bin/env python3
"""Test schema v14 SQL syntax by attempting a dry-run parse."""

import sys
sys.path.insert(0, '/Users/mbo/Documents/dev/aico')

from aico.data.schemas.core import CORE_SCHEMA

print("=" * 60)
print("Testing Schema Version 14 SQL Syntax")
print("=" * 60)

schema_v14 = CORE_SCHEMA[14]

print(f"\n📋 Testing {len(schema_v14.sql_statements)} SQL statements:\n")

# Try to parse each SQL statement
import sqlite3

# Create in-memory database for syntax testing
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# First create a minimal users table (required for foreign keys)
cursor.execute("""
    CREATE TABLE users (
        uuid TEXT PRIMARY KEY
    )
""")

errors = []
for i, stmt in enumerate(schema_v14.sql_statements, 1):
    try:
        # Try to execute statement
        cursor.execute(stmt)
        print(f"✅ Statement {i}: OK")
    except sqlite3.Error as e:
        errors.append((i, stmt[:100], str(e)))
        print(f"❌ Statement {i}: {e}")

conn.close()

print("\n" + "=" * 60)
if errors:
    print(f"❌ Found {len(errors)} SQL errors:")
    for i, stmt, error in errors:
        print(f"\n  Statement {i}:")
        print(f"  SQL: {stmt}...")
        print(f"  Error: {error}")
else:
    print("✅ All SQL statements are syntactically valid")
print("=" * 60)
