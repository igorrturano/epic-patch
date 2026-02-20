#!/usr/bin/env python3
"""
UO File Encryption/Decryption Tool using AES-256-GCM

This tool provides secure encryption for Ultima Online data files (.mul, .uop, .idx, etc.)
using AES-256 in GCM mode for authenticated encryption.

Security Features:
- AES-256-GCM: Provides both encryption and authentication
- Random IV/Nonce for each file
- Key derivation from passphrase using PBKDF2
- File integrity verification

Usage:
    python uo_crypto.py encrypt <file> --passphrase "your_secret_passphrase"
    python uo_crypto.py decrypt <file.enc> --passphrase "your_secret_passphrase"
    python uo_crypto.py encrypt-batch <directory> --passphrase "your_secret_passphrase"
"""

import os
import sys
import argparse
import hashlib
from pathlib import Path
from typing import Optional

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    from Crypto.Protocol.KDF import PBKDF2
except ImportError:
    try:
        from Cryptodome.Cipher import AES
        from Cryptodome.Random import get_random_bytes
        from Cryptodome.Protocol.KDF import PBKDF2
    except ImportError:
        print("ERROR: pycryptodome not installed.")
        print("Install it with: pip install pycryptodome")
        sys.exit(1)


class UOCrypto:
    """Handles encryption and decryption of UO files using AES-256-GCM"""

    # File format constants
    MAGIC_HEADER = b'UOENC'  # Magic bytes to identify encrypted files
    VERSION = b'\x01'  # Version byte
    SALT_SIZE = 32  # Salt size for key derivation
    NONCE_SIZE = 16  # GCM nonce size
    TAG_SIZE = 16  # GCM authentication tag size

    # File extensions to encrypt
    UO_EXTENSIONS = {'.mul', '.uop', '.idx', '.def', '.txt'}

    def __init__(self, passphrase: str):
        """
        Initialize the crypto handler with a passphrase.

        Args:
            passphrase: Secret passphrase for key derivation
        """
        self.passphrase = passphrase.encode('utf-8')

    def derive_key(self, salt: bytes) -> bytes:
        """
        Derive a 256-bit key from passphrase using PBKDF2.

        Args:
            salt: Random salt for key derivation

        Returns:
            32-byte AES-256 key
        """
        try:
            # Try newer API first (Cryptodome)
            from Crypto import Hash
            return PBKDF2(
                self.passphrase,
                salt,
                dkLen=32,  # 256 bits
                count=100000,  # Iterations
                hmac_hash_module=Hash.SHA256
            )
        except (ImportError, AttributeError):
            # Fallback to older API
            return PBKDF2(
                self.passphrase,
                salt,
                dkLen=32,  # 256 bits
                count=100000  # Iterations
            )

    def encrypt_file(self, input_path: str, output_path: Optional[str] = None) -> bool:
        """
        Encrypt a file using AES-256-GCM.

        File format:
        [MAGIC_HEADER(5)][VERSION(1)][SALT(32)][NONCE(16)][TAG(16)][ENCRYPTED_DATA]

        Args:
            input_path: Path to file to encrypt
            output_path: Output path (defaults to input_path + '.enc')

        Returns:
            True if successful, False otherwise
        """
        input_file = Path(input_path)

        if not input_file.exists():
            print(f"ERROR: File not found: {input_path}")
            return False

        if output_path is None:
            output_path = str(input_file) + '.enc'

        try:
            # Read original file
            with open(input_file, 'rb') as f:
                plaintext = f.read()

            # Generate random salt and nonce
            salt = get_random_bytes(self.SALT_SIZE)
            nonce = get_random_bytes(self.NONCE_SIZE)

            # Derive key from passphrase
            key = self.derive_key(salt)

            # Create cipher and encrypt
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext)

            # Write encrypted file
            with open(output_path, 'wb') as f:
                f.write(self.MAGIC_HEADER)
                f.write(self.VERSION)
                f.write(salt)
                f.write(nonce)
                f.write(tag)
                f.write(ciphertext)

            file_size = len(plaintext)
            encrypted_size = os.path.getsize(output_path)

            print(f"✓ Encrypted: {input_file.name}")
            print(f"  Original size: {file_size:,} bytes")
            print(f"  Encrypted size: {encrypted_size:,} bytes")
            print(f"  Output: {output_path}")

            return True

        except Exception as e:
            print(f"ERROR encrypting {input_path}: {e}")
            return False

    def decrypt_file(self, input_path: str, output_path: Optional[str] = None) -> bool:
        """
        Decrypt a file encrypted with encrypt_file().

        Args:
            input_path: Path to encrypted file
            output_path: Output path (defaults to input_path without '.enc')

        Returns:
            True if successful, False otherwise
        """
        input_file = Path(input_path)

        if not input_file.exists():
            print(f"ERROR: File not found: {input_path}")
            return False

        if output_path is None:
            output_path = str(input_file).replace('.enc', '')
            if output_path == str(input_file):
                output_path = str(input_file) + '.dec'

        try:
            # Read encrypted file
            with open(input_file, 'rb') as f:
                data = f.read()

            # Verify magic header
            if not data.startswith(self.MAGIC_HEADER):
                print(f"ERROR: Not a valid encrypted UO file (missing magic header)")
                return False

            # Parse file structure
            offset = len(self.MAGIC_HEADER)
            version = data[offset:offset+1]
            offset += 1

            if version != self.VERSION:
                print(f"ERROR: Unsupported file version: {version.hex()}")
                return False

            salt = data[offset:offset+self.SALT_SIZE]
            offset += self.SALT_SIZE

            nonce = data[offset:offset+self.NONCE_SIZE]
            offset += self.NONCE_SIZE

            tag = data[offset:offset+self.TAG_SIZE]
            offset += self.TAG_SIZE

            ciphertext = data[offset:]

            # Derive key
            key = self.derive_key(salt)

            # Decrypt and verify
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)

            # Write decrypted file
            with open(output_path, 'wb') as f:
                f.write(plaintext)

            file_size = len(plaintext)

            print(f"✓ Decrypted: {input_file.name}")
            print(f"  Decrypted size: {file_size:,} bytes")
            print(f"  Output: {output_path}")

            return True

        except ValueError as e:
            print(f"ERROR: Decryption failed - wrong passphrase or corrupted file")
            return False
        except Exception as e:
            print(f"ERROR decrypting {input_path}: {e}")
            return False

    def encrypt_directory(self, directory: str, extensions: Optional[set] = None,
                         recursive: bool = True, keep_original: bool = True) -> dict:
        """
        Encrypt all UO files in a directory.

        Args:
            directory: Directory to process
            extensions: Set of file extensions to encrypt (default: UO_EXTENSIONS)
            recursive: Process subdirectories
            keep_original: Keep original files after encryption

        Returns:
            Dictionary with encryption statistics
        """
        if extensions is None:
            extensions = self.UO_EXTENSIONS

        directory = Path(directory)

        if not directory.exists() or not directory.is_dir():
            print(f"ERROR: Directory not found: {directory}")
            return {'success': 0, 'failed': 0, 'skipped': 0}

        stats = {'success': 0, 'failed': 0, 'skipped': 0}

        # Find all files to encrypt
        pattern = '**/*' if recursive else '*'
        files_to_encrypt = []

        for ext in extensions:
            files_to_encrypt.extend(directory.glob(f'{pattern}{ext}'))

        # Filter out already encrypted files
        files_to_encrypt = [f for f in files_to_encrypt if not f.name.endswith('.enc')]

        if not files_to_encrypt:
            print(f"No files to encrypt in {directory}")
            return stats

        print(f"\nFound {len(files_to_encrypt)} files to encrypt")
        print(f"Extensions: {', '.join(sorted(extensions))}")
        print(f"Recursive: {recursive}")
        print(f"Keep originals: {keep_original}\n")

        # Encrypt each file
        for file_path in files_to_encrypt:
            output_path = str(file_path) + '.enc'

            # Skip if encrypted file already exists
            if Path(output_path).exists():
                print(f"⊘ Skipped: {file_path.name} (encrypted version exists)")
                stats['skipped'] += 1
                continue

            if self.encrypt_file(str(file_path), output_path):
                stats['success'] += 1

                # Optionally remove original
                if not keep_original:
                    try:
                        file_path.unlink()
                        print(f"  Removed original file")
                    except Exception as e:
                        print(f"  WARNING: Could not remove original: {e}")
            else:
                stats['failed'] += 1

            print()  # Blank line between files

        # Print summary
        print("=" * 60)
        print(f"Encryption Summary:")
        print(f"  Successful: {stats['success']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped: {stats['skipped']}")
        print("=" * 60)

        return stats


def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(
        description='UO File Encryption/Decryption Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Encrypt command
    encrypt_parser = subparsers.add_parser('encrypt', help='Encrypt a single file')
    encrypt_parser.add_argument('file', help='File to encrypt')
    encrypt_parser.add_argument('-o', '--output', help='Output file path')
    encrypt_parser.add_argument('-p', '--passphrase', required=True,
                               help='Encryption passphrase')

    # Decrypt command
    decrypt_parser = subparsers.add_parser('decrypt', help='Decrypt a single file')
    decrypt_parser.add_argument('file', help='File to decrypt')
    decrypt_parser.add_argument('-o', '--output', help='Output file path')
    decrypt_parser.add_argument('-p', '--passphrase', required=True,
                               help='Decryption passphrase')

    # Batch encrypt command
    batch_parser = subparsers.add_parser('encrypt-batch',
                                        help='Encrypt all UO files in a directory')
    batch_parser.add_argument('directory', help='Directory to process')
    batch_parser.add_argument('-p', '--passphrase', required=True,
                             help='Encryption passphrase')
    batch_parser.add_argument('-r', '--recursive', action='store_true',
                             help='Process subdirectories')
    batch_parser.add_argument('--remove-original', action='store_true',
                             help='Remove original files after encryption')
    batch_parser.add_argument('--extensions', nargs='+',
                             help='File extensions to encrypt (default: .mul .uop .idx)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Create crypto instance
    crypto = UOCrypto(args.passphrase)

    # Execute command
    if args.command == 'encrypt':
        success = crypto.encrypt_file(args.file, args.output)
        return 0 if success else 1

    elif args.command == 'decrypt':
        success = crypto.decrypt_file(args.file, args.output)
        return 0 if success else 1

    elif args.command == 'encrypt-batch':
        extensions = None
        if args.extensions:
            extensions = {ext if ext.startswith('.') else f'.{ext}'
                         for ext in args.extensions}

        stats = crypto.encrypt_directory(
            args.directory,
            extensions=extensions,
            recursive=args.recursive,
            keep_original=not args.remove_original
        )

        return 0 if stats['failed'] == 0 else 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
