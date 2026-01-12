"""
Backend Start Time Tracker

Shared module to track backend process start time without circular imports.
"""

import time

# Track backend start time (set when module is first imported)
start_time = time.time()
