"""
Transparent file encryption wrapper for AICO.

This module provides EncryptedFile, a drop-in replacement for Python's open()
function that transparently encrypts and decrypts files using AES-256-GCM.
"""

import os
import io
from typing import Optional, Union, Any, Iterator
from pathlib import Path

from ..core.config import ConfigurationManager
from ..core.logging import AICOLogger
from .key_manager import AICOKeyManager
from .file_crypto import FileCrypto
from .exceptions import (
    EncryptionError, 
    DecryptionError, 
    InvalidKeyError, 
    CorruptedFileError,
    InvalidFileFormatError
)


class EncryptedFile:
    """
    Transparent file encryption wrapper using AES-256-GCM.
    
    Provides a drop-in replacement for Python's open() function with
    transparent encryption/decryption capabilities.
    """
    
    def __init__(
        self,
        file_path: Union[str, Path],
        mode: str = "r",
        key_manager: Optional[AICOKeyManager] = None,
        purpose: str = "default",
        chunk_size: Optional[int] = None,
        encoding: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize EncryptedFile wrapper.
        
        Args:
            file_path: Path to the file
            mode: File mode ('r', 'w', 'rb', 'wb', 'a', 'ab')
            key_manager: AICOKeyManager instance for key operations
            purpose: Purpose identifier for key derivation
            chunk_size: Chunk size for streaming operations
            encoding: Text encoding (for text modes)
            **kwargs: Additional arguments (for compatibility)
        """
        self.file_path = Path(file_path)
        self.mode = mode
        self.purpose = purpose
        self.encoding = encoding or "utf-8"
        
        # Initialize components
        self.config = ConfigurationManager()
        self.logger = AICOLogger(
            subsystem="security",
            module="aico.security.encrypted_file", 
            config_manager=self.config
        )
        
        # Key manager setup
        if key_manager is None:
            self.key_manager = AICOKeyManager(self.config)
        else:
            self.key_manager = key_manager
        
        # Configuration
        self.chunk_size = chunk_size or self.config.get("file_encryption.chunk_size", 65536)
        self.buffer_size = self.config.get("file_encryption.buffer_size", 1048576)
        
        # Validate mode
        self._validate_mode()
        
        # File state
        self._file_handle = None
        self._crypto = None
        self._temp_file = None
        self._is_open = False
        self._position = 0
        self._file_size = None
        
        # Encryption key (derived lazily)
        self._encryption_key = None
    
    def _validate_mode(self):
        """Validate file mode."""
        valid_modes = {"r", "w", "a", "rb", "wb", "ab"}
        if self.mode not in valid_modes:
            raise ValueError(f"Unsupported mode: {self.mode}. Supported modes: {valid_modes}")
    
    def _get_encryption_key(self) -> bytes:
        """Get or derive the encryption key for this file."""
        if self._encryption_key is None:
            try:
                master_key = self.key_manager.authenticate(interactive=False)
                self._encryption_key = self.key_manager.derive_file_encryption_key(
                    master_key, self.purpose
                )
                self.logger.debug(f"Derived encryption key for purpose: {self.purpose}")
            except Exception as e:
                raise InvalidKeyError(f"Failed to derive encryption key: {e}") from e
        
        return self._encryption_key
    
    def _setup_crypto(self):
        """Initialize the crypto handler."""
        if self._crypto is None:
            key = self._get_encryption_key()
            self._crypto = FileCrypto(key, self.chunk_size)
    
    def _is_binary_mode(self) -> bool:
        """Check if file is opened in binary mode."""
        return "b" in self.mode
    
    def _is_write_mode(self) -> bool:
        """Check if file is opened for writing."""
        return any(m in self.mode for m in ["w", "a"])
    
    def _is_read_mode(self) -> bool:
        """Check if file is opened for reading."""
        return "r" in self.mode
    
    def _create_temp_file(self) -> io.BytesIO:
        """Create temporary file for write operations."""
        return io.BytesIO()
    
    def open(self):
        """Open the encrypted file."""
        if self._is_open:
            return self
        
        try:
            self._setup_crypto()
            
            if self._is_write_mode():
                self._open_for_write()
            elif self._is_read_mode():
                self._open_for_read()
            
            self._is_open = True
            self.logger.debug(f"Opened encrypted file: {self.file_path} (mode: {self.mode})")
            return self
            
        except Exception as e:
            self.logger.error(f"Failed to open encrypted file {self.file_path}: {e}")
            raise
    
    def _open_for_write(self):
        """Open file for writing (encrypt on close)."""
        # For write modes, we use a temporary buffer
        self._temp_file = self._create_temp_file()
        self._file_handle = self._temp_file
        
        # For append mode, first decrypt existing content
        if "a" in self.mode and self.file_path.exists():
            try:
                with open(self.file_path, "rb") as encrypted_file:
                    decrypted_content = io.BytesIO()
                    self._crypto.decrypt_file_streaming(encrypted_file, decrypted_content)
                    
                    # Write existing content to temp file
                    decrypted_content.seek(0)
                    self._temp_file.write(decrypted_content.read())
                    
            except Exception as e:
                self.logger.warning(f"Could not read existing file for append: {e}")
    
    def _open_for_read(self):
        """Open file for reading (decrypt on open)."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Encrypted file not found: {self.file_path}")
        
        try:
            # Decrypt entire file to memory for reading
            with open(self.file_path, "rb") as encrypted_file:
                decrypted_content = io.BytesIO()
                self._crypto.decrypt_file_streaming(encrypted_file, decrypted_content)
                
                # Set up for reading
                decrypted_content.seek(0)
                self._file_handle = decrypted_content
                self._file_size = len(decrypted_content.getvalue())
                
        except InvalidFileFormatError as e:
            raise CorruptedFileError(f"Invalid encrypted file format: {e}") from e
        except DecryptionError as e:
            raise CorruptedFileError(f"File decryption failed: {e}") from e
    
    def read(self, size: int = -1) -> Union[str, bytes]:
        """
        Read data from the encrypted file.
        
        Args:
            size: Number of bytes/characters to read (-1 for all)
            
        Returns:
            Data read from file (str for text mode, bytes for binary mode)
        """
        if not self._is_open:
            self.open()
        
        if not self._is_read_mode():
            raise io.UnsupportedOperation("File not opened for reading")
        
        data = self._file_handle.read(size)
        
        # Convert to text if in text mode
        if not self._is_binary_mode() and isinstance(data, bytes):
            data = data.decode(self.encoding)
        
        return data
    
    def readline(self, size: int = -1) -> Union[str, bytes]:
        """Read a single line from the encrypted file."""
        if not self._is_open:
            self.open()
        
        if not self._is_read_mode():
            raise io.UnsupportedOperation("File not opened for reading")
        
        if self._is_binary_mode():
            # Binary mode: read until newline byte
            line = b""
            while True:
                char = self._file_handle.read(1)
                if not char or char == b"\n":
                    if char:
                        line += char
                    break
                line += char
                if size > 0 and len(line) >= size:
                    break
            return line
        else:
            # Text mode: read until newline character
            line = ""
            while True:
                char_bytes = self._file_handle.read(1)
                if not char_bytes:
                    break
                char = char_bytes.decode(self.encoding)
                line += char
                if char == "\n":
                    break
                if size > 0 and len(line) >= size:
                    break
            return line
    
    def readlines(self) -> list:
        """Read all lines from the encrypted file."""
        if not self._is_open:
            self.open()
        
        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
        return lines
    
    def write(self, data: Union[str, bytes]) -> int:
        """
        Write data to the encrypted file.
        
        Args:
            data: Data to write (str for text mode, bytes for binary mode)
            
        Returns:
            Number of bytes/characters written
        """
        if not self._is_open:
            self.open()
        
        if not self._is_write_mode():
            raise io.UnsupportedOperation("File not opened for writing")
        
        # Convert text to bytes if necessary
        if not self._is_binary_mode() and isinstance(data, str):
            data = data.encode(self.encoding)
        elif self._is_binary_mode() and isinstance(data, str):
            raise TypeError("Cannot write str to binary mode file")
        elif not self._is_binary_mode() and isinstance(data, bytes):
            raise TypeError("Cannot write bytes to text mode file")
        
        return self._file_handle.write(data)
    
    def writelines(self, lines) -> None:
        """Write a list of lines to the encrypted file."""
        for line in lines:
            self.write(line)
    
    def seek(self, offset: int, whence: int = 0) -> int:
        """Seek to position in the encrypted file."""
        if not self._is_open:
            self.open()
        
        return self._file_handle.seek(offset, whence)
    
    def tell(self) -> int:
        """Get current position in the encrypted file."""
        if not self._is_open:
            self.open()
        
        return self._file_handle.tell()
    
    def flush(self) -> None:
        """Flush write buffers."""
        if self._is_open and self._file_handle:
            self._file_handle.flush()
    
    def close(self) -> None:
        """Close the encrypted file and perform encryption if needed."""
        if not self._is_open:
            return
        
        try:
            if self._is_write_mode() and self._temp_file:
                # Encrypt and write to actual file
                self._temp_file.seek(0)
                
                # Ensure parent directory exists
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.file_path, "wb") as output_file:
                    self._crypto.encrypt_file_streaming(self._temp_file, output_file)
                
                self.logger.info(f"Encrypted file written: {self.file_path} (purpose: {self.purpose})")
            
            # Close file handles
            if self._file_handle:
                self._file_handle.close()
                self._file_handle = None
            
            if self._temp_file:
                self._temp_file.close()
                self._temp_file = None
            
            self._is_open = False
            
        except Exception as e:
            self.logger.error(f"Error closing encrypted file {self.file_path}: {e}")
            raise EncryptionError(f"Failed to close encrypted file: {e}") from e
    
    def __enter__(self):
        """Context manager entry."""
        return self.open()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __iter__(self) -> Iterator[Union[str, bytes]]:
        """Iterate over lines in the file."""
        if not self._is_open:
            self.open()
        
        while True:
            line = self.readline()
            if not line:
                break
            yield line
    
    def verify_encryption(self) -> bool:
        """
        Verify that the file is properly encrypted.
        
        Returns:
            True if file is encrypted and can be decrypted, False otherwise
        """
        if not self.file_path.exists():
            return False
        
        try:
            self._setup_crypto()
            return self._crypto.verify_file_format(str(self.file_path))
        except Exception:
            return False
    
    def get_encryption_info(self) -> dict:
        """
        Get information about the encrypted file.
        
        Returns:
            Dictionary with encryption information
        """
        if not self.file_path.exists():
            return {"error": "File does not exist"}
        
        try:
            self._setup_crypto()
            return self._crypto.get_file_info(str(self.file_path))
        except Exception as e:
            return {"error": str(e)}
    
    @property
    def name(self) -> str:
        """Get the file name."""
        return str(self.file_path)
    
    @property
    def closed(self) -> bool:
        """Check if file is closed."""
        return not self._is_open
    
    @property
    def readable(self) -> bool:
        """Check if file is readable."""
        return self._is_read_mode()
    
    @property
    def writable(self) -> bool:
        """Check if file is writable."""
        return self._is_write_mode()
    
    @property
    def seekable(self) -> bool:
        """Check if file is seekable."""
        return True


def open_encrypted(
    file_path: Union[str, Path],
    mode: str = "r",
    key_manager: Optional[AICOKeyManager] = None,
    purpose: str = "default",
    **kwargs
) -> EncryptedFile:
    """
    Open an encrypted file - drop-in replacement for open().
    
    Args:
        file_path: Path to the file
        mode: File mode ('r', 'w', 'rb', 'wb', 'a', 'ab')
        key_manager: AICOKeyManager instance
        purpose: Purpose identifier for key derivation
        **kwargs: Additional arguments
        
    Returns:
        EncryptedFile instance
    """
    return EncryptedFile(file_path, mode, key_manager, purpose, **kwargs)
