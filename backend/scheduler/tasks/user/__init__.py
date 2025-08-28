"""
User-Defined Tasks Directory

This directory contains user-defined task implementations.
Each task should be in its own Python file with a class that inherits from BaseTask.

Example structure:
- my_custom_task.py - Contains MyCustomTask class
- data_processing.py - Contains DataProcessingTask class
- backup_task.py - Contains BackupTask class

Tasks are automatically discovered by the TaskRegistry based on database entries
with task_id starting with 'user.'.
"""
