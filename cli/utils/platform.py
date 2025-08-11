"""
Platform-specific utilities for cross-platform CLI compatibility.

The KISS solution: Just fix Windows CMD encoding and let Rich handle everything else.
Zero maintenance - works everywhere with beautiful Unicode.
"""

import platform
import sys
import os
from rich.console import Console


def get_platform_chars():
    """
    Get platform-appropriate characters for CLI display.
    
    Only Windows CMD gets ASCII alternatives - Git Bash, PowerShell, and other terminals 
    can handle Unicode just fine. This prevents UnicodeEncodeError crashes specifically 
    in Windows CMD while preserving beautiful Unicode everywhere else.
    
    Returns:
        dict: Character mappings for current platform/terminal
    """
    # Only use ASCII fallbacks for actual Windows CMD
    # CMD doesn't set TERM environment variable, while Git Bash sets TERM=xterm
    if platform.system() == "Windows" and "TERM" not in os.environ:
        return {
            "sparkle": "*",
            "package": ">",
            "database": ">",
            "security": ">", 
            "config": ">",
            "check": "✓",
            "cross": "✗",
            "arrow": "->",
            "bullet": "*"
        }
    
    # Use beautiful Unicode for everything else (Git Bash, PowerShell, Mac, Linux)
    return {
        "sparkle": "✨",
        "package": "📦",
        "database": "🛢️",
        "security": "🔐",
        "config": "📝",
        "check": "✅",
        "cross": "❌", 
        "arrow": "→",
        "bullet": "•"
    }


def create_console() -> Console:
    """
    Create a Rich Console with automatic Windows CMD compatibility.
    
    KISS Solution: Fix Windows encoding once, then use Rich normally everywhere.
    This is truly zero-maintenance - no special handling needed anywhere else.
    
    Returns:
        Console: Standard Rich console that works beautifully everywhere
    """
    # Fix Windows CMD encoding issue once and for all
    if platform.system() == "Windows":
        # Set UTF-8 encoding for Windows CMD if not already set
        if "PYTHONIOENCODING" not in os.environ:
            os.environ["PYTHONIOENCODING"] = "utf-8"
        
        # Try to set console to UTF-8 mode (Windows 10+)
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Set console output code page to UTF-8
            kernel32.SetConsoleOutputCP(65001)
            # Set console input code page to UTF-8  
            kernel32.SetConsoleCP(65001)
        except:
            # If that fails, we'll rely on PYTHONIOENCODING
            pass
    
    # Now just use Rich normally - it will work beautifully everywhere
    return Console(
        color_system="auto",
        force_terminal=None,
        legacy_windows=False
    )
