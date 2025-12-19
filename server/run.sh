#!/bin/bash
# Run the Sesame CSM TTS Server

# Change to server directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "../.venv" ]; then
    source ../.venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(dirname "$(pwd)")"

# Disable torch compile for faster startup
export NO_TORCH_COMPILE=1

# Run the server
echo "Starting Sesame CSM TTS Server..."
python main.py "$@"
