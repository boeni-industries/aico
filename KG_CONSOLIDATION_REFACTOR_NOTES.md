# KG Consolidation Refactoring Notes

## Status: DEFERRED - Complex Background Task

The `backend/scheduler/tasks/kg_consolidation.py` file contains extensive raw SQL for KG node deduplication and edge management. This is a **background consolidation task** that runs periodically to clean up duplicate nodes.

## Why Deferred

1. **Complexity**: 200+ lines of intricate SQL logic for:
   - Node deduplication detection
   - Historical node management
   - Edge reference updates with UNIQUE constraint handling
   - Orphaned edge cleanup
   - Batch processing with transaction management

2. **Low Priority**: This is a background maintenance task, not business logic
3. **Risk**: High risk of breaking complex deduplication logic during refactoring
4. **Effort**: Estimated 2-3 hours for proper refactoring

## Current SQL Operations (Lines 540-700+)

- `SELECT` queries to check node existence and historical versions
- `UPDATE` queries to mark nodes as historical
- `DELETE` queries for duplicate nodes and edges
- Complex edge reference updates with constraint violation handling
- Orphaned edge detection and cleanup

## Recommended Approach for Future Refactoring

1. **Create specialized repository methods**:
   - `kg_nodes.mark_as_historical(node_id)`
   - `kg_nodes.delete_with_edges(node_id)`
   - `kg_edges.update_node_references(old_id, new_id)`
   - `kg_edges.find_orphaned(user_id)`

2. **Use UoW for transaction management**:
   - Wrap entire deduplication process in single UoW transaction
   - Proper rollback on constraint violations

3. **Batch operations**:
   - Repository methods should support batch operations for performance

4. **Testing**:
   - Extensive testing required due to complexity
   - Test constraint violation handling
   - Test orphaned edge cleanup

## Temporary Acceptance

This file is **acceptable as-is** because:
- It's a background maintenance task, not user-facing business logic
- The SQL is well-documented and contained
- It doesn't violate the core architectural principle (business logic uses UoW)
- Refactoring can be done incrementally when time permits

## Alternative: Consider PostgreSQL Stored Procedure

Given the complexity, this logic might be better suited as a PostgreSQL stored procedure that can be called via UoW, maintaining transactional integrity while keeping the complex SQL in the database layer.
