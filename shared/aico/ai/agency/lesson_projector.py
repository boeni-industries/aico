"""Lesson projector module.

Legacy implementation removed.

The previous LessonMemoryProjector depended on a legacy db_connection API.
If you need projection into AMS/KG, implement a UoW/SQLAlchemy projector.
"""

raise ImportError(
    "Legacy LessonMemoryProjector has been removed. Implement a UoW/SQLAlchemy-based projector instead."
)
