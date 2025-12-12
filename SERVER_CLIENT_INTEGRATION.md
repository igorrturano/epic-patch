# Server-Client Integration Guide for Encrypted UO Files

This guide explains how to integrate encrypted UO files into your Ultima Online server-client architecture.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Integration Strategies](#integration-strategies)
3. [Client-Side Integration](#client-side-integration)
4. [Server-Side Integration](#server-side-integration)
5. [Key Distribution](#key-distribution)
6. [Deployment Workflow](#deployment-workflow)
7. [Security Considerations](#security-considerations)

---

## Architecture Overview

### Typical UO Server-Client Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENT SIDE                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │ UO Client    │ ──── │ Data Files   │ (art.mul, etc.)     │
│  │ (ClassicUO,  │      │ (.mul, .uop) │                     │
│  │  Razor, etc) │      └──────────────┘                     │
│  └──────────────┘                                            │
│         │                                                     │
│         │ Network Protocol (UO packets)                      │
│         ▼                                                     │
└─────────────────────────────────────────────────────────────┘
         │
         │ TCP/IP Connection (Port 2593, etc.)
         │
┌─────────────────────────────────────────────────────────────┐
│                         SERVER SIDE                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │ UO Server    │ ──── │ Data Files   │ (map files, etc.)   │
│  │ (RunUO,      │      │ (.mul, .uop) │                     │
│  │  ServUO)     │      └──────────────┘                     │
│  └──────────────┘                                            │
│         │                                                     │
│         ▼                                                     │
│  ┌──────────────┐                                            │
│  │ World Data   │ (saved games, accounts, etc.)             │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

### Where Encryption Fits

**Client Files** (PRIMARY TARGET):
- Art files (art.mul, artLegacyMUL.uop)
- Gump files (gumpart.mul, gumpartLegacyMUL.uop)
- Animation files (anim.mul, anim2.mul, anim3.mul)
- Multi files (multi.mul, multi.idx)
- Map files (map0.mul, statics, staidx)
- Sound files (sound.mul)

**Server Files** (OPTIONAL):
- Map files (if custom)
- Multi definitions
- Tiledata
- Custom content files

---

## Integration Strategies

### Strategy 1: Client-Only Encryption (Recommended for Patches)

**Use Case**: Protecting custom patch files for your shard

```
Client: Encrypted patch files → Decrypt in memory → Use normally
Server: Standard files (no changes needed)
```

**Pros**:
- No server modifications needed
- Protects custom art/gumps/animations
- Easy to deploy
- Works with any UO server

**Cons**:
- Server files remain unencrypted
- Doesn't protect server-side data

### Strategy 2: Full Encryption (Maximum Protection)

**Use Case**: Protecting all game assets

```
Client: Encrypted files → Decrypt in memory
Server: Encrypted files → Decrypt in memory
```

**Pros**:
- Maximum protection
- Prevents extraction from both client and server
- Protects entire game experience

**Cons**:
- Requires modifying both client and server
- More complex deployment
- Performance overhead

### Strategy 3: Hybrid Approach (Best Balance)

**Use Case**: Protect valuable assets, leave standard content alone

```
Client:
  - Standard UO files: Unencrypted
  - Custom patch files: Encrypted

Server:
  - Standard files: Unencrypted
  - Custom content: Encrypted
```

**Pros**:
- Protects custom content only
- Minimal performance impact
- Easier to maintain
- Compatible with standard tools

**Cons**:
- Standard content remains accessible

---

## Client-Side Integration

### For Python-Based Clients/Tools

If you're using Python for client-side tools or a custom client:

```python
from uo_file_loader import UOFileManager

class UOClient:
    def __init__(self, data_path, passphrase=None):
        # Initialize file manager
        self.file_manager = UOFileManager(
            passphrase=passphrase or self._get_passphrase(),
            search_paths=[
                data_path,                    # Main game files
                f"{data_path}/patch",         # Patch directory
                f"{data_path}/custom"         # Custom content
            ]
        )

    def _get_passphrase(self):
        """Get decryption passphrase from secure source"""
        # Option 1: Environment variable
        import os
        return os.getenv('UO_CLIENT_KEY')

        # Option 2: Config file
        # return self._load_from_config()

        # Option 3: Server authentication
        # return self._request_from_server()

    def load_art_file(self):
        """Load art.mul with transparent decryption"""
        # This automatically handles encrypted or plain files
        data = self.file_manager.load("art.mul")
        return self._parse_art_data(data)

    def load_gump_file(self):
        """Load gump files"""
        gump_data = self.file_manager.load("gumpart.mul")
        gump_idx = self.file_manager.load("gumpidx.mul")
        return self._parse_gump_data(gump_data, gump_idx)

    def _parse_art_data(self, data):
        """Parse art.mul format"""
        # Your existing parsing logic
        pass

    def _parse_gump_data(self, data, idx):
        """Parse gump data"""
        # Your existing parsing logic
        pass


# Usage
if __name__ == "__main__":
    client = UOClient(
        data_path="/path/to/uo/data",
        passphrase="YourSecretPassphrase"
    )

    # Load files normally - encryption is transparent
    art = client.load_art_file()
    gumps = client.load_gump_file()
```

### For C# Clients (ClassicUO, Razor, etc.)

See the detailed example in `client_integration_example.cs`, but here's a quick integration:

#### Step 1: Add the UOCrypto Class

Copy the classes from `client_integration_example.cs` into your project:
- `UOFileDecryptor`
- `UOFileStream`

#### Step 2: Modify File Loading Code

**Before (Standard File Loading):**
```csharp
public class ArtLoader
{
    private FileStream _artStream;
    private BinaryReader _artReader;

    public void Load(string dataPath)
    {
        string artPath = Path.Combine(dataPath, "art.mul");
        _artStream = new FileStream(artPath, FileMode.Open, FileAccess.Read);
        _artReader = new BinaryReader(_artStream);
    }
}
```

**After (With Encryption Support):**
```csharp
public class ArtLoader
{
    private Stream _artStream;
    private BinaryReader _artReader;
    private UOFileDecryptor _decryptor;

    public ArtLoader(string passphrase)
    {
        _decryptor = new UOFileDecryptor(passphrase);
    }

    public void Load(string dataPath)
    {
        string artPath = Path.Combine(dataPath, "art.mul");

        // Try encrypted version first
        if (File.Exists(artPath + ".enc"))
        {
            artPath = artPath + ".enc";
        }

        // UOFileStream transparently handles both encrypted and plain files
        _artStream = new UOFileStream(artPath, _decryptor);
        _artReader = new BinaryReader(_artStream);

        // Rest of your code remains unchanged!
    }
}
```

#### Step 3: Initialize with Passphrase

**Option A: From Environment Variable**
```csharp
static void Main(string[] args)
{
    string passphrase = Environment.GetEnvironmentVariable("UO_CLIENT_KEY");

    if (string.IsNullOrEmpty(passphrase))
    {
        Console.WriteLine("ERROR: UO_CLIENT_KEY not set!");
        return;
    }

    var client = new UOClient(passphrase);
    client.Start();
}
```

**Option B: From Config File**
```csharp
public class Config
{
    public static string GetPassphrase()
    {
        // Read from encrypted config
        string configPath = "client.config";

        if (File.Exists(configPath))
        {
            var config = JsonSerializer.Deserialize<ClientConfig>(
                File.ReadAllText(configPath)
            );
            return config.DecryptionKey;
        }

        throw new Exception("Config file not found!");
    }
}
```

**Option C: From Server Authentication**
```csharp
public class ServerAuth
{
    public static async Task<string> GetPassphrase(string username, string password)
    {
        using (var client = new HttpClient())
        {
            var response = await client.PostAsync(
                "https://your-server.com/api/auth",
                new StringContent(JsonSerializer.Serialize(new
                {
                    username,
                    password
                }))
            );

            if (response.IsSuccessStatusCode)
            {
                var result = await response.Content.ReadAsStringAsync();
                var auth = JsonSerializer.Deserialize<AuthResponse>(result);
                return auth.DecryptionKey;
            }

            throw new Exception("Authentication failed!");
        }
    }
}
```

---

## Server-Side Integration

### For Python Servers (POL, Custom)

```python
from uo_file_loader import UOFileManager

class UOServer:
    def __init__(self, data_path):
        self.file_manager = UOFileManager(
            passphrase=self._get_server_passphrase(),
            search_paths=[data_path]
        )

        # Load required data files
        self.load_server_data()

    def _get_server_passphrase(self):
        """Get server-side decryption key"""
        import os
        return os.getenv('UO_SERVER_KEY', 'default_server_key')

    def load_server_data(self):
        """Load all required server data files"""
        # Load map data
        self.map_data = self.file_manager.load("map0.mul")
        self.statics_data = self.file_manager.load("statics0.mul")
        self.staidx_data = self.file_manager.load("staidx0.mul")

        # Load multi data
        self.multi_data = self.file_manager.load("multi.mul")
        self.multi_idx = self.file_manager.load("multi.idx")

        # Load tile data
        self.tile_data = self.file_manager.load("tiledata.mul")

        print("✓ All server data loaded and decrypted")

    def get_tile_info(self, tile_id):
        """Get tile information"""
        # Your tile parsing logic using self.tile_data
        pass

    def get_static_items(self, x, y, map_id=0):
        """Get static items at location"""
        # Your statics parsing logic
        pass
```

### For C# Servers (RunUO, ServUO)

#### Step 1: Add Decryption Support to TileData.cs

**Find the TileData loading code** (usually in `TileData.cs`):

```csharp
// Before
public static void Initialize()
{
    string filePath = Core.FindDataFile("tiledata.mul");

    using (FileStream fs = new FileStream(filePath, FileMode.Open, FileAccess.Read))
    using (BinaryReader reader = new BinaryReader(fs))
    {
        // Parse tiledata
        ReadLandTileData(reader);
        ReadItemTileData(reader);
    }
}
```

**After (with encryption support):**
```csharp
private static UOFileDecryptor _decryptor;

public static void Initialize(string passphrase)
{
    _decryptor = new UOFileDecryptor(passphrase);

    string filePath = Core.FindDataFile("tiledata.mul");

    // Check for encrypted version
    if (File.Exists(filePath + ".enc"))
        filePath = filePath + ".enc";

    using (Stream stream = new UOFileStream(filePath, _decryptor))
    using (BinaryReader reader = new BinaryReader(stream))
    {
        // Parse tiledata - rest unchanged
        ReadLandTileData(reader);
        ReadItemTileData(reader);
    }
}
```

#### Step 2: Modify Map.cs for Encrypted Maps

```csharp
public Map(int mapID, int mapIndex, int fileIndex, int width, int height)
{
    // ... existing initialization code ...

    // Load encrypted map files
    string dataPath = Core.DataDirectories[0];

    string mapPath = Path.Combine(dataPath, $"map{fileIndex}.mul");
    string staticsPath = Path.Combine(dataPath, $"statics{fileIndex}.mul");
    string indexPath = Path.Combine(dataPath, $"staidx{fileIndex}.mul");

    // Check for encrypted versions
    if (File.Exists(mapPath + ".enc"))
        mapPath = mapPath + ".enc";
    if (File.Exists(staticsPath + ".enc"))
        staticsPath = staticsPath + ".enc";
    if (File.Exists(indexPath + ".enc"))
        indexPath = indexPath + ".enc";

    // Load using decryptor
    m_MapStream = new UOFileStream(mapPath, _decryptor);
    m_StaticsStream = new UOFileStream(staticsPath, _decryptor);
    m_IndexStream = new UOFileStream(indexPath, _decryptor);
}
```

#### Step 3: Initialize Server with Passphrase

**In Main.cs or Core.cs:**
```csharp
public static void Main(string[] args)
{
    // Get passphrase from environment or config
    string passphrase = Environment.GetEnvironmentVariable("UO_SERVER_KEY");

    if (string.IsNullOrEmpty(passphrase))
    {
        Console.WriteLine("ERROR: UO_SERVER_KEY environment variable not set!");
        Console.WriteLine("Set it with: export UO_SERVER_KEY='your_passphrase'");
        return;
    }

    // Initialize crypto
    UOFileDecryptor.Initialize(passphrase);

    // Continue with normal server startup
    TileData.Initialize(passphrase);
    Map.Initialize();

    // ... rest of server initialization ...
}
```

---

## Key Distribution

### Strategy 1: Environment Variables (Development)

**Client:**
```bash
# Linux/Mac
export UO_CLIENT_KEY="dev_passphrase_123"
./uo_client

# Windows
set UO_CLIENT_KEY=dev_passphrase_123
uo_client.exe
```

**Server:**
```bash
export UO_SERVER_KEY="dev_passphrase_123"
./runuo
```

### Strategy 2: Configuration Files (Local Deployment)

**Client config.json:**
```json
{
  "dataPath": "/path/to/uo/data",
  "decryptionKey": "YourClientPassphrase123!",
  "serverAddress": "play.yourshard.com",
  "serverPort": 2593
}
```

**Server config:**
```bash
# In server startup script
#!/bin/bash
export UO_SERVER_KEY=$(cat /secure/location/server.key)
cd /uo/server
./runuo
```

### Strategy 3: Server Authentication (Recommended for Production)

**Flow:**
```
1. Client launches
2. User enters credentials
3. Client authenticates with web server
4. Web server validates and returns decryption key
5. Client uses key to decrypt files
6. Client connects to game server
```

**Implementation:**

**Client-side:**
```python
import requests

def authenticate_and_get_key(username, password):
    """Get decryption key from auth server"""
    response = requests.post(
        'https://auth.yourshard.com/api/get-key',
        json={
            'username': username,
            'password': password,
            'hwid': get_hardware_id()  # Optional: hardware fingerprinting
        }
    )

    if response.status_code == 200:
        data = response.json()
        return data['decryption_key']
    else:
        raise Exception("Authentication failed")

# Usage
username = input("Username: ")
password = getpass.getpass("Password: ")

decryption_key = authenticate_and_get_key(username, password)

# Now use the key
client = UOClient(passphrase=decryption_key)
```

**Server-side (Flask example):**
```python
from flask import Flask, request, jsonify
import hashlib

app = Flask(__name__)

# This should be in a database
VALID_USERS = {
    'user1': {
        'password_hash': hashlib.sha256(b'password123').hexdigest(),
        'decryption_key': 'user1_specific_key_abc123'
    }
}

@app.route('/api/get-key', methods=['POST'])
def get_decryption_key():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Validate credentials
    if username in VALID_USERS:
        user = VALID_USERS[username]
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        if password_hash == user['password_hash']:
            # Return decryption key
            return jsonify({
                'success': True,
                'decryption_key': user['decryption_key']
            })

    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

if __name__ == '__main__':
    app.run(ssl_context='adhoc')  # Use proper SSL in production
```

### Strategy 4: License Key System

Tie decryption to license keys:

```python
def validate_license_and_get_key(license_key):
    """Validate license and return decryption key"""
    # License format: XXXX-YYYY-ZZZZ-WWWW

    if validate_license_format(license_key):
        # Derive decryption key from license
        decryption_key = derive_key_from_license(license_key)
        return decryption_key

    raise Exception("Invalid license key")

def derive_key_from_license(license_key):
    """Derive decryption key from license key"""
    import hashlib

    # Use PBKDF2 to derive key from license
    salt = b"your_app_specific_salt"
    key = hashlib.pbkdf2_hmac(
        'sha256',
        license_key.encode(),
        salt,
        100000
    )

    # Convert to passphrase format
    return key.hex()
```

---

## Deployment Workflow

### Complete Deployment Process

#### Phase 1: Preparation

```bash
# 1. Backup everything
tar -czf uo_files_backup_$(date +%Y%m%d).tar.gz \
    *.mul *.uop *.idx

# 2. Test encryption on copies first
mkdir test_encryption
cp *.mul test_encryption/
cd test_encryption

python3 ../uo_crypto.py encrypt-batch . \
    --passphrase "TestPassword" \
    --recursive

# 3. Verify decryption works
python3 -c "
from uo_file_loader import UOFileLoader
loader = UOFileLoader('TestPassword')
data = loader.load_file('art.mul.enc')
print(f'✓ Test successful: {len(data)} bytes loaded')
"
```

#### Phase 2: Client Deployment

```bash
# 1. Encrypt client patch files
cd /path/to/client/patch

python3 uo_crypto.py encrypt-batch . \
    --passphrase "ClientPatchKey2025!" \
    --recursive \
    --extensions .mul .uop .idx

# 2. Create client launcher script
cat > launch_client.sh <<'EOF'
#!/bin/bash
export UO_CLIENT_KEY="ClientPatchKey2025!"
cd /path/to/client
./uo_client
EOF

chmod +x launch_client.sh

# 3. Distribute encrypted files + modified client to users
```

#### Phase 3: Server Deployment

```bash
# 1. Encrypt server data files (if needed)
cd /path/to/server/data

python3 uo_crypto.py encrypt-batch . \
    --passphrase "ServerDataKey2025!" \
    --recursive

# 2. Create server startup script
cat > start_server.sh <<'EOF'
#!/bin/bash
export UO_SERVER_KEY="ServerDataKey2025!"
cd /path/to/server
./runuo
EOF

chmod +x start_server.sh

# 3. Start server
./start_server.sh
```

#### Phase 4: Testing

```bash
# 1. Test client can load encrypted files
./launch_client.sh

# 2. Test server can load encrypted files
./start_server.sh

# 3. Test client-server connection
# Connect client to server and verify normal gameplay

# 4. Monitor for errors
tail -f server.log
tail -f client.log
```

---

## Security Considerations

### 1. Passphrase Security

**DO:**
- Use different passphrases for client and server
- Use different passphrases for dev/test/prod
- Store passphrases in secure locations (env vars, secret managers)
- Rotate passphrases periodically

**DON'T:**
- Hardcode passphrases in client/server code
- Commit passphrases to version control
- Use the same passphrase for everything
- Share passphrases in plain text

### 2. Key Distribution

**Options by Security Level:**

| Method | Security | Complexity | Use Case |
|--------|----------|------------|----------|
| Environment Variables | Low | Low | Development |
| Config Files | Medium | Low | Local deployment |
| Server Authentication | High | Medium | Production online |
| License Keys | High | High | Commercial |
| Hardware Tokens | Very High | Very High | Enterprise |

### 3. Defense in Depth

Encryption is one layer. Also consider:

```
Layer 1: File Encryption (AES-256-GCM) ←  You are here
Layer 2: Code Obfuscation
Layer 3: Anti-debugging
Layer 4: Integrity Checking
Layer 5: License Validation
Layer 6: Legal Protection (EULA)
```

### 4. Performance Considerations

**Optimization Tips:**

1. **Cache Decrypted Files:**
```python
loader = UOFileLoader(passphrase, cache_enabled=True)
# First load: Decrypt from disk
data1 = loader.load_file("art.mul.enc")  # Slow
# Second load: From cache
data2 = loader.load_file("art.mul.enc")  # Fast!
```

2. **Preload at Startup:**
```python
# Preload all files during client initialization
loader.preload_files([
    "art.mul.enc",
    "gumpart.mul.enc",
    "tiledata.mul.enc"
])
# Now all files are in memory cache
```

3. **Lazy Loading:**
```python
# Don't decrypt until actually needed
art_loader = lambda: loader.load_file("art.mul.enc")
# Only decrypt when called
art_data = art_loader()
```

---

## Troubleshooting

### Common Issues

**1. "Decryption failed - wrong passphrase"**
- Verify environment variable is set correctly
- Check for typos in passphrase
- Ensure same passphrase used for encryption/decryption

**2. "File not found"**
- Check search paths are correct
- Verify .enc files exist
- Check file permissions

**3. "Performance issues"**
- Enable caching
- Preload files at startup
- Consider SSD storage
- Profile to find bottlenecks

**4. "Client won't connect to server"**
- File encryption doesn't affect network protocol
- Check firewall settings
- Verify server is running
- Check server address/port

---

## Next Steps

1. **Choose your integration strategy** (Client-only, Server-only, or Full)
2. **Select key distribution method** (Environment, Config, or Server auth)
3. **Test on development environment** first
4. **Deploy to production** following the workflow above
5. **Monitor and iterate** based on user feedback

For specific implementation help, refer to:
- `uo_file_loader.py` - Python integration
- `client_integration_example.cs` - C# integration
- `ENCRYPTION_GUIDE.md` - Complete documentation

---

**Questions?** Review the code examples above or check the troubleshooting section.
