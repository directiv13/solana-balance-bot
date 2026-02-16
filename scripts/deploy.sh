#!/bin/bash
# Manual deployment and debugging script for VPS

set -e

VPS_USER="${VPS_USER:-deployer}"
VPS_HOST="${VPS_HOST}"
VPS_PATH="${VPS_PATH:-/opt/solana_balance_bot}"

if [ -z "$VPS_HOST" ]; then
    echo "❌ Error: VPS_HOST environment variable is required"
    echo "Usage: VPS_HOST=your-vps-ip ./deploy.sh"
    exit 1
fi

echo "================================================"
echo "Deploying to VPS"
echo "================================================"
echo "Host: $VPS_HOST"
echo "User: $VPS_USER"
echo "Path: $VPS_PATH"
echo ""

# Sync files
echo "📦 Syncing files..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '.github' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'data/' \
    --exclude 'venv/' \
    ./ $VPS_USER@$VPS_HOST:$VPS_PATH/

# Deploy
echo ""
echo "🚀 Deploying..."
ssh $VPS_USER@$VPS_HOST << ENDSSH
    cd $VPS_PATH
    
    # Check .env
    if [ ! -f .env ]; then
        echo "⚠️  .env file not found!"
        echo "Creating from .env.example..."
        cp .env.example .env
        echo "❌ Please edit .env file with your credentials"
        exit 1
    fi
    
    echo "🐳 Stopping containers..."
    docker compose down
    
    echo "🔨 Building new image..."
    docker compose build --no-cache
    
    echo "🚀 Starting containers..."
    docker compose up -d
    
    echo "⏳ Waiting for startup..."
    sleep 5
    
    echo ""
    echo "📊 Container status:"
    docker compose ps
    
    echo ""
    echo "📝 Recent logs:"
    docker compose logs --tail=50
    
    echo ""
    if docker compose ps | grep -q "Up"; then
        echo "✅ Deployment successful!"
    else
        echo "⚠️  Container may not be running properly"
        echo "Check logs with: ssh $VPS_USER@$VPS_HOST 'cd $VPS_PATH && docker compose logs'"
    fi
ENDSSH

echo ""
echo "================================================"
echo "Deployment complete!"
echo "================================================"
echo ""
echo "Useful commands:"
echo "  View logs:    ssh $VPS_USER@$VPS_HOST 'cd $VPS_PATH && docker compose logs -f'"
echo "  Check status: ssh $VPS_USER@$VPS_HOST 'cd $VPS_PATH && docker compose ps'"
echo "  Restart:      ssh $VPS_USER@$VPS_HOST 'cd $VPS_PATH && docker compose restart'"
echo "  Stop:         ssh $VPS_USER@$VPS_HOST 'cd $VPS_PATH && docker compose down'"
