#!/bin/bash
# Setup script for Storacha authentication

set -e

echo "=========================================="
echo "Storacha Authentication Setup"
echo "=========================================="
echo ""

# Check if Storacha CLI is installed
if ! command -v storacha &> /dev/null; then
    echo "📦 Storacha CLI not found. Installing..."
    echo ""
    npm install -g @storacha/cli
    echo ""
    echo "✓ Storacha CLI installed"
else
    echo "✓ Storacha CLI already installed"
fi

echo ""
echo "=========================================="
echo "Authentication Steps"
echo "=========================================="
echo ""

# Check if already logged in
if storacha whoami &> /dev/null; then
    echo "✓ Already logged in to Storacha"
    echo ""
    storacha whoami
else
    echo "You need to login to Storacha."
    echo ""
    read -p "Enter your email address: " email
    
    echo ""
    echo "Logging in..."
    echo "⚠️  Check your email for verification link!"
    echo ""
    
    storacha login "$email"
    
    echo ""
    echo "✓ Login successful!"
fi

echo ""
echo "=========================================="
echo "Space Setup"
echo "=========================================="
echo ""

# List existing spaces
echo "Checking for existing spaces..."
spaces=$(storacha space ls 2>/dev/null || echo "")

if [ -z "$spaces" ]; then
    echo "No spaces found. Creating a new space..."
    echo ""
    read -p "Enter space name (default: migration-space): " space_name
    space_name=${space_name:-migration-space}
    
    echo ""
    echo "Creating space: $space_name"
    storacha space create "$space_name"
    
    echo ""
    echo "✓ Space created: $space_name"
else
    echo "✓ Existing spaces found:"
    echo "$spaces"
fi

echo ""
echo "=========================================="
echo "Current Configuration"
echo "=========================================="
echo ""

echo "Current user:"
storacha whoami

echo ""
echo "Available spaces:"
storacha space ls

echo ""
echo "Current space:"
storacha space info 2>/dev/null || echo "(No current space set)"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "You can now run the migration:"
echo "  python test_actual_migration.py"
echo ""
echo "Or test with a small file:"
echo "  echo 'test' > test.txt"
echo "  storacha up test.txt"
echo ""
