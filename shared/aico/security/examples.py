"""
Usage examples for AICO's transparent file encryption.

This module demonstrates various use cases for the EncryptedFile wrapper class.
"""

import json
import pickle
from pathlib import Path

from .encrypted_file import EncryptedFile, open_encrypted
from .key_manager import AICOKeyManager


def example_config_encryption():
    """Example: Encrypting sensitive configuration files."""
    key_manager = AICOKeyManager()
    
    # Sensitive configuration data
    config_data = {
        "database_password": "super_secret_password",
        "api_keys": {
            "openai": "sk-1234567890abcdef",
            "anthropic": "ant-1234567890abcdef"
        },
        "encryption_settings": {
            "master_key_salt": "random_salt_value"
        }
    }
    
    # Write encrypted configuration
    config_file = "sensitive_config.enc"
    with EncryptedFile(config_file, "w", key_manager=key_manager, purpose="config") as f:
        json.dump(config_data, f, indent=2)
    
    print(f"Encrypted configuration saved to {config_file}")
    
    # Read encrypted configuration
    with EncryptedFile(config_file, "r", key_manager=key_manager, purpose="config") as f:
        loaded_config = json.load(f)
    
    print("Successfully loaded encrypted configuration")
    return loaded_config


def example_log_encryption():
    """Example: Encrypting log files containing sensitive data."""
    key_manager = AICOKeyManager()
    log_file = "user_activity.log.enc"
    
    # Simulate logging user activities
    activities = [
        "2024-01-15 10:30:00 - User john.doe@example.com logged in",
        "2024-01-15 10:31:15 - User accessed sensitive document: /docs/financial_report.pdf",
        "2024-01-15 10:35:22 - User performed search: 'salary information'",
        "2024-01-15 10:40:10 - User john.doe@example.com logged out"
    ]
    
    # Write encrypted log entries
    with EncryptedFile(log_file, "w", key_manager=key_manager, purpose="logs") as f:
        for activity in activities:
            f.write(activity + "\n")
    
    print(f"Encrypted log entries saved to {log_file}")
    
    # Append new log entry
    with EncryptedFile(log_file, "a", key_manager=key_manager, purpose="logs") as f:
        f.write("2024-01-15 11:00:00 - System backup completed\n")
    
    # Read encrypted log
    with EncryptedFile(log_file, "r", key_manager=key_manager, purpose="logs") as f:
        print("Encrypted log contents:")
        for line in f:
            print(f"  {line.strip()}")


def example_binary_data_encryption():
    """Example: Encrypting binary data (e.g., ChromaDB files)."""
    key_manager = AICOKeyManager()
    
    # Simulate binary data (could be ChromaDB, pickled objects, etc.)
    binary_data = {
        "vectors": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        "metadata": {"model": "text-embedding-ada-002", "dimension": 3},
        "documents": ["Hello world", "Goodbye world"]
    }
    
    # Serialize and encrypt binary data
    binary_file = "vector_data.enc"
    with EncryptedFile(binary_file, "wb", key_manager=key_manager, purpose="chroma") as f:
        pickle.dump(binary_data, f)
    
    print(f"Encrypted binary data saved to {binary_file}")
    
    # Read and deserialize encrypted binary data
    with EncryptedFile(binary_file, "rb", key_manager=key_manager, purpose="chroma") as f:
        loaded_data = pickle.load(f)
    
    print("Successfully loaded encrypted binary data")
    print(f"Vectors: {loaded_data['vectors']}")
    print(f"Metadata: {loaded_data['metadata']}")
    return loaded_data


def example_streaming_large_file():
    """Example: Streaming encryption for large files."""
    key_manager = AICOKeyManager()
    
    # Simulate processing a large file in chunks
    large_file = "large_dataset.enc"
    chunk_size = 8192  # 8KB chunks
    
    # Write large file in chunks
    with EncryptedFile(large_file, "wb", key_manager=key_manager, purpose="dataset", 
                       chunk_size=chunk_size) as f:
        # Simulate writing 1MB of data in chunks
        for i in range(128):  # 128 * 8KB = 1MB
            chunk_data = f"Chunk {i:03d}: " + "x" * (chunk_size - 20) + "\n"
            f.write(chunk_data.encode())
    
    print(f"Large encrypted file created: {large_file}")
    
    # Read large file in chunks
    with EncryptedFile(large_file, "rb", key_manager=key_manager, purpose="dataset") as f:
        chunk_count = 0
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            chunk_count += 1
            # Process chunk (in real scenario)
            if chunk_count <= 3:  # Show first 3 chunks
                print(f"Read chunk {chunk_count}: {len(chunk)} bytes")
    
    print(f"Processed {chunk_count} chunks from encrypted file")


def example_plugin_data_encryption():
    """Example: Plugin-specific encrypted data storage."""
    key_manager = AICOKeyManager()
    
    class ExamplePlugin:
        def __init__(self, plugin_name):
            self.plugin_name = plugin_name
            self.key_manager = key_manager
        
        def save_plugin_data(self, data):
            """Save plugin-specific encrypted data."""
            purpose = f"plugin_{self.plugin_name}"
            data_file = f"{self.plugin_name}_data.enc"
            
            with EncryptedFile(data_file, "w", key_manager=self.key_manager, purpose=purpose) as f:
                json.dump(data, f, indent=2)
            
            print(f"Plugin {self.plugin_name} data saved to {data_file}")
        
        def load_plugin_data(self):
            """Load plugin-specific encrypted data."""
            purpose = f"plugin_{self.plugin_name}"
            data_file = f"{self.plugin_name}_data.enc"
            
            try:
                with EncryptedFile(data_file, "r", key_manager=self.key_manager, purpose=purpose) as f:
                    data = json.load(f)
                print(f"Plugin {self.plugin_name} data loaded successfully")
                return data
            except FileNotFoundError:
                print(f"No data file found for plugin {self.plugin_name}")
                return {}
    
    # Example usage
    plugin = ExamplePlugin("weather_forecast")
    
    # Save plugin data
    plugin_data = {
        "api_endpoint": "https://api.weather.com/v1/forecast",
        "cache_duration": 3600,
        "default_location": "San Francisco, CA",
        "user_preferences": {
            "units": "metric",
            "show_humidity": True
        }
    }
    
    plugin.save_plugin_data(plugin_data)
    loaded_data = plugin.load_plugin_data()
    
    return loaded_data


def example_migration_from_plaintext():
    """Example: Migrating existing plaintext files to encrypted format."""
    key_manager = AICOKeyManager()
    
    # Create a sample plaintext file
    plaintext_file = "sample_config.txt"
    with open(plaintext_file, "w") as f:
        f.write("database_host=localhost\n")
        f.write("database_user=admin\n")
        f.write("database_password=secret123\n")
        f.write("debug_mode=true\n")
    
    print(f"Created plaintext file: {plaintext_file}")
    
    # Migrate to encrypted format
    encrypted_file = "sample_config.enc"
    
    def migrate_file_to_encrypted(source_path, target_path, purpose):
        """Migrate a plaintext file to encrypted format."""
        with open(source_path, "r") as src:
            with EncryptedFile(target_path, "w", key_manager=key_manager, purpose=purpose) as dst:
                # Copy content
                content = src.read()
                dst.write(content)
        
        print(f"Migrated {source_path} -> {target_path}")
        
        # Optionally remove plaintext file
        Path(source_path).unlink()
        print(f"Removed plaintext file: {source_path}")
    
    migrate_file_to_encrypted(plaintext_file, encrypted_file, "config")
    
    # Verify migration
    with EncryptedFile(encrypted_file, "r", key_manager=key_manager, purpose="config") as f:
        migrated_content = f.read()
    
    print("Migration successful. Encrypted content:")
    print(migrated_content)


def example_batch_directory_encryption():
    """Example: Batch encryption of multiple files in a directory."""
    key_manager = AICOKeyManager()
    
    # Create sample directory with files
    sample_dir = Path("sample_data")
    sample_dir.mkdir(exist_ok=True)
    
    # Create sample files
    files_to_create = {
        "user_profiles.json": {"users": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]},
        "settings.json": {"theme": "dark", "notifications": True},
        "cache.json": {"last_update": "2024-01-15", "entries": 150}
    }
    
    for filename, content in files_to_create.items():
        with open(sample_dir / filename, "w") as f:
            json.dump(content, f, indent=2)
    
    print(f"Created sample files in {sample_dir}")
    
    # Batch encrypt directory
    encrypted_dir = Path("encrypted_data")
    encrypted_dir.mkdir(exist_ok=True)
    
    def encrypt_directory(source_dir, target_dir, purpose_prefix):
        """Encrypt all files in a directory."""
        for file_path in source_dir.glob("*.json"):
            # Create purpose based on filename
            purpose = f"{purpose_prefix}_{file_path.stem}"
            encrypted_path = target_dir / f"{file_path.name}.enc"
            
            # Encrypt file
            with open(file_path, "r") as src:
                with EncryptedFile(encrypted_path, "w", key_manager=key_manager, purpose=purpose) as dst:
                    content = src.read()
                    dst.write(content)
            
            print(f"Encrypted: {file_path} -> {encrypted_path}")
    
    encrypt_directory(sample_dir, encrypted_dir, "batch")
    
    # Verify batch encryption
    print("\nVerifying encrypted files:")
    for encrypted_file in encrypted_dir.glob("*.enc"):
        purpose = f"batch_{encrypted_file.stem.replace('.json', '')}"
        
        with EncryptedFile(encrypted_file, "r", key_manager=key_manager, purpose=purpose) as f:
            content = f.read()
            data = json.loads(content)
            print(f"  {encrypted_file.name}: {len(content)} chars, {len(data)} keys")


def example_encryption_verification():
    """Example: Verifying file encryption and getting encryption info."""
    key_manager = AICOKeyManager()
    
    # Create test files with different purposes
    test_files = [
        ("config.enc", "config", {"setting1": "value1", "setting2": "value2"}),
        ("logs.enc", "logs", "2024-01-15 10:00:00 - Application started\n"),
        ("data.enc", "data", b"\x00\x01\x02\x03\x04\x05")
    ]
    
    for filename, purpose, content in test_files:
        if isinstance(content, bytes):
            mode = "wb"
        else:
            mode = "w"
            if isinstance(content, dict):
                content = json.dumps(content, indent=2)
        
        with EncryptedFile(filename, mode, key_manager=key_manager, purpose=purpose) as f:
            f.write(content)
        
        print(f"Created encrypted file: {filename}")
    
    # Verify encryption for each file
    print("\nEncryption verification:")
    for filename, purpose, _ in test_files:
        encrypted_file = EncryptedFile(filename, "r", key_manager=key_manager, purpose=purpose)
        
        # Verify encryption
        is_encrypted = encrypted_file.verify_encryption()
        print(f"  {filename}: Encrypted = {is_encrypted}")
        
        # Get encryption info
        info = encrypted_file.get_encryption_info()
        print(f"    Algorithm: {info.get('algorithm', 'Unknown')}")
        print(f"    Key size: {info.get('key_size', 0)} bits")
        print(f"    File size: {info.get('file_size', 0)} bytes")
        print(f"    Payload size: {info.get('payload_size', 0)} bytes")
        print(f"    Overhead: {info.get('overhead_size', 0)} bytes")
        print()


if __name__ == "__main__":
    """Run all examples."""
    print("=== AICO Encrypted File Examples ===\n")
    
    try:
        print("1. Configuration File Encryption:")
        example_config_encryption()
        print()
        
        print("2. Log File Encryption:")
        example_log_encryption()
        print()
        
        print("3. Binary Data Encryption:")
        example_binary_data_encryption()
        print()
        
        print("4. Large File Streaming:")
        example_streaming_large_file()
        print()
        
        print("5. Plugin Data Encryption:")
        example_plugin_data_encryption()
        print()
        
        print("6. Migration from Plaintext:")
        example_migration_from_plaintext()
        print()
        
        print("7. Batch Directory Encryption:")
        example_batch_directory_encryption()
        print()
        
        print("8. Encryption Verification:")
        example_encryption_verification()
        
        print("=== All examples completed successfully! ===")
        
    except Exception as e:
        print(f"Example failed with error: {e}")
        raise
