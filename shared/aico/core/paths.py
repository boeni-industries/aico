"""
AICO Cross-Platform Path Resolution

Zero-maintenance path handling for Windows, Linux, and macOS.
Uses platformdirs for OS-appropriate data directories.
"""

from pathlib import Path
import os
import platform
from typing import Optional


class AICOPaths:
    """Zero-maintenance cross-platform path resolution for AICO."""
    
    # Application metadata
    APP_NAME = "aico"
    APP_AUTHOR = "boeni-industries"
    
    @classmethod
    def get_data_directory(cls) -> Path:
        """
        Get AICO data directory - works everywhere, zero config.
        
        Platform-specific locations:
        - Windows: %APPDATA%/aico (e.g., C:/Users/username/AppData/Roaming/aico)
        - macOS: ~/Library/Application Support/aico
        - Linux: ~/.local/share/aico (XDG Base Directory)
        
        Returns:
            Path: Platform-appropriate data directory
        """
        # Check for explicit override first
        if override := os.getenv("AICO_DATA_DIR"):
            return Path(override)
        
        # Lazy import platformdirs only when needed
        import platformdirs
        return Path(platformdirs.user_data_dir(cls.APP_NAME, cls.APP_AUTHOR))
    
    @classmethod
    def get_config_directory(cls) -> Path:
        """
        Get AICO configuration directory.
        
        Platform-specific locations:
        - Windows: %APPDATA%/aico/config
        - macOS: ~/Library/Application Support/aico/config
        - Linux: ~/.local/share/aico/config
        
        Returns:
            Path: Platform-appropriate config directory
        """
        # Check for explicit override first
        if override := os.getenv("AICO_CONFIG_DIR"):
            return Path(override)
        
        # Use unified approach - all subdirectories under main data directory
        return cls.get_data_directory() / "config"
    
    @classmethod
    def get_cache_directory(cls) -> Path:
        """
        Get AICO cache directory.
        
        Platform-specific locations:
        - Windows: %APPDATA%/aico/cache
        - macOS: ~/Library/Application Support/aico/cache
        - Linux: ~/.local/share/aico/cache
        
        Returns:
            Path: Platform-appropriate cache directory
        """
        # Check for explicit override first
        if override := os.getenv("AICO_CACHE_DIR"):
            return Path(override)
        
        # Use unified approach - all subdirectories under main data directory
        return cls.get_data_directory() / "cache"
    
    @classmethod
    def get_logs_directory(cls) -> Path:
        """
        Get AICO logs directory.
        
        Platform-specific locations:
        - Windows: %APPDATA%/aico/logs
        - macOS: ~/Library/Application Support/aico/logs
        - Linux: ~/.local/share/aico/logs
        
        Returns:
            Path: Platform-appropriate logs directory
        """
        # Check for explicit override first
        if override := os.getenv("AICO_LOGS_DIR"):
            return Path(override)
        
        # Use unified approach - all subdirectories under main data directory
        return cls.get_data_directory() / "logs"
    
    @classmethod
    def get_directory_mode_from_config(cls) -> str:
        """
        Get directory_mode from configuration, with fallback to 'auto'.
        
        Returns:
            str: Directory mode ('auto', 'current', or explicit path)
        """
        try:
            # Try to import and read from configuration
            from aico.core.config import ConfigurationManager
            config_manager = ConfigurationManager()
            config_manager.initialize()
            return config_manager.get("system.paths.directory_mode", "auto")
        except Exception:
            # Fallback to 'auto' if configuration is not available
            return "auto"
    
    @classmethod
    def get_data_subdirectory_from_config(cls) -> str:
        """
        Get data subdirectory name from configuration, with fallback to 'data'.
        
        Returns:
            str: Data subdirectory name
        """
        try:
            from aico.core.config import ConfigurationManager
            config_manager = ConfigurationManager()
            config_manager.initialize()
            return config_manager.get("system.paths.data_subdirectory", "data")
        except Exception:
            return "data"
    
    @classmethod
    def resolve_database_path(cls, config_path: str, directory_mode: str = "auto") -> Path:
        """
        Resolve database path based on simple config.
        
        Args:
            config_path: Database filename (e.g., "aico.db")
            directory_mode: "auto", "current", or explicit directory path
        
        Returns:
            Path: Resolved absolute path to database file
        """
        if directory_mode == "current":
            # Development mode - use current working directory with "data" subdirectory
            data_dir = Path.cwd() / "data"
            data_dir.mkdir(parents=True, exist_ok=True)  # Auto-create
            return data_dir / config_path
        
        elif directory_mode == "auto":
            # Production mode - use OS-appropriate data directory with configurable subdirectory
            data_subdir = cls.get_data_subdirectory_from_config()
            data_dir = cls.get_data_directory() / data_subdir
            data_dir.mkdir(parents=True, exist_ok=True)  # Auto-create
            return data_dir / config_path
        
        else:
            # Explicit directory path provided
            explicit_dir = Path(directory_mode)
            explicit_dir.mkdir(parents=True, exist_ok=True)  # Auto-create
            return explicit_dir / config_path
    
    @classmethod
    def resolve_config_path(cls, config_path: str, directory_mode: str = "auto") -> Path:
        """
        Resolve configuration file path.
        
        Args:
            config_path: Config filename (e.g., "settings.yaml")
            directory_mode: "auto", "current", or explicit directory path
        
        Returns:
            Path: Resolved absolute path to config file
        """
        if directory_mode == "current":
            return Path.cwd() / config_path
        elif directory_mode == "auto":
            config_dir = cls.get_config_directory()
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir / config_path
        else:
            explicit_dir = Path(directory_mode)
            explicit_dir.mkdir(parents=True, exist_ok=True)
            return explicit_dir / config_path
    
    @classmethod
    def ensure_directory(cls, path: Path) -> Path:
        """
        Ensure directory exists, creating it if necessary.
        
        Args:
            path: Directory path to ensure
        
        Returns:
            Path: The ensured directory path
        """
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @classmethod
    def get_platform_info(cls) -> dict:
        """
        Get platform-specific path information for debugging.
        
        Returns:
            dict: Platform and path information
        """
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "data_directory": str(cls.get_data_directory()),
            "config_directory": str(cls.get_config_directory()),
            "cache_directory": str(cls.get_cache_directory()),
            "logs_directory": str(cls.get_logs_directory()),
            "environment_overrides": {
                "AICO_DATA_DIR": os.getenv("AICO_DATA_DIR"),
                "AICO_CONFIG_DIR": os.getenv("AICO_CONFIG_DIR"),
                "AICO_CACHE_DIR": os.getenv("AICO_CACHE_DIR"),
                "AICO_LOGS_DIR": os.getenv("AICO_LOGS_DIR"),
            }
        }


# Convenience functions for common operations
def get_default_database_path(filename: str = "aico.db") -> Path:
    """Get default database path in user data directory."""
    return AICOPaths.resolve_database_path(filename, "auto")


def get_development_database_path(filename: str = "aico.db") -> Path:
    """Get development database path in current directory."""
    return AICOPaths.resolve_database_path(filename, "current")


def get_custom_database_path(directory: str, filename: str = "aico.db") -> Path:
    """Get database path in custom directory."""
    return AICOPaths.resolve_database_path(filename, directory)
