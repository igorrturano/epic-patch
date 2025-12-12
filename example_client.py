#!/usr/bin/env python3
"""
Example UO Client with Encrypted File Support

This demonstrates how to integrate encrypted file loading into a UO client.
"""

import os
import sys
from pathlib import Path
from uo_file_loader import UOFileManager

class UOClient:
    """
    Example UO Client that loads encrypted files transparently
    """

    def __init__(self, data_path, passphrase=None):
        """
        Initialize the client

        Args:
            data_path: Path to UO data files
            passphrase: Decryption passphrase (if None, will try to get from env)
        """
        self.data_path = Path(data_path)

        # Get passphrase
        if passphrase is None:
            passphrase = self._get_passphrase()

        # Initialize file manager with multiple search paths
        self.file_manager = UOFileManager(
            passphrase=passphrase,
            search_paths=[
                str(self.data_path),              # Main data directory
                str(self.data_path / "patch"),    # Patch files
                str(self.data_path / "custom"),   # Custom content
            ]
        )

        # File caches
        self.art_data = None
        self.gump_data = None
        self.tile_data = None

        print(f"✓ UO Client initialized with data path: {self.data_path}")

    def _get_passphrase(self):
        """
        Get decryption passphrase from environment or prompt user

        Returns:
            Passphrase string
        """
        # Try environment variable first
        passphrase = os.getenv('UO_CLIENT_KEY')

        if passphrase:
            print("✓ Using passphrase from UO_CLIENT_KEY environment variable")
            return passphrase

        # Try config file
        config_file = self.data_path / "client.config"
        if config_file.exists():
            print(f"✓ Loading passphrase from {config_file}")
            return config_file.read_text().strip()

        # Prompt user as last resort
        print("⚠ No passphrase found in environment or config")
        import getpass
        return getpass.getpass("Enter decryption passphrase: ")

    def load_art_file(self):
        """
        Load art.mul file with transparent decryption

        Returns:
            Bytes of art.mul data
        """
        if self.art_data is None:
            print("Loading art.mul...")
            self.art_data = self.file_manager.load("art.mul")
            print(f"✓ Loaded art.mul: {len(self.art_data):,} bytes")

        return self.art_data

    def load_gump_files(self):
        """
        Load gump files (gumpart.mul and gumpidx.mul)

        Returns:
            Tuple of (gumpart_data, gumpidx_data)
        """
        print("Loading gump files...")

        gumpart_data = self.file_manager.load("gumpart.mul")
        gumpidx_data = self.file_manager.load("gumpidx.mul")

        print(f"✓ Loaded gumpart.mul: {len(gumpart_data):,} bytes")
        print(f"✓ Loaded gumpidx.mul: {len(gumpidx_data):,} bytes")

        return gumpart_data, gumpidx_data

    def load_tiledata(self):
        """
        Load tiledata.mul file

        Returns:
            Bytes of tiledata.mul
        """
        if self.tile_data is None:
            print("Loading tiledata.mul...")
            self.tile_data = self.file_manager.load("tiledata.mul")
            print(f"✓ Loaded tiledata.mul: {len(self.tile_data):,} bytes")

        return self.tile_data

    def load_animation_files(self):
        """
        Load all animation files

        Returns:
            Dict of animation files
        """
        print("Loading animation files...")

        anims = {}
        for anim_file in ["anim.mul", "anim2.mul", "anim3.mul"]:
            try:
                data = self.file_manager.load(anim_file)
                anims[anim_file] = data
                print(f"✓ Loaded {anim_file}: {len(data):,} bytes")
            except FileNotFoundError:
                print(f"⊘ {anim_file} not found (optional)")

        return anims

    def load_all_files(self):
        """
        Preload all common files for faster access
        """
        print("\nPreloading all game files...")
        print("=" * 60)

        files_to_load = [
            "art.mul",
            "artidx.mul",
            "gumpart.mul",
            "gumpidx.mul",
            "tiledata.mul",
            "multi.mul",
            "multi.idx",
            "animdata.mul",
        ]

        loaded_count = 0
        total_bytes = 0

        for filename in files_to_load:
            try:
                data = self.file_manager.load(filename)
                loaded_count += 1
                total_bytes += len(data)
                print(f"  ✓ {filename:<20} {len(data):>12,} bytes")
            except FileNotFoundError:
                print(f"  ⊘ {filename:<20} {'not found':>12}")

        print("=" * 60)
        print(f"Loaded {loaded_count}/{len(files_to_load)} files")
        print(f"Total: {total_bytes:,} bytes ({total_bytes / 1024 / 1024:.2f} MB)")
        print()

    def start(self):
        """
        Start the client
        """
        print("\n" + "=" * 60)
        print("UO Client Starting...")
        print("=" * 60)

        # Load all files
        self.load_all_files()

        # Your client logic here
        print("✓ Client ready!")
        print("\nTo connect to server:")
        print("  - Server address: <your server address>")
        print("  - Server port: 2593")
        print()


class AuthenticatedClient(UOClient):
    """
    Client that gets decryption key from authentication server
    """

    def __init__(self, data_path, auth_server_url):
        """
        Initialize client with server authentication

        Args:
            data_path: Path to UO data files
            auth_server_url: URL of authentication server
        """
        self.auth_server_url = auth_server_url

        # Get passphrase from auth server
        passphrase = self._authenticate()

        # Initialize parent with passphrase
        super().__init__(data_path, passphrase)

    def _authenticate(self):
        """
        Authenticate with server and get decryption key

        Returns:
            Decryption passphrase
        """
        print(f"\nAuthenticating with {self.auth_server_url}...")

        import getpass

        username = input("Username: ")
        password = getpass.getpass("Password: ")

        try:
            import requests

            response = requests.post(
                f"{self.auth_server_url}/api/get-key",
                json={
                    'username': username,
                    'password': password
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✓ Authentication successful!")
                    return data['decryption_key']
                else:
                    print(f"✗ Authentication failed: {data.get('error')}")
                    sys.exit(1)
            else:
                print(f"✗ Server returned error: {response.status_code}")
                sys.exit(1)

        except ImportError:
            print("✗ requests library not installed")
            print("  Install with: pip install requests")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            sys.exit(1)


def main():
    """
    Main entry point
    """
    import argparse

    parser = argparse.ArgumentParser(
        description='UO Client with Encrypted File Support'
    )

    parser.add_argument(
        '--data-path',
        default='.',
        help='Path to UO data files (default: current directory)'
    )

    parser.add_argument(
        '--passphrase',
        help='Decryption passphrase (or use UO_CLIENT_KEY env var)'
    )

    parser.add_argument(
        '--auth-server',
        help='Authentication server URL (for server-side key distribution)'
    )

    parser.add_argument(
        '--test-load',
        action='store_true',
        help='Test loading all files and exit'
    )

    args = parser.parse_args()

    try:
        # Create client
        if args.auth_server:
            client = AuthenticatedClient(args.data_path, args.auth_server)
        else:
            client = UOClient(args.data_path, args.passphrase)

        # Test or start
        if args.test_load:
            client.load_all_files()
            print("✓ Test complete - all files loaded successfully!")
        else:
            client.start()

    except KeyboardInterrupt:
        print("\n\n✓ Client shutdown by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
