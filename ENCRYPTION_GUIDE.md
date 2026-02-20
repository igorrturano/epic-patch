# UO File Encryption Guide

Complete guide for encrypting and protecting your Ultima Online game files using AES-256-GCM encryption.

## Table of Contents

1. [Overview](#overview)
2. [Security Features](#security-features)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Usage Examples](#usage-examples)
6. [Client Integration](#client-integration)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This encryption system protects your UO files (.mul, .uop, .idx) from unauthorized access and extraction. It uses industry-standard AES-256-GCM encryption with the following features:

- **AES-256-GCM**: Authenticated encryption (encryption + integrity verification)
- **PBKDF2**: Secure key derivation from passphrase
- **Random IV/Nonce**: Each file gets unique encryption parameters
- **In-memory decryption**: Client never writes decrypted data to disk

## Security Features

### Why AES-256-GCM?

1. **Encryption**: AES-256 is the gold standard (used by governments)
2. **Authentication**: GCM mode detects tampering and corruption
3. **Performance**: Hardware-accelerated on modern CPUs
4. **Security**: Each file has unique nonce (no pattern leakage)

### File Format

```
[MAGIC_HEADER (5 bytes)] "UOENC"
[VERSION (1 byte)]        0x01
[SALT (32 bytes)]         Random salt for key derivation
[NONCE (16 bytes)]        Random nonce for GCM
[TAG (16 bytes)]          Authentication tag
[ENCRYPTED_DATA]          Your file data
```

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Install Dependencies

```bash
# Install pycryptodome (AES-GCM implementation)
pip install pycryptodome

# Verify installation
python3 -c "from Cryptodome.Cipher import AES; print('✓ Installation successful')"
```

### Files Included

- `uo_crypto.py` - Main encryption/decryption tool
- `uo_file_loader.py` - Client-side transparent file loader
- `client_integration_example.cs` - C# integration example
- `ENCRYPTION_GUIDE.md` - This guide

---

## Quick Start

### 1. Encrypt a Single File

```bash
python3 uo_crypto.py encrypt art.mul --passphrase "your_secret_passphrase"
```

Output: `art.mul.enc`

### 2. Encrypt All Files in Directory

```bash
python3 uo_crypto.py encrypt-batch . --passphrase "your_secret_passphrase" --recursive
```

### 3. Decrypt a File

```bash
python3 uo_crypto.py decrypt art.mul.enc --passphrase "your_secret_passphrase"
```

Output: `art.mul`

---

## Usage Examples

### Example 1: Encrypt Current Directory

Encrypt all UO files in the current directory:

```bash
python3 uo_crypto.py encrypt-batch . \
    --passphrase "MyStrongPassword123!" \
    --recursive
```

This will:
- Find all .mul, .uop, .idx files
- Create encrypted .enc versions
- Keep original files

### Example 2: Encrypt and Remove Originals

**⚠️ WARNING: This deletes original files! Make backups first!**

```bash
# Make backup first!
tar -czf uo_files_backup.tar.gz *.mul *.uop *.idx

# Encrypt and remove originals
python3 uo_crypto.py encrypt-batch . \
    --passphrase "MyStrongPassword123!" \
    --remove-original
```

### Example 3: Encrypt Specific File Types

Encrypt only animation files:

```bash
python3 uo_crypto.py encrypt-batch . \
    --passphrase "MyPassword" \
    --extensions .mul \
    --recursive
```

### Example 4: Encrypt Multiple Directories

```bash
# Encrypt main game files
python3 uo_crypto.py encrypt-batch /path/to/uo/data \
    --passphrase "MyPassword" \
    --recursive

# Encrypt patch files
python3 uo_crypto.py encrypt-batch /path/to/uo/patch \
    --passphrase "MyPassword" \
    --recursive
```

### Example 5: Batch Script for All Files

Create a shell script `encrypt_all.sh`:

```bash
#!/bin/bash

PASSPHRASE="YourSecretPassphrase123!"

# Directories to encrypt
DIRS=(
    "/home/user/uo/data"
    "/home/user/uo/patch"
    "/home/user/uo/custom"
)

for dir in "${DIRS[@]}"; do
    echo "Encrypting: $dir"
    python3 uo_crypto.py encrypt-batch "$dir" \
        --passphrase "$PASSPHRASE" \
        --recursive
    echo ""
done

echo "✓ All directories encrypted!"
```

Make executable and run:

```bash
chmod +x encrypt_all.sh
./encrypt_all.sh
```

---

## Client Integration

### Python Client/Server

Use the `UOFileLoader` class for transparent decryption:

```python
from uo_file_loader import UOFileLoader, UOFileManager

# Method 1: Simple loader
loader = UOFileLoader("your_passphrase")
data = loader.load_file("art.mul.enc")

# Method 2: File manager with search paths
manager = UOFileManager(
    passphrase="your_passphrase",
    search_paths=["./data", "./patch"]
)

# Automatically finds encrypted or plain version
art_data = manager.load("art.mul")
gump_data = manager.load("gumpart.mul")

print(f"Loaded art.mul: {len(art_data)} bytes")
```

### C# Client (ClassicUO, RunUO, ServUO)

See `client_integration_example.cs` for full implementation.

Basic usage:

```csharp
// Initialize decryptor
var decryptor = new UOFileDecryptor("your_passphrase");

// Load encrypted file
byte[] artData = decryptor.LoadFile("art.mul.enc");

// Or use stream (transparent to existing code)
using (var stream = new UOFileStream("art.mul.enc", decryptor))
using (var reader = new BinaryReader(stream))
{
    // Read data normally
    byte[] header = reader.ReadBytes(64);
}
```

### Integration Steps

1. **Replace file opening code:**

   Before:
   ```csharp
   FileStream fs = File.OpenRead("art.mul");
   ```

   After:
   ```csharp
   UOFileStream fs = new UOFileStream("art.mul.enc", decryptor);
   ```

2. **Fallback to plain files:**

   ```csharp
   string filePath = "art.mul";
   if (File.Exists(filePath + ".enc"))
       filePath = filePath + ".enc";

   var stream = new UOFileStream(filePath, decryptor);
   ```

3. **No other changes needed** - rest of your code works as-is!

---

## Best Practices

### 1. Passphrase Security

**DO:**
- Use strong, unique passphrases (20+ characters)
- Mix uppercase, lowercase, numbers, symbols
- Store passphrase securely (password manager, encrypted config)
- Use different passphrases for different environments (dev/prod)

**DON'T:**
- Hardcode passphrase in client code
- Use simple passwords ("password123")
- Commit passphrase to version control
- Share passphrase in plain text

**Example strong passphrase:**
```
Correct-Horse-Battery-Staple-2025!
```

### 2. Key Management

**Option A: Environment Variable**

```bash
# Linux/Mac
export UO_DECRYPT_KEY="your_passphrase"
python3 your_client.py

# Windows
set UO_DECRYPT_KEY=your_passphrase
python your_client.py
```

**Option B: Config File (encrypted)**

```python
import json
from pathlib import Path

# Store encrypted config
config = {
    "passphrase": "your_passphrase"
}

# In production, encrypt this file too!
with open("config.json", "w") as f:
    json.dump(config, f)
```

**Option C: Request from server**

Client requests decryption key from authenticated server session.

### 3. Deployment Strategy

**Development Environment:**
- Keep unencrypted files for testing
- Use test passphrase

**Production Environment:**
- Encrypt all files
- Remove unencrypted originals
- Strong passphrase
- Client validates authenticity before getting key

### 4. Backup Strategy

**Before encrypting:**

```bash
# Full backup
tar -czf uo_backup_$(date +%Y%m%d).tar.gz *.mul *.uop *.idx

# Verify backup
tar -tzf uo_backup_$(date +%Y%m%d).tar.gz | head
```

**Store backups:**
- Off-site location
- Encrypted storage
- Multiple copies (3-2-1 rule)

### 5. Performance Optimization

**Client-side caching:**

```python
# Enable caching (default)
loader = UOFileLoader("passphrase", cache_enabled=True)

# Preload frequently used files
loader.preload_files([
    "art.mul.enc",
    "gumpart.mul.enc",
    "tiledata.mul.enc"
])
```

**Lazy loading:**

```python
# Only decrypt when needed
class LazyLoader:
    def __init__(self):
        self.loader = None

    def get_data(self, filename):
        if self.loader is None:
            self.loader = UOFileLoader(os.getenv("UO_KEY"))
        return self.loader.load_file(filename)
```

---

## Troubleshooting

### Problem: "Decryption failed - wrong passphrase"

**Cause:** Incorrect passphrase or corrupted file

**Solution:**
1. Verify passphrase is exactly the same
2. Check for typos or extra spaces
3. Ensure file wasn't modified after encryption
4. Try re-encrypting the file

### Problem: "pycryptodome not installed"

**Solution:**
```bash
pip install pycryptodome

# If using Python 2 and 3:
python3 -m pip install pycryptodome
```

### Problem: Performance issues

**Solutions:**
1. Enable caching: `UOFileLoader(passphrase, cache_enabled=True)`
2. Preload files at startup
3. Use SSD storage
4. Decrypt to RAM disk if available

### Problem: Files too large

**Solution:**
For very large files (>100MB), consider chunk-based encryption:

```python
# Future enhancement - not yet implemented
# Could add streaming encryption/decryption for large files
```

### Problem: Integration with existing code

**Solution:**
Use wrapper classes that maintain same interface:

```python
class CompatibleFileReader:
    def __init__(self, path, decryptor):
        self.data = decryptor.load_file(path)
        self.pos = 0

    def read(self, size):
        chunk = self.data[self.pos:self.pos+size]
        self.pos += size
        return chunk
```

---

## Advanced Topics

### Multi-key System

Use different keys for different file types:

```python
keys = {
    "art": "art_passphrase_123",
    "gumps": "gump_passphrase_456",
    "anims": "anim_passphrase_789"
}

loaders = {
    name: UOFileLoader(passphrase)
    for name, passphrase in keys.items()
}

# Load with appropriate key
art_data = loaders["art"].load_file("art.mul.enc")
```

### Server-side Validation

Validate client before providing decryption key:

```python
def get_decryption_key(client_id, client_secret):
    # Validate client
    if not validate_client(client_id, client_secret):
        raise PermissionError("Invalid client")

    # Return key only to authorized clients
    return os.getenv("UO_MASTER_KEY")
```

### Hybrid Protection

Combine encryption with other protection methods:

1. **Encryption**: Protect files at rest
2. **Obfuscation**: Make reverse engineering harder
3. **Anti-debug**: Detect debugging attempts
4. **Code signing**: Verify client integrity
5. **Network encryption**: Protect data in transit

---

## Security Considerations

### What This Protects Against

✅ File extraction and analysis
✅ Casual data mining
✅ Automated bot file reading
✅ Unauthorized server setup with your files
✅ File tampering (GCM authentication)

### What This Doesn't Protect Against

❌ Determined reverse engineers (memory dumps)
❌ Compromised client with key access
❌ Physical access to running system
❌ Social engineering for passphrase

### Recommendations

1. **Defense in depth**: Use multiple protection layers
2. **Update regularly**: Change passphrases periodically
3. **Monitor access**: Log decryption attempts
4. **Legal protection**: Use licensing and terms of service
5. **Community**: Build engaged community (best protection)

---

## Additional Resources

### File Format Documentation

- [UO File Formats](https://docs.polserver.com/pol099/fileformats.html)
- [MUL File Structure](https://github.com/polserver/polserver/wiki/MUL-Files)

### Encryption References

- [AES-GCM Specification](https://csrc.nist.gov/publications/detail/sp/800-38d/final)
- [PBKDF2 Specification](https://www.rfc-editor.org/rfc/rfc2898)
- [Cryptography Best Practices](https://www.owasp.org/index.php/Cryptographic_Storage_Cheat_Sheet)

---

## Support

For issues or questions:

1. Check this guide first
2. Review error messages carefully
3. Test with a single small file first
4. Verify passphrase is correct
5. Check Python and dependency versions

---

## License

This encryption system is provided as-is for protecting your UO game files.
Use responsibly and in compliance with all applicable laws and licenses.

---

## Changelog

**Version 1.0** (2025-12-11)
- Initial release
- AES-256-GCM encryption
- Python encryption tool
- Python file loader
- C# integration example
- Comprehensive documentation
