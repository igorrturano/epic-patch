# Deployment Guide: Server-Client Integration

Step-by-step guide for deploying encrypted UO files in your server-client environment.

## Quick Start Scenarios

### Scenario 1: Encrypt Client Patch Files Only

**Best for**: Protecting custom patch content while keeping server unchanged

```bash
# Step 1: Encrypt your patch files
cd /path/to/client/patch
python3 uo_crypto.py encrypt-batch . \
    --passphrase "MyPatchKey2025!" \
    --recursive

# Step 2: Test loading
python3 example_client.py \
    --data-path /path/to/client/patch \
    --passphrase "MyPatchKey2025!" \
    --test-load

# Step 3: Distribute to users
# Copy encrypted .enc files + modified client
```

### Scenario 2: Full Server-Client Encryption

**Best for**: Maximum protection of all game assets

```bash
# Step 1: Encrypt client files
cd /client/data
python3 uo_crypto.py encrypt-batch . -p "ClientKey2025!" -r

# Step 2: Encrypt server files
cd /server/data
python3 uo_crypto.py encrypt-batch . -p "ServerKey2025!" -r

# Step 3: Deploy
# See detailed steps below
```

### Scenario 3: Server Authentication

**Best for**: Online shards with user accounts

```bash
# Step 1: Start authentication server
python3 example_auth_server.py --create-test-users

# Step 2: Encrypt files
python3 uo_crypto.py encrypt-batch . -p "ServerProvidedKey!" -r

# Step 3: Launch client with auth
python3 example_client.py \
    --auth-server http://localhost:5000 \
    --data-path /path/to/data
```

---

## Detailed Deployment Steps

### Phase 1: Preparation

#### 1.1 Backup Everything

```bash
#!/bin/bash
# backup_uo_files.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups"

mkdir -p "$BACKUP_DIR"

# Backup client files
echo "Backing up client files..."
tar -czf "$BACKUP_DIR/client_backup_$DATE.tar.gz" \
    /path/to/client/data/*.mul \
    /path/to/client/data/*.uop \
    /path/to/client/data/*.idx

# Backup server files
echo "Backing up server files..."
tar -czf "$BACKUP_DIR/server_backup_$DATE.tar.gz" \
    /path/to/server/data/*.mul \
    /path/to/server/data/*.uop \
    /path/to/server/data/*.idx

echo "✓ Backups created in $BACKUP_DIR/"
ls -lh "$BACKUP_DIR/"
```

#### 1.2 Test on Development Environment

```bash
# Create test environment
mkdir -p ~/uo_test/client ~/uo_test/server

# Copy files
cp /path/to/client/data/*.mul ~/uo_test/client/
cp /path/to/server/data/*.mul ~/uo_test/server/

# Test encryption
cd ~/uo_test/client
python3 uo_crypto.py encrypt art.mul -p "TestKey123"
python3 uo_crypto.py decrypt art.mul.enc -p "TestKey123"

# Verify files match
diff art.mul art.mul.dec && echo "✓ Test successful"
```

---

### Phase 2: Client Deployment

#### 2.1 Choose Integration Method

**Option A: Standalone Python Client**

```bash
# Use the example client
python3 example_client.py \
    --data-path /path/to/uo/data \
    --passphrase "YourKey" \
    --test-load
```

**Option B: Modify Existing C# Client**

See `client_integration_example.cs` for complete code, then:

```csharp
// In your Main.cs or Program.cs
public static void Main(string[] args)
{
    // Get passphrase
    string passphrase = GetPassphrase();

    // Initialize decryption
    UOFileDecryptor.Initialize(passphrase);

    // Rest of your client code...
}
```

**Option C: Wrapper Script**

```bash
#!/bin/bash
# launch_client.sh

# Set passphrase from environment
export UO_CLIENT_KEY="YourClientPassphrase2025!"

# Launch client
cd /path/to/client
./uo_client

# Or with Python client:
# python3 example_client.py --data-path ./data
```

#### 2.2 Encrypt Client Files

```bash
cd /path/to/client/data

# Encrypt all UO files
python3 uo_crypto.py encrypt-batch . \
    --passphrase "ClientKey2025!" \
    --recursive

# Optional: Remove originals (CAREFUL!)
# Add --remove-original flag only after testing!
```

#### 2.3 Create Client Distribution Package

```bash
# Package encrypted files + client executable
mkdir -p uo_client_package

# Copy encrypted files
cp *.enc uo_client_package/

# Copy modified client
cp uo_client uo_client_package/
cp launch_client.sh uo_client_package/

# Copy dependencies
cp uo_file_loader.py uo_client_package/

# Create archive
tar -czf uo_client_v1.0.tar.gz uo_client_package/

# Distribute to users
```

---

### Phase 3: Server Deployment

#### 3.1 Encrypt Server Files

```bash
cd /path/to/server/data

# Encrypt server data files
python3 uo_crypto.py encrypt-batch . \
    --passphrase "ServerKey2025!" \
    --recursive \
    --extensions .mul .idx
```

#### 3.2 Create Server Startup Script

```bash
#!/bin/bash
# start_uo_server.sh

# Server configuration
SERVER_DIR="/path/to/server"
DATA_DIR="$SERVER_DIR/data"
LOG_FILE="$SERVER_DIR/logs/server_$(date +%Y%m%d).log"

# Set decryption key
export UO_SERVER_KEY="ServerKey2025!"

# Start server
cd "$SERVER_DIR"
./runuo 2>&1 | tee "$LOG_FILE"

# Or for ServUO:
# mono ServUO.exe 2>&1 | tee "$LOG_FILE"
```

#### 3.3 Integrate with Server Code

**For RunUO/ServUO (C#):**

```csharp
// In Server/Main.cs
public static void Main(string[] args)
{
    // Get server decryption key
    string serverKey = Environment.GetEnvironmentVariable("UO_SERVER_KEY");

    if (string.IsNullOrEmpty(serverKey))
    {
        Console.WriteLine("ERROR: UO_SERVER_KEY not set!");
        return;
    }

    // Initialize crypto
    UOFileDecryptor.Initialize(serverKey);

    // Continue with normal server initialization
    // Your existing server startup code...
}
```

**For Python-based servers:**

```python
# In server.py
from uo_file_loader import UOFileManager
import os

class UOServer:
    def __init__(self):
        # Get decryption key
        server_key = os.getenv('UO_SERVER_KEY')

        # Initialize file manager
        self.files = UOFileManager(
            passphrase=server_key,
            search_paths=['./data']
        )

        # Load server data
        self.load_data()

    def load_data(self):
        self.map_data = self.files.load('map0.mul')
        self.statics = self.files.load('statics0.mul')
        # etc...
```

---

### Phase 4: Authentication Server (Optional)

#### 4.1 Setup Authentication Server

```bash
# Install dependencies
pip install flask

# Create database and test users
python3 example_auth_server.py --create-test-users

# Start server
python3 example_auth_server.py --host 0.0.0.0 --port 5000
```

#### 4.2 Add Custom Users

```bash
# Via command line
python3 example_auth_server.py --add-user username password

# Via API
curl -X POST http://localhost:5000/api/register \
    -H "Content-Type: application/json" \
    -d '{"username":"newuser","password":"pass123"}'
```

#### 4.3 Configure Client for Auth

```bash
# Launch client with authentication
python3 example_client.py \
    --data-path /path/to/data \
    --auth-server http://your-auth-server.com:5000
```

---

### Phase 5: Testing

#### 5.1 Test Client Independently

```bash
# Test file loading
python3 example_client.py \
    --data-path /path/to/client/data \
    --passphrase "ClientKey2025!" \
    --test-load

# Expected output:
# ✓ Loaded art.mul: 12,345,678 bytes
# ✓ Loaded gumpart.mul: 1,234,567 bytes
# etc...
```

#### 5.2 Test Server Independently

```bash
# Start server with logging
./start_uo_server.sh

# Check logs
tail -f logs/server_*.log

# Look for:
# ✓ Loaded map data
# ✓ Server initialized
```

#### 5.3 Test Client-Server Connection

```bash
# 1. Start server
./start_uo_server.sh

# 2. In another terminal, start client
./launch_client.sh

# 3. Connect client to server
# Use normal UO client connection process
# Server: localhost (or your server IP)
# Port: 2593 (or your port)

# 4. Test gameplay
# - Login
# - Move character
# - View items/gumps
# - Verify everything works normally
```

#### 5.4 Test Authentication Flow

```bash
# 1. Start auth server
python3 example_auth_server.py

# 2. Start game server
./start_uo_server.sh

# 3. Launch client with auth
python3 example_client.py \
    --auth-server http://localhost:5000 \
    --data-path ./data

# 4. Login with test credentials
# Username: user1
# Password: password1

# Should see:
# ✓ Authentication successful!
# ✓ Loaded decryption key
# ✓ Files loaded
```

---

### Phase 6: Production Deployment

#### 6.1 Prepare Production Environment

```bash
# Set production environment variables
cat > /etc/environment.d/uo_server.conf <<EOF
UO_SERVER_KEY=ProductionServerKey_2025_SecureAndLong!
EOF

# Set client environment (on user machines)
echo 'export UO_CLIENT_KEY="ProductionClientKey_2025!"' >> ~/.bashrc
```

#### 6.2 Deploy with Systemd (Linux Server)

```ini
# /etc/systemd/system/uo-server.service
[Unit]
Description=UO Game Server
After=network.target

[Service]
Type=simple
User=uoserver
Group=uoserver
WorkingDirectory=/opt/uo-server
Environment="UO_SERVER_KEY=YourProductionKey2025!"
ExecStart=/opt/uo-server/runuo
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable uo-server
sudo systemctl start uo-server

# Check status
sudo systemctl status uo-server
sudo journalctl -u uo-server -f
```

#### 6.3 Deploy Auth Server with Nginx

```nginx
# /etc/nginx/sites-available/uo-auth
server {
    listen 443 ssl;
    server_name auth.yourshard.com;

    ssl_certificate /etc/letsencrypt/live/auth.yourshard.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/auth.yourshard.com/privkey.pem;

    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/uo-auth /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Security Checklist

### Pre-Deployment

- [ ] All files backed up
- [ ] Tested encryption/decryption on test files
- [ ] Tested client can load encrypted files
- [ ] Tested server can load encrypted files
- [ ] Tested client-server connection
- [ ] Strong passphrases generated (20+ characters)
- [ ] Passphrases documented in secure location
- [ ] Different keys for dev/prod environments

### Production

- [ ] Passphrases NOT hardcoded in source
- [ ] Passphrases NOT in version control
- [ ] Environment variables set correctly
- [ ] SSL/TLS enabled for auth server
- [ ] Firewall rules configured
- [ ] Logging enabled
- [ ] Monitoring configured
- [ ] Backup strategy in place

### Post-Deployment

- [ ] Monitor server logs for errors
- [ ] Monitor auth server for failed logins
- [ ] Test user can connect and play
- [ ] Verify encrypted files not accessible directly
- [ ] Performance acceptable
- [ ] Plan for key rotation (6-12 months)

---

## Troubleshooting

### Client Issues

**Problem**: Client shows "Decryption failed"

```bash
# Check passphrase
echo $UO_CLIENT_KEY

# Verify file is encrypted
python3 -c "
from uo_file_loader import UOFileLoader
loader = UOFileLoader('YourKey')
print(loader.is_encrypted('art.mul.enc'))
"

# Test manual decryption
python3 uo_crypto.py decrypt art.mul.enc -p "YourKey"
```

**Problem**: Client can't find files

```python
# Check search paths
from uo_file_loader import UOFileManager

manager = UOFileManager(
    passphrase="YourKey",
    search_paths=["/path/to/data"]
)

# Try to find file
path = manager.find_file("art.mul")
print(f"Found at: {path}")
```

### Server Issues

**Problem**: Server won't start

```bash
# Check environment variable
echo $UO_SERVER_KEY

# Check file permissions
ls -la /path/to/server/data/*.enc

# Check server logs
tail -100 /path/to/server/logs/server.log
```

**Problem**: Server performance issues

```bash
# Check if caching is enabled (in code)
# Enable preloading of frequently accessed files
# Monitor memory usage
free -h
top -p $(pgrep runuo)
```

### Authentication Issues

**Problem**: Auth server not responding

```bash
# Check if running
ps aux | grep auth_server

# Check port
netstat -tlnp | grep 5000

# Test health endpoint
curl http://localhost:5000/api/health
```

**Problem**: Authentication fails

```bash
# Check database
sqlite3 auth.db "SELECT username FROM users;"

# Test manually
curl -X POST http://localhost:5000/api/get-key \
    -H "Content-Type: application/json" \
    -d '{"username":"user1","password":"password1"}'
```

---

## Rollback Procedure

If something goes wrong:

```bash
#!/bin/bash
# rollback.sh

echo "⚠ Rolling back to unencrypted files"

# 1. Stop services
systemctl stop uo-server
pkill -f uo_client

# 2. Restore from backup
LATEST_BACKUP=$(ls -t backups/*.tar.gz | head -1)
echo "Restoring from: $LATEST_BACKUP"

tar -xzf "$LATEST_BACKUP" -C /

# 3. Remove environment variables
unset UO_CLIENT_KEY
unset UO_SERVER_KEY

# 4. Restart services
systemctl start uo-server

echo "✓ Rollback complete"
```

---

## Performance Optimization

### Client Optimization

```python
# Preload files at startup
loader.preload_files([
    "art.mul.enc",
    "gumpart.mul.enc",
    "tiledata.mul.enc"
])

# Enable aggressive caching
loader = UOFileLoader(
    passphrase="key",
    cache_enabled=True
)
```

### Server Optimization

```bash
# Use RAM disk for decrypted data (Linux)
sudo mkdir -p /mnt/ramdisk
sudo mount -t tmpfs -o size=2G tmpfs /mnt/ramdisk

# Decrypt to RAM disk at startup
# (modify your server startup script)
```

---

## Monitoring

### Log What Matters

```python
# In your client/server code
import logging

logging.basicConfig(
    filename='uo_crypto.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Log decryption attempts
logging.info(f"Loading encrypted file: {filename}")
logging.info(f"Decryption successful: {len(data)} bytes")

# Log failures
logging.error(f"Decryption failed for {filename}: {error}")
```

### Monitor Auth Server

```bash
# Count authentication attempts
grep "Authentication" auth_server.log | wc -l

# Count failed attempts
grep "Authentication failed" auth_server.log | wc -l

# Monitor in real-time
tail -f auth_server.log | grep --color=always "failed"
```

---

## Maintenance

### Regular Tasks

**Weekly**:
- Check logs for errors
- Monitor disk space
- Verify backups

**Monthly**:
- Review access logs
- Update dependencies
- Test restore procedure

**Every 6 Months**:
- Rotate passphrases
- Update encryption library
- Security audit

### Passphrase Rotation

```bash
#!/bin/bash
# rotate_keys.sh

OLD_KEY="OldPassphrase2025"
NEW_KEY="NewPassphrase2025"

# 1. Decrypt all files with old key
for file in *.enc; do
    python3 uo_crypto.py decrypt "$file" -p "$OLD_KEY"
done

# 2. Remove old encrypted files
rm *.enc

# 3. Re-encrypt with new key
python3 uo_crypto.py encrypt-batch . -p "$NEW_KEY" -r

# 4. Update environment variables
# (requires manual update or config management)

echo "✓ Keys rotated - update environment variables!"
```

---

## Support and Resources

- **Full Documentation**: `ENCRYPTION_GUIDE.md`
- **Integration Guide**: `SERVER_CLIENT_INTEGRATION.md`
- **Code Examples**: `example_client.py`, `example_auth_server.py`
- **C# Integration**: `client_integration_example.cs`

For issues, check troubleshooting section or review the example code.
