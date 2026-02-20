#!/usr/bin/env python3
"""
UO File Loader with Transparent Decryption

This module provides a file loader that transparently decrypts encrypted UO files
in memory without writing decrypted data to disk. This is useful for:

1. Game clients that need to load encrypted files
2. Server emulators (RunUO, ServUO, etc.) that load UO data files
3. Development tools that process UO files

Usage Example:
    from uo_file_loader import UOFileLoader

    # Initialize loader with passphrase
    loader = UOFileLoader("your_secret_passphrase")

    # Load encrypted file into memory
    data = loader.load_file("art.mul.enc")

    # Use the decrypted data
    print(f"Loaded {len(data)} bytes")
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Union
from io import BytesIO

try:
    from Crypto.Cipher import AES
    from Crypto.Protocol.KDF import PBKDF2
except ImportError:
    try:
        from Cryptodome.Cipher import AES
        from Cryptodome.Protocol.KDF import PBKDF2
    except ImportError:
        print("ERROR: pycryptodome not installed.")
        print("Install it with: pip install pycryptodome")
        raise


class UOFileLoader:
    """
    Loads and decrypts UO files transparently in memory.

    This class provides methods to load encrypted UO files without writing
    decrypted data to disk, keeping data secure in memory only.
    """

    # File format constants (must match uo_crypto.py)
    MAGIC_HEADER = b'UOENC'
    VERSION = b'\x01'
    SALT_SIZE = 32
    NONCE_SIZE = 16
    TAG_SIZE = 16

    def __init__(self, passphrase: str, cache_enabled: bool = True):
        """
        Initialize the file loader.

        Args:
            passphrase: Passphrase for decryption
            cache_enabled: Enable in-memory caching of decrypted files
        """
        self.passphrase = passphrase.encode('utf-8')
        self.cache_enabled = cache_enabled
        self._cache = {}

    def derive_key(self, salt: bytes) -> bytes:
        """Derive AES-256 key from passphrase and salt."""
        try:
            # Try newer API first (Cryptodome)
            from Crypto import Hash
            return PBKDF2(
                self.passphrase,
                salt,
                dkLen=32,
                count=100000,
                hmac_hash_module=Hash.SHA256
            )
        except (ImportError, AttributeError):
            # Fallback to older API
            return PBKDF2(
                self.passphrase,
                salt,
                dkLen=32,
                count=100000
            )

    def is_encrypted(self, file_path: str) -> bool:
        """
        Check if a file is encrypted.

        Args:
            file_path: Path to file to check

        Returns:
            True if file is encrypted, False otherwise
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(len(self.MAGIC_HEADER))
                return header == self.MAGIC_HEADER
        except:
            return False

    def load_file(self, file_path: str, use_cache: bool = True) -> bytes:
        """
        Load a file, decrypting if necessary.

        Args:
            file_path: Path to file (encrypted or plain)
            use_cache: Use cached version if available

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If decryption fails
        """
        file_path = str(Path(file_path).resolve())

        # Check cache first
        if use_cache and self.cache_enabled and file_path in self._cache:
            return self._cache[file_path]

        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file
        with open(file_path, 'rb') as f:
            data = f.read()

        # Check if encrypted
        if data.startswith(self.MAGIC_HEADER):
            data = self._decrypt_data(data)

        # Cache if enabled
        if self.cache_enabled:
            self._cache[file_path] = data

        return data

    def _decrypt_data(self, data: bytes) -> bytes:
        """
        Decrypt encrypted file data.

        Args:
            data: Encrypted file data

        Returns:
            Decrypted data

        Raises:
            ValueError: If decryption fails
        """
        # Verify magic header
        if not data.startswith(self.MAGIC_HEADER):
            raise ValueError("Not a valid encrypted UO file")

        # Parse file structure
        offset = len(self.MAGIC_HEADER)
        version = data[offset:offset+1]
        offset += 1

        if version != self.VERSION:
            raise ValueError(f"Unsupported file version: {version.hex()}")

        salt = data[offset:offset+self.SALT_SIZE]
        offset += self.SALT_SIZE

        nonce = data[offset:offset+self.NONCE_SIZE]
        offset += self.NONCE_SIZE

        tag = data[offset:offset+self.TAG_SIZE]
        offset += self.TAG_SIZE

        ciphertext = data[offset:]

        # Derive key and decrypt
        key = self.derive_key(salt)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

        try:
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext
        except ValueError:
            raise ValueError("Decryption failed - wrong passphrase or corrupted file")

    def load_file_stream(self, file_path: str) -> BytesIO:
        """
        Load a file and return as a BytesIO stream.

        This is useful for code that expects file-like objects.

        Args:
            file_path: Path to file

        Returns:
            BytesIO stream containing decrypted data
        """
        data = self.load_file(file_path)
        return BytesIO(data)

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()

    def get_cache_size(self) -> int:
        """
        Get total size of cached data in bytes.

        Returns:
            Total bytes in cache
        """
        return sum(len(data) for data in self._cache.values())

    def preload_files(self, file_paths: list):
        """
        Preload multiple files into cache.

        Args:
            file_paths: List of file paths to preload
        """
        for file_path in file_paths:
            try:
                self.load_file(file_path)
            except Exception as e:
                print(f"Warning: Failed to preload {file_path}: {e}")


class UOFileManager:
    """
    High-level manager for UO files with automatic path resolution.

    This class provides a convenient interface for loading UO files from
    multiple directories with fallback support.
    """

    def __init__(self, passphrase: str, search_paths: Optional[list] = None):
        """
        Initialize the file manager.

        Args:
            passphrase: Passphrase for decryption
            search_paths: List of directories to search for files
        """
        self.loader = UOFileLoader(passphrase)
        self.search_paths = search_paths or ['.']

    def add_search_path(self, path: str):
        """Add a directory to search for files."""
        if path not in self.search_paths:
            self.search_paths.append(path)

    def find_file(self, filename: str) -> Optional[str]:
        """
        Find a file in search paths.

        Looks for both encrypted (.enc) and plain versions.

        Args:
            filename: Name of file to find

        Returns:
            Full path to file, or None if not found
        """
        for search_path in self.search_paths:
            # Try encrypted version first
            enc_path = os.path.join(search_path, filename + '.enc')
            if os.path.exists(enc_path):
                return enc_path

            # Try plain version
            plain_path = os.path.join(search_path, filename)
            if os.path.exists(plain_path):
                return plain_path

        return None

    def load(self, filename: str) -> bytes:
        """
        Load a file by name, searching all search paths.

        Args:
            filename: Name of file to load

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file not found in any search path
        """
        file_path = self.find_file(filename)

        if file_path is None:
            raise FileNotFoundError(
                f"File '{filename}' not found in search paths: {self.search_paths}"
            )

        return self.loader.load_file(file_path)

    def load_stream(self, filename: str) -> BytesIO:
        """
        Load a file as a stream by name.

        Args:
            filename: Name of file to load

        Returns:
            BytesIO stream containing file data
        """
        data = self.load(filename)
        return BytesIO(data)


# Example usage and testing
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python uo_file_loader.py <encrypted_file> <passphrase>")
        print("\nExample:")
        print("  python uo_file_loader.py art.mul.enc 'my_secret_passphrase'")
        sys.exit(1)

    file_path = sys.argv[1]
    passphrase = sys.argv[2]

    try:
        # Create loader
        loader = UOFileLoader(passphrase)

        # Check if encrypted
        is_enc = loader.is_encrypted(file_path)
        print(f"File: {file_path}")
        print(f"Encrypted: {is_enc}")

        # Load file
        print("\nLoading file...")
        data = loader.load_file(file_path)

        print(f"✓ Successfully loaded {len(data):,} bytes")
        print(f"First 64 bytes (hex): {data[:64].hex()}")

        # Show cache stats
        print(f"\nCache size: {loader.get_cache_size():,} bytes")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
