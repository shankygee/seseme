#!/bin/bash
# Local Development Setup for Jarvis
# Sets up the environment for local development and testing

set -e

echo "🛠️  Jarvis Local Development Setup"
echo "==================================="
echo ""

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM=Linux;;
    Darwin*)    PLATFORM=Mac;;
    *)          PLATFORM="UNKNOWN"
esac

echo "📋 Detected platform: $PLATFORM"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python version: $PYTHON_VERSION"

# Check CUDA (optional)
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    DEVICE="cuda"
else
    echo "⚠️  No NVIDIA GPU detected - will use CPU (slower)"
    DEVICE="cpu"
fi

echo ""

# Project root (script is in deploy/scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
cd "$PROJECT_ROOT"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   Created venv/"
else
    echo "   Using existing venv/"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install backend dependencies
echo ""
echo "📦 Installing backend dependencies..."
pip install -r backend/requirements.txt

# Install CSM dependencies (from parent directory)
if [ -f "../requirements.txt" ]; then
    echo "📦 Installing CSM dependencies..."
    pip install -r ../requirements.txt
fi

# Create .env file if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo ""
    echo "📝 Creating .env file..."
    cp backend/.env.example backend/.env

    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env and add your ANTHROPIC_API_KEY"
    echo "   Get your key from: https://console.anthropic.com/"
    echo ""
fi

# Create data directories
mkdir -p data/models data/cache

# Download models (optional)
echo ""
read -p "📥 Download AI models now? (This may take 10-20 minutes) [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Downloading Whisper model..."
    python3 -c "import whisper; whisper.load_model('large-v3')"

    echo "Downloading CSM model..."
    python3 -c "
import sys
sys.path.insert(0, '..')
from generator import load_csm_1b
load_csm_1b(device='$DEVICE')
"
    echo "✅ Models downloaded"
else
    echo "ℹ️  Models will be downloaded on first run"
fi

# Redis setup (optional)
echo ""
if command -v docker &> /dev/null; then
    read -p "🐳 Start Redis in Docker? [y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker run -d --name jarvis-redis -p 6379:6379 redis:7-alpine || true
        echo "✅ Redis started on port 6379"
    fi
else
    echo "ℹ️  Docker not found - Redis won't be available (conversations won't persist)"
fi

echo ""
echo "============================================"
echo "✅ Setup Complete!"
echo "============================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Edit backend/.env and add your ANTHROPIC_API_KEY"
echo ""
echo "2. Start the server:"
echo "   source venv/bin/activate"
echo "   cd backend"
echo "   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "3. Test the API:"
echo "   curl http://localhost:8000/health"
echo ""
echo "4. Build the iOS app in Xcode and connect to http://YOUR_IP:8000"
echo ""
echo "🔧 Configuration:"
echo "   Device: $DEVICE"
echo "   Server: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
