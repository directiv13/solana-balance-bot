#!/bin/bash

# VPS Setup Script for Solana Balance Bot
# This script prepares a fresh Linux VPS for deployment

set -e

echo "================================================"
echo "Solana Balance Bot - VPS Setup Script"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run as root or with sudo"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "✅ Docker installed successfully"
else
    echo "ℹ️  Docker is already installed"
fi

# Install Docker Compose
echo "🐳 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt-get install -y docker-compose-plugin
    echo "✅ Docker Compose installed successfully"
else
    echo "ℹ️  Docker Compose is already installed"
fi

# Create deployment directory
DEPLOY_PATH="/opt/solana_balance_bot"
echo "📁 Creating deployment directory: $DEPLOY_PATH"
mkdir -p $DEPLOY_PATH
mkdir -p $DEPLOY_PATH/data

# Set permissions
echo "🔐 Setting permissions..."
chmod 755 $DEPLOY_PATH
chmod 755 $DEPLOY_PATH/data

# Create .env file template if it doesn't exist
if [ ! -f "$DEPLOY_PATH/.env" ]; then
    echo "📝 Creating .env template..."
    cat > $DEPLOY_PATH/.env << 'EOF'
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHANNEL_ID=@your_channel_or_chat_id

# Helius RPC Configuration
HELIUS_API_KEY=your_helius_api_key_here

# Pushover Configuration
PUSHOVER_APP_TOKEN=your_pushover_app_token_here

# Database Configuration
DATABASE_PATH=./data/bot.db

# Sync Interval (seconds)
SYNC_INTERVAL=60

# Alert Threshold (USDT)
ALERT_THRESHOLD=1000000
EOF
    echo "✅ .env template created at $DEPLOY_PATH/.env"
    echo "⚠️  IMPORTANT: Edit $DEPLOY_PATH/.env with your credentials before deployment!"
else
    echo "ℹ️  .env file already exists"
fi

# Configure firewall (optional, adjust as needed)
echo "🔥 Configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp  # SSH
    echo "✅ Firewall configured"
else
    echo "ℹ️  UFW not installed, skipping firewall configuration"
fi

# Enable Docker service
echo "🚀 Enabling Docker service..."
systemctl enable docker
systemctl start docker

echo ""
echo "================================================"
echo "✅ VPS Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Edit the configuration file:"
echo "   nano $DEPLOY_PATH/.env"
echo ""
echo "2. Add your GitHub repository as a deployment source"
echo "   or manually copy the application files to:"
echo "   $DEPLOY_PATH"
echo ""
echo "3. Deploy the application:"
echo "   cd $DEPLOY_PATH"
echo "   docker-compose up -d"
echo ""
echo "4. View logs:"
echo "   docker-compose logs -f"
echo ""
echo "================================================"
