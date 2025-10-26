#!/bin/bash
# Install JavaScript dependencies for S3 to Storacha migration

set -e

echo "=========================================="
echo "Installing JavaScript Dependencies"
echo "=========================================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed!"
    echo ""
    echo "Please install Node.js 18+ from:"
    echo "  - https://nodejs.org"
    echo "  - Or use: brew install node (macOS)"
    echo ""
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required!"
    echo "Current version: $(node --version)"
    echo ""
    echo "Please upgrade Node.js from:"
    echo "  - https://nodejs.org"
    echo ""
    exit 1
fi

echo "✓ Node.js $(node --version) detected"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed!"
    exit 1
fi

echo "✓ npm $(npm --version) detected"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the JavaScript directory
cd "$SCRIPT_DIR"

echo ""
echo "Installing dependencies..."
echo ""

# Install dependencies
npm install

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "JavaScript dependencies installed successfully."
echo ""
echo "You can now use the Python library:"
echo "  python examples/test_migration.py --config examples/config.json --source test-data/ --destination migrated/"
echo ""
