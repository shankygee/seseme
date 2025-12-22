#!/bin/bash
# Deploy Jarvis to AWS EC2 with GPU
# Uses g4dn.xlarge (NVIDIA T4) or g5.xlarge (NVIDIA A10G)

set -e

echo "🚀 Jarvis Deployment Script for AWS EC2"
echo "========================================"

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
INSTANCE_TYPE="${INSTANCE_TYPE:-g4dn.xlarge}"  # T4 GPU, ~$0.50/hr
KEY_NAME="${KEY_NAME:-jarvis-key}"
SECURITY_GROUP="${SECURITY_GROUP:-jarvis-sg}"
AMI_ID="${AMI_ID:-}"  # Will be auto-detected if empty

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ Error: AWS CLI is required"
    echo "   Install: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Error: AWS credentials not configured"
    echo "   Run: aws configure"
    exit 1
fi

echo ""
echo "📋 Configuration:"
echo "   Region: $AWS_REGION"
echo "   Instance Type: $INSTANCE_TYPE"
echo "   Key Name: $KEY_NAME"
echo ""

# Get latest Deep Learning AMI (Ubuntu)
if [ -z "$AMI_ID" ]; then
    echo "🔍 Finding latest Deep Learning AMI..."
    AMI_ID=$(aws ec2 describe-images \
        --region $AWS_REGION \
        --owners amazon \
        --filters "Name=name,Values=Deep Learning AMI GPU PyTorch*Ubuntu 22.04*" \
        --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
        --output text)
    echo "   Found AMI: $AMI_ID"
fi

# Create key pair if it doesn't exist
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME --region $AWS_REGION &> /dev/null; then
    echo "🔑 Creating key pair..."
    aws ec2 create-key-pair \
        --key-name $KEY_NAME \
        --region $AWS_REGION \
        --query 'KeyMaterial' \
        --output text > ~/.ssh/${KEY_NAME}.pem
    chmod 400 ~/.ssh/${KEY_NAME}.pem
    echo "   Key saved to ~/.ssh/${KEY_NAME}.pem"
fi

# Create security group if it doesn't exist
SG_ID=$(aws ec2 describe-security-groups \
    --group-names $SECURITY_GROUP \
    --region $AWS_REGION \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "")

if [ -z "$SG_ID" ] || [ "$SG_ID" == "None" ]; then
    echo "🔒 Creating security group..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP \
        --description "Jarvis AI Assistant" \
        --region $AWS_REGION \
        --query 'GroupId' \
        --output text)

    # Allow SSH
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --region $AWS_REGION

    # Allow HTTP (API)
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 \
        --region $AWS_REGION

    # Allow HTTPS
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $AWS_REGION

    echo "   Security group created: $SG_ID"
fi

# User data script to setup Jarvis
USER_DATA=$(cat << 'USERDATA'
#!/bin/bash
set -e

# Update system
apt-get update
apt-get install -y docker.io docker-compose-plugin git

# Start Docker
systemctl start docker
systemctl enable docker

# Clone and setup Jarvis
cd /home/ubuntu
git clone https://github.com/YOUR_REPO/jarvis.git || true
cd jarvis

# Create .env file
cat > deploy/.env << EOF
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
DEVICE=cuda
WHISPER_MODEL=large-v3
USE_FASTER_WHISPER=true
EOF

# Start services
cd deploy
docker compose up -d

echo "Jarvis deployment complete!"
USERDATA
)

echo "🚀 Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --region $AWS_REGION \
    --user-data "$USER_DATA" \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3"}}]' \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=jarvis-assistant}]' \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "   Instance ID: $INSTANCE_ID"
echo ""
echo "⏳ Waiting for instance to start..."

aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $AWS_REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $AWS_REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📍 Instance Details:"
echo "   Instance ID: $INSTANCE_ID"
echo "   Public IP: $PUBLIC_IP"
echo ""
echo "🔗 Access:"
echo "   SSH: ssh -i ~/.ssh/${KEY_NAME}.pem ubuntu@$PUBLIC_IP"
echo "   API: http://$PUBLIC_IP:8000"
echo "   Health: http://$PUBLIC_IP:8000/health"
echo ""
echo "⚠️  Note: It may take 5-10 minutes for the API to be ready"
echo "   Monitor progress: ssh into instance and run 'docker logs jarvis-api -f'"
echo ""
echo "💡 Cost estimate: ~\$0.50-1.00/hour for $INSTANCE_TYPE"
echo "   Don't forget to stop/terminate when not in use!"
