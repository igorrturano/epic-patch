#!/usr/bin/env python3
"""
Example Authentication Server for Key Distribution

This server provides decryption keys to authenticated clients.
"""

from flask import Flask, request, jsonify
import hashlib
import os
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

# Database setup
DB_PATH = 'auth.db'


def init_database():
    """Initialize the authentication database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            decryption_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    # Create auth tokens table (for session management)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            decryption_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()

    print("✓ Database initialized")


def add_user(username, password, decryption_key=None):
    """
    Add a new user to the database

    Args:
        username: Username
        password: Plain text password (will be hashed)
        decryption_key: Optional custom decryption key
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Hash password
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    # Generate decryption key if not provided
    if decryption_key is None:
        # Generate unique key for this user
        decryption_key = hashlib.sha256(
            f"{username}:{password}:secret_salt".encode()
        ).hexdigest()

    try:
        cursor.execute(
            'INSERT INTO users (username, password_hash, decryption_key) VALUES (?, ?, ?)',
            (username, password_hash, decryption_key)
        )
        conn.commit()
        print(f"✓ User '{username}' added successfully")
        print(f"  Decryption key: {decryption_key}")
        return True
    except sqlite3.IntegrityError:
        print(f"✗ User '{username}' already exists")
        return False
    finally:
        conn.close()


def verify_credentials(username, password):
    """
    Verify user credentials

    Args:
        username: Username
        password: Plain text password

    Returns:
        User dict if valid, None otherwise
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    cursor.execute(
        'SELECT id, username, decryption_key, is_active FROM users WHERE username = ? AND password_hash = ?',
        (username, password_hash)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        user_id, username, decryption_key, is_active = row

        if not is_active:
            return None

        return {
            'id': user_id,
            'username': username,
            'decryption_key': decryption_key
        }

    return None


def update_last_login(user_id):
    """Update user's last login timestamp"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        'UPDATE users SET last_login = ? WHERE id = ?',
        (datetime.now(), user_id)
    )

    conn.commit()
    conn.close()


@app.route('/api/get-key', methods=['POST'])
def get_decryption_key():
    """
    API endpoint to get decryption key

    Request JSON:
        {
            "username": "user1",
            "password": "password123"
        }

    Response JSON:
        {
            "success": true,
            "decryption_key": "abc123..."
        }
    """
    try:
        data = request.json

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password required'
            }), 400

        # Verify credentials
        user = verify_credentials(username, password)

        if user:
            # Update last login
            update_last_login(user['id'])

            # Log authentication
            print(f"✓ Authentication successful: {username} at {datetime.now()}")

            return jsonify({
                'success': True,
                'decryption_key': user['decryption_key'],
                'username': user['username']
            })
        else:
            # Log failed attempt
            print(f"✗ Authentication failed: {username} at {datetime.now()}")

            return jsonify({
                'success': False,
                'error': 'Invalid credentials'
            }), 401

    except Exception as e:
        print(f"✗ Error in get_decryption_key: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'UO Authentication Server',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/register', methods=['POST'])
def register_user():
    """
    Register a new user (optional endpoint)

    Request JSON:
        {
            "username": "newuser",
            "password": "password123",
            "email": "user@example.com"
        }
    """
    try:
        data = request.json

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password required'
            }), 400

        # Add user
        if add_user(username, password):
            return jsonify({
                'success': True,
                'message': 'User registered successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'User already exists'
            }), 409

    except Exception as e:
        print(f"✗ Error in register_user: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


def create_test_users():
    """Create some test users"""
    init_database()

    test_users = [
        ('admin', 'admin123', 'AdminDecryptionKey2025!'),
        ('user1', 'password1', 'User1Key_ABC123'),
        ('user2', 'password2', 'User2Key_XYZ789'),
    ]

    for username, password, key in test_users:
        add_user(username, password, key)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='UO Authentication Server'
    )

    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize database'
    )

    parser.add_argument(
        '--create-test-users',
        action='store_true',
        help='Create test users'
    )

    parser.add_argument(
        '--add-user',
        nargs=2,
        metavar=('USERNAME', 'PASSWORD'),
        help='Add a new user'
    )

    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )

    parser.add_argument(
        '--ssl',
        action='store_true',
        help='Enable SSL (uses adhoc certificate for testing)'
    )

    args = parser.parse_args()

    # Handle commands
    if args.init_db:
        init_database()
        return

    if args.create_test_users:
        create_test_users()
        return

    if args.add_user:
        username, password = args.add_user
        init_database()
        add_user(username, password)
        return

    # Start server
    print("=" * 60)
    print("UO Authentication Server")
    print("=" * 60)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"SSL: {args.ssl}")
    print()

    # Initialize database if it doesn't exist
    if not os.path.exists(DB_PATH):
        print("Database not found, initializing...")
        init_database()
        create_test_users()
        print()

    print("API Endpoints:")
    print(f"  POST /api/get-key     - Get decryption key")
    print(f"  POST /api/register    - Register new user")
    print(f"  GET  /api/health      - Health check")
    print()
    print("Test users (if created with --create-test-users):")
    print("  admin / admin123")
    print("  user1 / password1")
    print("  user2 / password2")
    print()
    print("Starting server...")
    print("=" * 60)
    print()

    # Run server
    if args.ssl:
        # For production, use proper SSL certificates
        # ssl_context = ('/path/to/cert.pem', '/path/to/key.pem')
        app.run(host=args.host, port=args.port, ssl_context='adhoc')
    else:
        app.run(host=args.host, port=args.port, debug=True)


if __name__ == '__main__':
    main()
