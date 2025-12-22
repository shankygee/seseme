#!/bin/bash
# Deploy Jarvis to Google Cloud Platform with GPU
# Uses n1-standard-4 with NVIDIA T4

set -e

echo "🚀 Jarvis Deployment Script for GCP"
echo "===================================="

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
ZONE="${GCP_ZONE:-us-central1-a}"
MACHINE_TYPE="${MACHINE_TYPE:-n1-standard-4}"
GPU_TYPE="${GPU_TYPE:-nvidia-tesla-t4}"
INSTANCE_NAME="${INSTANCE_NAME:-jarvis-assistant}"

# Check gcloud CLI
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is required"
    echo "   Install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check project ID
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        echo "❌ Error: GCP_PROJECT_ID not set and no default project"
        echo "   Run: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
fi

echo ""
echo "📋 Configuration:"
echo "   Project: $PROJECT_ID"
echo "   Zone: $ZONE"
echo "   Machine Type: $MACHINE_TYPE"
echo "   GPU: $GPU_TYPE"
echo ""

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable compute.googleapis.com --project=$PROJECT_ID

# Create firewall rule if it doesn't exist
if ! gcloud compute firewall-rules describe jarvis-allow-http --project=$PROJECT_ID &>/dev/null; then
    echo "🔒 Creating firewall rule..."
    gcloud compute firewall-rules create jarvis-allow-http \
        --project=$PROJECT_ID \
        --allow tcp:8000,tcp:443,tcp:80 \
        --target-tags=jarvis \
        --description="Allow Jarvis API traffic"
fi

# Startup script
STARTUP_SCRIPT=$(cat << 'STARTUP'
#!/bin/bash
set -e

# Install NVIDIA drivers and Docker
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update
apt-get install -y docker.io docker-compose-plugin nvidia-container-toolkit git

# Configure Docker for GPU
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

# Clone Jarvis
cd /opt
git clone https://github.com/YOUR_REPO/jarvis.git || true
cd jarvis/deploy

# Start services
docker compose up -d

echo "Jarvis deployment complete!" > /var/log/jarvis-startup.log
STARTUP
)

echo "🚀 Creating GCP instance..."
gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --accelerator=type=$GPU_TYPE,count=1 \
    --maintenance-policy=TERMINATE \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=100GB \
    --boot-disk-type=pd-ssd \
    --tags=jarvis \
    --metadata=startup-script="$STARTUP_SCRIPT" \
    --metadata=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"

echo ""
echo "⏳ Waiting for instance to start..."
sleep 30

# Get external IP
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📍 Instance Details:"
echo "   Name: $INSTANCE_NAME"
echo "   Zone: $ZONE"
echo "   External IP: $EXTERNAL_IP"
echo ""
echo "🔗 Access:"
echo "   SSH: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID"
echo "   API: http://$EXTERNAL_IP:8000"
echo "   Health: http://$EXTERNAL_IP:8000/health"
echo ""
echo "⚠️  Note: It may take 10-15 minutes for full setup"
echo "   Monitor: gcloud compute ssh $INSTANCE_NAME --command='tail -f /var/log/jarvis-startup.log'"
echo ""
echo "💡 Cost estimate: ~\$0.35-0.50/hour"
echo "   Stop when not in use: gcloud compute instances stop $INSTANCE_NAME --zone=$ZONE"
