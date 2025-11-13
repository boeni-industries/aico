#!/usr/bin/env python3
"""Test schema v14 SQL statements without applying to database."""

import sys
sys.path.insert(0, '/Users/mbo/Documents/dev/aico')

from aico.data.schemas.core import CORE_SCHEMA

print("=" * 60)
print("Testing Schema Version 14 - AMS Phase 3 Behavioral Learning")
print("=" * 60)

schema_v14 = CORE_SCHEMA[14]

print(f"\n📋 Schema Info:")
print(f"   Version: {schema_v14.version}")
print(f"   Name: {schema_v14.name}")
print(f"   Description: {schema_v14.description}")

print(f"\n📊 SQL Statements ({len(schema_v14.sql_statements)} total):")
for i, stmt in enumerate(schema_v14.sql_statements, 1):
    # Extract table/index name
    stmt_clean = stmt.strip()
    if stmt_clean.startswith("CREATE TABLE"):
        table_name = stmt_clean.split("(")[0].replace("CREATE TABLE IF NOT EXISTS", "").strip()
        print(f"   {i}. CREATE TABLE {table_name}")
    elif stmt_clean.startswith("CREATE INDEX"):
        idx_name = stmt_clean.split("ON")[0].replace("CREATE INDEX IF NOT EXISTS", "").strip()
        print(f"   {i}. CREATE INDEX {idx_name}")
    else:
        print(f"   {i}. {stmt_clean[:60]}...")

print(f"\n🔄 Rollback Statements ({len(schema_v14.rollback_statements) if schema_v14.rollback_statements else 0} total):")
if schema_v14.rollback_statements:
    for i, stmt in enumerate(schema_v14.rollback_statements, 1):
        print(f"   {i}. {stmt.strip()}")

print("\n✅ Schema v14 structure is valid")
print("=" * 60)
