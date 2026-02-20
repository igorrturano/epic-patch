#!/bin/bash

###############################################################################
# Quick UO File Encryption Script
#
# This script provides an easy way to encrypt all your UO files with a
# single command. It handles backup, encryption, and verification.
#
# Usage:
#   ./quick_encrypt.sh
#
# The script will:
# 1. Check dependencies
# 2. Create backup
# 3. Encrypt all files
# 4. Verify encryption
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PASSPHRASE=""
BACKUP_DIR="./backups"
ENCRYPT_EXTENSIONS=".mul .uop .idx .def"

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          UO File Encryption - Quick Setup                 ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

###############################################################################
# Step 1: Check Dependencies
###############################################################################

check_dependencies() {
    print_info "Checking dependencies..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo "Install Python 3: sudo apt install python3"
        exit 1
    fi
    print_success "Python 3 found: $(python3 --version)"

    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_warning "pip3 not found, trying to install..."
        sudo apt install python3-pip -y
    fi
    print_success "pip3 found"

    # Check pycryptodome
    if ! python3 -c "from Cryptodome.Cipher import AES" 2>/dev/null; then
        print_warning "pycryptodome not installed, installing..."
        pip3 install pycryptodome
    fi
    print_success "pycryptodome installed"

    echo ""
}

###############################################################################
# Step 2: Get Passphrase
###############################################################################

get_passphrase() {
    print_info "Passphrase Configuration"
    echo ""

    while true; do
        read -s -p "Enter encryption passphrase (20+ characters recommended): " PASSPHRASE
        echo ""

        if [ ${#PASSPHRASE} -lt 12 ]; then
            print_warning "Passphrase too short! Use at least 12 characters."
            continue
        fi

        read -s -p "Confirm passphrase: " PASSPHRASE_CONFIRM
        echo ""

        if [ "$PASSPHRASE" = "$PASSPHRASE_CONFIRM" ]; then
            print_success "Passphrase confirmed"
            break
        else
            print_error "Passphrases don't match, try again"
        fi
    done

    echo ""
}

###############################################################################
# Step 3: Count Files
###############################################################################

count_files() {
    print_info "Scanning for UO files..."

    local count=0
    for ext in $ENCRYPT_EXTENSIONS; do
        local found=$(find . -type f -name "*${ext}" ! -name "*.enc" | wc -l)
        count=$((count + found))
    done

    if [ $count -eq 0 ]; then
        print_error "No UO files found in current directory"
        exit 1
    fi

    print_success "Found $count files to encrypt"
    echo ""

    # List files
    print_info "Files to encrypt:"
    for ext in $ENCRYPT_EXTENSIONS; do
        find . -type f -name "*${ext}" ! -name "*.enc" -exec basename {} \; | head -10
    done

    if [ $count -gt 10 ]; then
        echo "... and $((count - 10)) more files"
    fi

    echo ""
}

###############################################################################
# Step 4: Create Backup
###############################################################################

create_backup() {
    print_info "Creating backup..."

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    # Create timestamped backup
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/uo_backup_$timestamp.tar.gz"

    # Find and backup all UO files
    local files_to_backup=""
    for ext in $ENCRYPT_EXTENSIONS; do
        files_to_backup="$files_to_backup $(find . -type f -name "*${ext}" ! -name "*.enc")"
    done

    if [ -n "$files_to_backup" ]; then
        tar -czf "$backup_file" $files_to_backup 2>/dev/null || true
        print_success "Backup created: $backup_file"

        local backup_size=$(du -h "$backup_file" | cut -f1)
        print_info "Backup size: $backup_size"
    else
        print_warning "No files to backup"
    fi

    echo ""
}

###############################################################################
# Step 5: Encrypt Files
###############################################################################

encrypt_files() {
    print_info "Starting encryption..."
    echo ""

    # Run encryption
    python3 uo_crypto.py encrypt-batch . \
        --passphrase "$PASSPHRASE" \
        --recursive

    echo ""
    print_success "Encryption complete!"
    echo ""
}

###############################################################################
# Step 6: Verify Encryption
###############################################################################

verify_encryption() {
    print_info "Verifying encrypted files..."

    local enc_count=$(find . -type f -name "*.enc" | wc -l)

    if [ $enc_count -gt 0 ]; then
        print_success "Created $enc_count encrypted files"

        # Test decryption on first file
        local test_file=$(find . -type f -name "*.enc" | head -1)
        if [ -n "$test_file" ]; then
            print_info "Testing decryption on: $(basename $test_file)"

            if python3 uo_crypto.py decrypt "$test_file" \
                --passphrase "$PASSPHRASE" \
                --output "/tmp/test_decrypt_$$" 2>/dev/null; then
                print_success "Decryption test successful!"
                rm -f "/tmp/test_decrypt_$$"
            else
                print_error "Decryption test failed!"
                exit 1
            fi
        fi
    else
        print_error "No encrypted files created!"
        exit 1
    fi

    echo ""
}

###############################################################################
# Step 7: Cleanup Options
###############################################################################

cleanup_originals() {
    print_warning "IMPORTANT: Original file cleanup"
    echo ""
    echo "Your original files are still present. Options:"
    echo ""
    echo "  1. Keep originals (safe, recommended for first time)"
    echo "  2. Delete originals (save space, encrypted files only)"
    echo "  3. Skip (decide later)"
    echo ""

    read -p "Choose option [1-3]: " choice

    case $choice in
        2)
            print_warning "This will DELETE all original unencrypted files!"
            read -p "Are you sure? Type 'yes' to confirm: " confirm

            if [ "$confirm" = "yes" ]; then
                print_info "Deleting original files..."

                for ext in $ENCRYPT_EXTENSIONS; do
                    find . -type f -name "*${ext}" ! -name "*.enc" -delete
                done

                print_success "Original files deleted"
            else
                print_info "Deletion cancelled"
            fi
            ;;
        1|3)
            print_info "Keeping original files"
            ;;
        *)
            print_info "Invalid option, keeping original files"
            ;;
    esac

    echo ""
}

###############################################################################
# Step 8: Summary
###############################################################################

print_summary() {
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                Encryption Complete!                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""

    print_info "Next Steps:"
    echo ""
    echo "1. SAVE YOUR PASSPHRASE in a secure location!"
    echo "   You cannot decrypt files without it!"
    echo ""
    echo "2. Test decryption with:"
    echo "   python3 uo_crypto.py decrypt <file.enc> --passphrase 'your_passphrase'"
    echo ""
    echo "3. Integrate with your client:"
    echo "   - Python: See uo_file_loader.py"
    echo "   - C#: See client_integration_example.cs"
    echo ""
    echo "4. Read full documentation:"
    echo "   cat ENCRYPTION_GUIDE.md"
    echo ""
    echo "5. Backup location:"
    echo "   $BACKUP_DIR/"
    echo ""

    print_success "Your UO files are now encrypted!"
    echo ""
}

###############################################################################
# Main Execution
###############################################################################

main() {
    clear
    print_header

    # Check if uo_crypto.py exists
    if [ ! -f "uo_crypto.py" ]; then
        print_error "uo_crypto.py not found in current directory!"
        exit 1
    fi

    # Execute steps
    check_dependencies
    get_passphrase
    count_files

    # Confirm before proceeding
    read -p "Proceed with encryption? [y/N]: " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        print_info "Encryption cancelled"
        exit 0
    fi
    echo ""

    create_backup
    encrypt_files
    verify_encryption
    cleanup_originals
    print_summary
}

# Run main function
main
