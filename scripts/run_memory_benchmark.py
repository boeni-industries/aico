#!/usr/bin/env python3
"""
AICO Memory Benchmark Suite - Main Entry Point

Performance benchmarking CLI for AICO's V2 memory system that measures
fact extraction performance, storage efficiency, and memory improvements over time.

Usage:
    python run_memory_benchmark.py [command] [options]
    
Examples:
    # List available benchmark scenarios
    python run_memory_benchmark.py list --verbose
    
    # Run comprehensive memory benchmark
    python run_memory_benchmark.py run --scenario comprehensive_memory_test
    
    # Continuous benchmarking for performance tracking
    python run_memory_benchmark.py continuous --iterations 10
    
    # Show version information
    python run_memory_benchmark.py version
"""

import sys
from pathlib import Path

# Add the scripts directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the beautiful CLI from memory_benchmark
from memory_benchmark.cli import app

if __name__ == "__main__":
    """Main entry point - run the memory benchmark CLI"""
    app()
