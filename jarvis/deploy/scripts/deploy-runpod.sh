#!/bin/bash
# Deploy Jarvis to RunPod.io
# RunPod provides affordable GPU instances for AI workloads

set -e

echo "🚀 Jarvis Deployment Script for RunPod"
echo "========================================"

# Configuration
RUNPOD_API_KEY="${RUNPOD_API_KEY:-}"
GPU_TYPE="${GPU_TYPE:-NVIDIA RTX A5000}"
DISK_SIZE="${DISK_SIZE:-50}"
VOLUME_SIZE="${VOLUME_SIZE:-20}"

# Check requirements
if [ -z "$RUNPOD_API_KEY" ]; then
    echo "❌ Error: RUNPOD_API_KEY environment variable is required"
    echo "   Get your API key from: https://www.runpod.io/console/user/settings"
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY environment variable is required"
    echo "   Get your API key from: https://console.anthropic.com/"
    exit 1
fi

# Install runpodctl if not present
if ! command -v runpodctl &> /dev/null; then
    echo "📦 Installing runpodctl..."
    curl -sSL https://raw.githubusercontent.com/runpod/runpodctl/main/install.sh | bash
fi

echo ""
echo "📋 Deployment Configuration:"
echo "   GPU Type: $GPU_TYPE"
echo "   Disk Size: ${DISK_SIZE}GB"
echo "   Volume Size: ${VOLUME_SIZE}GB"
echo ""

# Create pod configuration
cat > /tmp/jarvis-pod.json << EOF
{
    "name": "jarvis-assistant",
    "imageName": "runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel-ubuntu22.04",
    "gpuTypeId": "$GPU_TYPE",
    "volumeInGb": $VOLUME_SIZE,
    "containerDiskInGb": $DISK_SIZE,
    "dockerArgs": "",
    "ports": "8000/http",
    "volumeMountPath": "/workspace",
    "env": [
        {"key": "ANTHROPIC_API_KEY", "value": "$ANTHROPIC_API_KEY"},
        {"key": "DEVICE", "value": "cuda"},
        {"key": "WHISPER_MODEL", "value": "large-v3"}
    ],
    "startScript": "cd /workspace && git clone https://github.com/YOUR_REPO/jarvis.git || true && cd jarvis && pip install -r backend/requirements.txt && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
}
EOF

echo "🔧 Creating RunPod instance..."
echo ""
echo "⚠️  Manual steps required:"
echo ""
echo "1. Go to https://www.runpod.io/console/pods"
echo "2. Click 'Deploy' and select GPU: $GPU_TYPE"
echo "3. Choose template: 'RunPod Pytorch 2.1'"
echo "4. Set container disk to ${DISK_SIZE}GB"
echo "5. Add environment variables:"
echo "   - ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
echo "6. In 'Docker Command', add:"
echo "   pip install fastapi uvicorn anthropic torch torchaudio transformers && \\"
echo "   git clone YOUR_REPO && cd jarvis && \\"
echo "   pip install -r backend/requirements.txt && \\"
echo "   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "7. Deploy and wait for the instance to start"
echo "8. Access Jarvis at the provided URL on port 8000"
echo ""
echo "📖 For automated deployment, use the Docker image:"
echo "   docker build -t jarvis-assistant -f deploy/Dockerfile ."
echo "   docker push YOUR_REGISTRY/jarvis-assistant:latest"
echo ""

# Alternative: Use runpodctl for API deployment
# runpodctl create pod --name jarvis-assistant \
#   --gpu-type "$GPU_TYPE" \
#   --image runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel \
#   --disk $DISK_SIZE \
#   --volume $VOLUME_SIZE

echo "✅ Configuration created!"
