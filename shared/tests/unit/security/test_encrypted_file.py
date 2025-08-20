"""
Unit tests for EncryptedFile functionality.
"""

import os
import tempfile
import pytest
from pathlib import Path

from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager
from aico.security.encrypted_file import EncryptedFile, open_encrypted
from aico.security.exceptions import (
    EncryptionError,
    DecryptionError,
    InvalidKeyError,
    CorruptedFileError,
    InvalidFileFormatError
)


class TestEncryptedFile:
    """Test cases for EncryptedFile class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def key_manager(self):
        """Create test key manager."""
        # Use test configuration
        config = ConfigurationManager()
        # In a real app, config would be initialized properly
        # For this test, we ensure the required value is present
        if not config.get("security.keyring_service_name"):
            config.set("security.keyring_service_name", "AICO_Test")
        
        km = AICOKeyManager(config)
        
        # Clean up any previous test keys to ensure a clean slate.
        if km.has_stored_key():
            km.clear_stored_key()

        # Set up test master key
        test_password = "test_password_123"
        km.setup_master_password(test_password)
        
        yield km

        # Teardown: clean up the key from the keyring after the test
        if km.has_stored_key():
            km.clear_stored_key()
    
    def test_text_write_read(self, temp_dir, key_manager):
        """Test basic text file write and read operations."""
        test_file = temp_dir / "test.enc"
        test_data = "Hello, encrypted world!\nThis is a test file."
        
        # Write encrypted file
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="test") as f:
            f.write(test_data)
        
        # Verify file exists and is encrypted
        assert test_file.exists()
        assert test_file.stat().st_size > len(test_data)  # Overhead from encryption
        
        # Read encrypted file
        with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="test") as f:
            read_data = f.read()
        
        assert read_data == test_data
    
    def test_binary_write_read(self, temp_dir, key_manager):
        """Test binary file write and read operations."""
        test_file = temp_dir / "binary.enc"
        test_data = b"\x00\x01\x02\x03\xFF\xFE\xFD\xFC"
        
        # Write encrypted binary file
        with EncryptedFile(test_file, "wb", key_manager=key_manager, purpose="binary") as f:
            f.write(test_data)
        
        # Read encrypted binary file
        with EncryptedFile(test_file, "rb", key_manager=key_manager, purpose="binary") as f:
            read_data = f.read()
        
        assert read_data == test_data
    
    def test_append_mode(self, temp_dir, key_manager):
        """Test append mode functionality."""
        test_file = temp_dir / "append.enc"
        
        # Write initial content
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="append") as f:
            f.write("Initial content\n")
        
        # Append more content
        with EncryptedFile(test_file, "a", key_manager=key_manager, purpose="append") as f:
            f.write("Appended content\n")
        
        # Read full content
        with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="append") as f:
            content = f.read()
        
        expected = "Initial content\nAppended content\n"
        assert content == expected
    
    def test_line_operations(self, temp_dir, key_manager):
        """Test readline and readlines operations."""
        test_file = temp_dir / "lines.enc"
        lines = ["Line 1\n", "Line 2\n", "Line 3"]
        
        # Write lines
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="lines") as f:
            f.writelines(lines)
        
        # Read lines one by one
        with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="lines") as f:
            line1 = f.readline()
            line2 = f.readline()
            line3 = f.readline()
        
        assert line1 == "Line 1\n"
        assert line2 == "Line 2\n"
        assert line3 == "Line 3"
        
        # Read all lines at once
        with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="lines") as f:
            all_lines = f.readlines()
        
        assert all_lines == lines
    
    def test_seek_tell(self, temp_dir, key_manager):
        """Test seek and tell operations."""
        test_file = temp_dir / "seek.enc"
        test_data = "0123456789"
        
        # Write test data
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="seek") as f:
            f.write(test_data)
        
        # Test seek and tell
        with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="seek") as f:
            assert f.tell() == 0
            
            # Seek to middle
            f.seek(5)
            assert f.tell() == 5
            assert f.read(3) == "567"
            
            # Seek to beginning
            f.seek(0)
            assert f.tell() == 0
            assert f.read(3) == "012"
    
    def test_iteration(self, temp_dir, key_manager):
        """Test file iteration."""
        test_file = temp_dir / "iter.enc"
        lines = ["Line 1\n", "Line 2\n", "Line 3\n"]
        
        # Write lines
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="iter") as f:
            f.writelines(lines)
        
        # Iterate over lines
        with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="iter") as f:
            read_lines = list(f)
        
        assert read_lines == lines
    
    def test_different_purposes(self, temp_dir, key_manager):
        """Test that different purposes use different keys."""
        test_file1 = temp_dir / "purpose1.enc"
        test_file2 = temp_dir / "purpose2.enc"
        test_data = "Same data, different keys"
        
        # Write with different purposes
        with EncryptedFile(test_file1, "w", key_manager=key_manager, purpose="purpose1") as f:
            f.write(test_data)
        
        with EncryptedFile(test_file2, "w", key_manager=key_manager, purpose="purpose2") as f:
            f.write(test_data)
        
        # Files should have different encrypted content
        with open(test_file1, "rb") as f1, open(test_file2, "rb") as f2:
            content1 = f1.read()
            content2 = f2.read()
            assert content1 != content2
        
        # But should decrypt to same content with correct purpose
        with EncryptedFile(test_file1, "r", key_manager=key_manager, purpose="purpose1") as f:
            read1 = f.read()
        
        with EncryptedFile(test_file2, "r", key_manager=key_manager, purpose="purpose2") as f:
            read2 = f.read()
        
        assert read1 == test_data
        assert read2 == test_data
    
    def test_wrong_purpose_fails(self, temp_dir, key_manager):
        """Test that wrong purpose fails to decrypt."""
        test_file = temp_dir / "wrong_purpose.enc"
        test_data = "Secret data"
        
        # Write with one purpose
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="correct") as f:
            f.write(test_data)
        
        # Try to read with wrong purpose - should fail
        with pytest.raises(CorruptedFileError):
            with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="wrong") as f:
                f.read()
    
    def test_file_corruption_detection(self, temp_dir, key_manager):
        """Test detection of corrupted files."""
        test_file = temp_dir / "corrupt.enc"
        test_data = "Data to corrupt"
        
        # Write encrypted file
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="corrupt") as f:
            f.write(test_data)
        
        # Corrupt the file by modifying a byte
        with open(test_file, "r+b") as f:
            f.seek(-5, 2)  # Go near the end (auth tag area)
            f.write(b"\xFF")  # Corrupt a byte
        
        # Try to read corrupted file - should fail
        with pytest.raises(CorruptedFileError):
            with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="corrupt") as f:
                f.read()
    
    def test_encryption_verification(self, temp_dir, key_manager):
        """Test encryption verification methods."""
        test_file = temp_dir / "verify.enc"
        test_data = "Data to verify"
        
        # Write encrypted file
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="verify") as f:
            f.write(test_data)
        
        # Verify encryption
        encrypted_file = EncryptedFile(test_file, "r", key_manager=key_manager, purpose="verify")
        assert encrypted_file.verify_encryption() is True
        
        # Get encryption info
        info = encrypted_file.get_encryption_info()
        assert info["algorithm"] == "AES-256-GCM"
        assert info["key_size"] == 256
        assert info["is_encrypted"] is True
        assert info["file_size"] > len(test_data)
    
    def test_open_encrypted_function(self, temp_dir, key_manager):
        """Test the open_encrypted convenience function."""
        test_file = temp_dir / "convenience.enc"
        test_data = "Testing convenience function"
        
        # Write using convenience function
        with open_encrypted(test_file, "w", key_manager=key_manager, purpose="convenience") as f:
            f.write(test_data)
        
        # Read using convenience function
        with open_encrypted(test_file, "r", key_manager=key_manager, purpose="convenience") as f:
            read_data = f.read()
        
        assert read_data == test_data
    
    def test_large_file_streaming(self, temp_dir, key_manager):
        """Test streaming with larger files."""
        test_file = temp_dir / "large.enc"
        
        # Create larger test data (1MB)
        chunk = "0123456789" * 100  # 1KB chunk
        large_data = chunk * 1024  # 1MB total
        
        # Write large file
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="large") as f:
            f.write(large_data)
        
        # Read large file
        with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="large") as f:
            read_data = f.read()
        
        assert read_data == large_data
        assert len(read_data) == len(large_data)
    
    def test_file_properties(self, temp_dir, key_manager):
        """Test file object properties."""
        test_file = temp_dir / "properties.enc"
        
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="props") as f:
            assert f.name == str(test_file)
            assert f.writable is True
            assert f.readable is False
            assert f.seekable is True
            assert f.closed is False
        
        # After closing
        assert f.closed is True
        
        with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="props") as f:
            assert f.readable is True
            assert f.writable is False
    
    def test_invalid_modes(self, temp_dir, key_manager):
        """Test invalid file modes."""
        test_file = temp_dir / "invalid.enc"
        
        with pytest.raises(ValueError):
            EncryptedFile(test_file, "x", key_manager=key_manager, purpose="invalid")
        
        with pytest.raises(ValueError):
            EncryptedFile(test_file, "rw", key_manager=key_manager, purpose="invalid")
    
    def test_missing_file_read(self, temp_dir, key_manager):
        """Test reading non-existent file."""
        test_file = temp_dir / "missing.enc"
        
        with pytest.raises(FileNotFoundError):
            with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="missing") as f:
                f.read()
    
    def test_configuration_integration(self, temp_dir, key_manager):
        """Test integration with configuration system."""
        test_file = temp_dir / "config.enc"
        
        # Create file with custom chunk size
        with EncryptedFile(test_file, "w", key_manager=key_manager, purpose="config", chunk_size=32768) as f:
            f.write("Configuration test data")
            assert f.chunk_size == 32768
        
        # Read should work normally
        with EncryptedFile(test_file, "r", key_manager=key_manager, purpose="config") as f:
            data = f.read()
            assert data == "Configuration test data"
