"""
Low-level cryptographic operations for file encryption.

This module provides the core AES-GCM encryption/decryption functionality
used by the EncryptedFile wrapper class.
"""

import os
import struct
from typing import Tuple, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .exceptions import EncryptionError, DecryptionError, InvalidFileFormatError


class FileCrypto:
    """Low-level file encryption/decryption operations using AES-256-GCM."""
    
    # File format constants
    HEADER_MAGIC = b"AICO"
    HEADER_SIZE = 4
    SALT_SIZE = 16
    NONCE_SIZE = 12
    TAG_SIZE = 16
    
    # Total overhead per file
    OVERHEAD_SIZE = HEADER_SIZE + SALT_SIZE + NONCE_SIZE + TAG_SIZE
    
    def __init__(self, key: bytes, chunk_size: int = 65536):
        """
        Initialize FileCrypto with encryption key.
        
        Args:
            key: 32-byte AES-256 encryption key
            chunk_size: Size of chunks for streaming operations
        """
        if len(key) != 32:
            raise ValueError("Key must be exactly 32 bytes for AES-256")
        
        self.key = key
        self.chunk_size = chunk_size
        self.aesgcm = AESGCM(key)
    
    def generate_salt(self) -> bytes:
        """Generate a random 16-byte salt."""
        return os.urandom(self.SALT_SIZE)
    
    def generate_nonce(self) -> bytes:
        """Generate a random 12-byte nonce for GCM."""
        return os.urandom(self.NONCE_SIZE)
    
    def create_file_header(self, salt: bytes, nonce: bytes) -> bytes:
        """
        Create the file header containing magic, salt, and nonce.
        
        Args:
            salt: 16-byte salt used for key derivation
            nonce: 12-byte nonce for GCM encryption
            
        Returns:
            Complete file header (32 bytes total)
        """
        if len(salt) != self.SALT_SIZE:
            raise ValueError(f"Salt must be {self.SALT_SIZE} bytes")
        if len(nonce) != self.NONCE_SIZE:
            raise ValueError(f"Nonce must be {self.NONCE_SIZE} bytes")
        
        return self.HEADER_MAGIC + salt + nonce
    
    def parse_file_header(self, header_data: bytes) -> Tuple[bytes, bytes]:
        """
        Parse file header to extract salt and nonce.
        
        Args:
            header_data: First 32 bytes of encrypted file
            
        Returns:
            Tuple of (salt, nonce)
            
        Raises:
            InvalidFileFormatError: If header format is invalid
        """
        if len(header_data) < self.HEADER_SIZE + self.SALT_SIZE + self.NONCE_SIZE:
            raise InvalidFileFormatError("Header too short")
        
        # Check magic bytes
        magic = header_data[:self.HEADER_SIZE]
        if magic != self.HEADER_MAGIC:
            raise InvalidFileFormatError(f"Invalid magic bytes: {magic}")
        
        # Extract salt and nonce
        salt = header_data[self.HEADER_SIZE:self.HEADER_SIZE + self.SALT_SIZE]
        nonce = header_data[self.HEADER_SIZE + self.SALT_SIZE:self.HEADER_SIZE + self.SALT_SIZE + self.NONCE_SIZE]
        
        return salt, nonce
    
    def encrypt_data(self, plaintext: bytes, nonce: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            nonce: 12-byte nonce for GCM
            associated_data: Optional additional authenticated data
            
        Returns:
            Encrypted data (ciphertext + 16-byte auth tag)
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            return self.aesgcm.encrypt(nonce, plaintext, associated_data)
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}") from e
    
    def decrypt_data(self, ciphertext_with_tag: bytes, nonce: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """
        Decrypt data using AES-256-GCM.
        
        Args:
            ciphertext_with_tag: Encrypted data with authentication tag
            nonce: 12-byte nonce used for encryption
            associated_data: Optional additional authenticated data
            
        Returns:
            Decrypted plaintext data
            
        Raises:
            DecryptionError: If decryption or authentication fails
        """
        try:
            return self.aesgcm.decrypt(nonce, ciphertext_with_tag, associated_data)
        except Exception as e:
            raise DecryptionError(f"Decryption failed: {e}") from e
    
    def encrypt_file_streaming(self, input_file, output_file, progress_callback=None):
        """
        Encrypt a file using streaming to handle large files efficiently.
        
        Args:
            input_file: File-like object to read plaintext from
            output_file: File-like object to write encrypted data to
            progress_callback: Optional callback function for progress updates
        """
        try:
            # Generate salt and nonce
            salt = self.generate_salt()
            nonce = self.generate_nonce()
            
            # Write header
            header = self.create_file_header(salt, nonce)
            output_file.write(header)
            
            # Read all data (for single GCM operation)
            plaintext = input_file.read()
            
            # Encrypt with associated data (header for additional authentication)
            ciphertext_with_tag = self.encrypt_data(plaintext, nonce, header)
            
            # Write encrypted data
            output_file.write(ciphertext_with_tag)
            
            if progress_callback:
                progress_callback(len(plaintext), len(plaintext))
                
        except Exception as e:
            raise EncryptionError(f"File encryption failed: {e}") from e
    
    def decrypt_file_streaming(self, input_file, output_file, progress_callback=None):
        """
        Decrypt a file using streaming to handle large files efficiently.
        
        Args:
            input_file: File-like object to read encrypted data from
            output_file: File-like object to write plaintext to
            progress_callback: Optional callback function for progress updates
        """
        try:
            # Read and parse header
            header_data = input_file.read(self.HEADER_SIZE + self.SALT_SIZE + self.NONCE_SIZE)
            if len(header_data) < self.HEADER_SIZE + self.SALT_SIZE + self.NONCE_SIZE:
                raise InvalidFileFormatError("File too short to contain valid header")
            
            salt, nonce = self.parse_file_header(header_data)
            
            # Read remaining encrypted data
            ciphertext_with_tag = input_file.read()
            if len(ciphertext_with_tag) < self.TAG_SIZE:
                raise InvalidFileFormatError("File too short to contain authentication tag")
            
            # Decrypt with header as associated data
            plaintext = self.decrypt_data(ciphertext_with_tag, nonce, header_data)
            
            # Write decrypted data
            output_file.write(plaintext)
            
            if progress_callback:
                progress_callback(len(plaintext), len(plaintext))
                
        except (EncryptionError, DecryptionError, InvalidFileFormatError):
            raise
        except Exception as e:
            raise DecryptionError(f"File decryption failed: {e}") from e
    
    def verify_file_format(self, file_path: str) -> bool:
        """
        Verify that a file has the correct encrypted format.
        
        Args:
            file_path: Path to file to verify
            
        Returns:
            True if file has valid encrypted format, False otherwise
        """
        try:
            with open(file_path, "rb") as f:
                header_data = f.read(self.HEADER_SIZE)
                return header_data == self.HEADER_MAGIC
        except (OSError, IOError):
            return False
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Get information about an encrypted file.
        
        Args:
            file_path: Path to encrypted file
            
        Returns:
            Dictionary with file information
        """
        try:
            with open(file_path, "rb") as f:
                # Get file size
                f.seek(0, 2)  # Seek to end
                total_size = f.tell()
                f.seek(0)  # Seek back to start
                
                # Read header
                header_data = f.read(self.HEADER_SIZE + self.SALT_SIZE + self.NONCE_SIZE)
                if len(header_data) < self.HEADER_SIZE + self.SALT_SIZE + self.NONCE_SIZE:
                    raise InvalidFileFormatError("Invalid file format")
                
                salt, nonce = self.parse_file_header(header_data)
                
                # Calculate payload size
                payload_size = total_size - self.OVERHEAD_SIZE
                
                return {
                    "algorithm": "AES-256-GCM",
                    "key_size": 256,
                    "file_size": total_size,
                    "payload_size": payload_size,
                    "overhead_size": self.OVERHEAD_SIZE,
                    "salt": salt.hex(),
                    "nonce": nonce.hex(),
                    "is_encrypted": True
                }
        except Exception as e:
            return {
                "algorithm": "Unknown",
                "key_size": 0,
                "file_size": 0,
                "payload_size": 0,
                "overhead_size": 0,
                "salt": "",
                "nonce": "",
                "is_encrypted": False,
                "error": str(e)
            }
