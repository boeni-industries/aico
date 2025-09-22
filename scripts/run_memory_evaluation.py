#!/usr/bin/env python3
"""
AICO Memory Intelligence Evaluator - Main Entry Point

Award-winning visual CLI interface that leverages existing AICO modules
and provides stunning Typer/Rich output for memory system evaluation.

This integrates with AICO's existing CLI structure and provides beautiful
visual feedback for memory system testing.

Usage:
    python run_memory_evaluation.py [command] [options]
    
Examples:
    # List available scenarios
    python run_memory_evaluation.py list --verbose
    
    # Run comprehensive memory test
    python run_memory_evaluation.py run --scenario comprehensive_memory_test
    
    # Continuous evaluation for system improvement
    python run_memory_evaluation.py continuous --iterations 10
    
    # Show version information
    python run_memory_evaluation.py version
"""

import sys
from pathlib import Path

# Add the scripts directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the beautiful CLI from memory_eval
from memory_eval.cli import app

if __name__ == "__main__":
    """Main entry point - directly run the beautiful Typer CLI"""
    app()
