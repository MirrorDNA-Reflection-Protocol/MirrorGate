#!/bin/bash
# MirrorGate Demo Launcher
# One-command demo start

set -e

cd "$(dirname "$0")/.."

echo "⟡ MirrorGate Demo Setup"
echo ""

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q watchdog cryptography uuid6

# Create watch directories if needed
mkdir -p ~/.mirrordna
mkdir -p ~/.mirrorgate

echo ""
echo "Starting MirrorGate daemon..."
echo ""

# Run daemon
python3 -m src.daemon "$@"
