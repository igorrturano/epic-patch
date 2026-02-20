/*
 * UO Client Integration Example (C#)
 *
 * This example shows how to integrate encrypted file loading into a
 * UO client or server emulator (RunUO, ServUO, ClassicUO, etc.)
 *
 * Key Concepts:
 * 1. Replace standard file I/O with decrypting file reader
 * 2. Keep decrypted data in memory only
 * 3. Transparent integration with existing code
 */

using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace UOCrypto
{
    /// <summary>
    /// Provides AES-256-GCM decryption for encrypted UO files
    /// </summary>
    public class UOFileDecryptor
    {
        // File format constants (must match Python implementation)
        private static readonly byte[] MAGIC_HEADER = Encoding.ASCII.GetBytes("UOENC");
        private const byte VERSION = 0x01;
        private const int SALT_SIZE = 32;
        private const int NONCE_SIZE = 16;
        private const int TAG_SIZE = 16;

        private readonly string _passphrase;

        public UOFileDecryptor(string passphrase)
        {
            _passphrase = passphrase ?? throw new ArgumentNullException(nameof(passphrase));
        }

        /// <summary>
        /// Derive AES-256 key from passphrase using PBKDF2
        /// </summary>
        private byte[] DeriveKey(byte[] salt)
        {
            using (var pbkdf2 = new Rfc2898DeriveBytes(
                _passphrase,
                salt,
                iterations: 100000,
                HashAlgorithmName.SHA256))
            {
                return pbkdf2.GetBytes(32); // 256 bits
            }
        }

        /// <summary>
        /// Check if a file is encrypted
        /// </summary>
        public bool IsEncrypted(string filePath)
        {
            try
            {
                using (var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read))
                {
                    byte[] header = new byte[MAGIC_HEADER.Length];
                    fs.Read(header, 0, header.Length);

                    for (int i = 0; i < MAGIC_HEADER.Length; i++)
                    {
                        if (header[i] != MAGIC_HEADER[i])
                            return false;
                    }
                    return true;
                }
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Decrypt an encrypted file into memory
        /// </summary>
        public byte[] DecryptFile(string filePath)
        {
            if (!File.Exists(filePath))
                throw new FileNotFoundException($"File not found: {filePath}");

            byte[] encryptedData = File.ReadAllBytes(filePath);

            // Check magic header
            for (int i = 0; i < MAGIC_HEADER.Length; i++)
            {
                if (encryptedData[i] != MAGIC_HEADER[i])
                    throw new InvalidDataException("Not a valid encrypted UO file");
            }

            int offset = MAGIC_HEADER.Length;

            // Read version
            byte version = encryptedData[offset++];
            if (version != VERSION)
                throw new NotSupportedException($"Unsupported file version: {version}");

            // Read salt
            byte[] salt = new byte[SALT_SIZE];
            Buffer.BlockCopy(encryptedData, offset, salt, 0, SALT_SIZE);
            offset += SALT_SIZE;

            // Read nonce
            byte[] nonce = new byte[NONCE_SIZE];
            Buffer.BlockCopy(encryptedData, offset, nonce, 0, NONCE_SIZE);
            offset += NONCE_SIZE;

            // Read tag
            byte[] tag = new byte[TAG_SIZE];
            Buffer.BlockCopy(encryptedData, offset, tag, 0, TAG_SIZE);
            offset += TAG_SIZE;

            // Read ciphertext
            int ciphertextLength = encryptedData.Length - offset;
            byte[] ciphertext = new byte[ciphertextLength];
            Buffer.BlockCopy(encryptedData, offset, ciphertext, 0, ciphertextLength);

            // Derive key
            byte[] key = DeriveKey(salt);

            // Decrypt using AES-GCM
            byte[] plaintext = new byte[ciphertextLength];

            using (var aes = new AesGcm(key))
            {
                try
                {
                    aes.Decrypt(nonce, ciphertext, tag, plaintext);
                }
                catch (CryptographicException)
                {
                    throw new CryptographicException("Decryption failed - wrong passphrase or corrupted file");
                }
            }

            return plaintext;
        }

        /// <summary>
        /// Load a file, decrypting if necessary
        /// </summary>
        public byte[] LoadFile(string filePath)
        {
            if (IsEncrypted(filePath))
            {
                return DecryptFile(filePath);
            }
            else
            {
                return File.ReadAllBytes(filePath);
            }
        }
    }

    /// <summary>
    /// Custom FileStream that transparently decrypts encrypted files
    /// </summary>
    public class UOFileStream : Stream
    {
        private readonly MemoryStream _innerStream;
        private readonly string _filePath;

        public override bool CanRead => _innerStream.CanRead;
        public override bool CanSeek => _innerStream.CanSeek;
        public override bool CanWrite => false;
        public override long Length => _innerStream.Length;

        public override long Position
        {
            get => _innerStream.Position;
            set => _innerStream.Position = value;
        }

        public UOFileStream(string filePath, UOFileDecryptor decryptor)
        {
            _filePath = filePath;

            // Load and decrypt file into memory
            byte[] data = decryptor.LoadFile(filePath);
            _innerStream = new MemoryStream(data, false);
        }

        public override int Read(byte[] buffer, int offset, int count)
        {
            return _innerStream.Read(buffer, offset, count);
        }

        public override long Seek(long offset, SeekOrigin origin)
        {
            return _innerStream.Seek(offset, origin);
        }

        public override void Flush()
        {
            _innerStream.Flush();
        }

        public override void SetLength(long value)
        {
            throw new NotSupportedException();
        }

        public override void Write(byte[] buffer, int offset, int count)
        {
            throw new NotSupportedException();
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                _innerStream?.Dispose();
            }
            base.Dispose(disposing);
        }
    }

    /// <summary>
    /// Example: Integrating with existing UO file readers
    /// </summary>
    public class Example
    {
        private static UOFileDecryptor _decryptor;

        public static void Initialize(string passphrase)
        {
            _decryptor = new UOFileDecryptor(passphrase);
        }

        /// <summary>
        /// Example: Loading art.mul with encryption support
        /// </summary>
        public static void LoadArtFile(string dataPath)
        {
            string artPath = Path.Combine(dataPath, "art.mul");

            // Check if encrypted version exists
            if (File.Exists(artPath + ".enc"))
            {
                artPath = artPath + ".enc";
            }

            // Load file (automatically decrypts if needed)
            using (var stream = new UOFileStream(artPath, _decryptor))
            using (var reader = new BinaryReader(stream))
            {
                // Read UO data as normal
                // The decryption is transparent to this code

                Console.WriteLine($"Loaded art.mul: {stream.Length} bytes");

                // Example: Read first few bytes
                byte[] header = reader.ReadBytes(64);
                Console.WriteLine($"First bytes: {BitConverter.ToString(header)}");
            }
        }

        /// <summary>
        /// Example: Batch loading multiple files
        /// </summary>
        public static void LoadAllUOFiles(string dataPath)
        {
            string[] files = {
                "art.mul",
                "gumpart.mul",
                "multi.mul",
                "anim.mul",
                "tiledata.mul"
            };

            foreach (string filename in files)
            {
                string filePath = Path.Combine(dataPath, filename);

                // Try encrypted version first
                if (File.Exists(filePath + ".enc"))
                {
                    filePath = filePath + ".enc";
                }

                if (File.Exists(filePath))
                {
                    try
                    {
                        byte[] data = _decryptor.LoadFile(filePath);
                        Console.WriteLine($"✓ Loaded {filename}: {data.Length:N0} bytes");
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"✗ Failed to load {filename}: {ex.Message}");
                    }
                }
            }
        }
    }

    /// <summary>
    /// Main program for testing
    /// </summary>
    class Program
    {
        static void Main(string[] args)
        {
            if (args.Length < 2)
            {
                Console.WriteLine("Usage: UOCrypto.exe <data_path> <passphrase>");
                Console.WriteLine();
                Console.WriteLine("Example:");
                Console.WriteLine("  UOCrypto.exe \"C:\\UO\\Data\" \"my_secret_passphrase\"");
                return;
            }

            string dataPath = args[0];
            string passphrase = args[1];

            try
            {
                // Initialize decryptor
                Example.Initialize(passphrase);

                // Load files
                Example.LoadAllUOFiles(dataPath);

                Console.WriteLine("\n✓ All files loaded successfully!");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\n✗ Error: {ex.Message}");
                Environment.Exit(1);
            }
        }
    }
}
