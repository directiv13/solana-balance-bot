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

# Create 'deployer' user
DEPLOYER_USER="deployer"
echo "👤 Setting up '$DEPLOYER_USER' user..."
if id "$DEPLOYER_USER" &>/dev/null; then
    echo "ℹ️  User '$DEPLOYER_USER' already exists"
else
    # Create user with home directory
    useradd -m -s /bin/bash $DEPLOYER_USER
    echo "✅ User '$DEPLOYER_USER' created"
    
    # Set a password (user should change this later)
    echo "$DEPLOYER_USER:deployer123" | chpasswd
    echo "⚠️  Default password set to 'deployer123' - CHANGE THIS IMMEDIATELY!"
fi

# Add deployer to docker group (so they can run docker without sudo)
echo "🐳 Adding '$DEPLOYER_USER' to docker group..."
usermod -aG docker $DEPLOYER_USER

# Optionally add to sudo group (uncomment if needed)
# usermod -aG sudo $DEPLOYER_USER

# Set up SSH directory for deployer
echo "🔑 Setting up SSH for '$DEPLOYER_USER'..."
DEPLOYER_HOME="/home/$DEPLOYER_USER"
mkdir -p $DEPLOYER_HOME/.ssh
chmod 700 $DEPLOYER_HOME/.ssh
touch $DEPLOYER_HOME/.ssh/authorized_keys
chmod 600 $DEPLOYER_HOME/.ssh/authorized_keys
chown -R $DEPLOYER_USER:$DEPLOYER_USER $DEPLOYER_HOME/.ssh

# Create deployment directory
DEPLOY_PATH="/opt/solana_balance_bot"
echo "📁 Creating deployment directory: $DEPLOY_PATH"
mkdir -p $DEPLOY_PATH
mkdir -p $DEPLOY_PATH/data

# Set permissions and ownership for deployer
echo "🔐 Setting permissions and ownership..."
chown -R $DEPLOYER_USER:$DEPLOYER_USER $DEPLOY_PATH
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
echo "👤 Deployer User Information:"
echo "   Username: $DEPLOYER_USER"
echo "   Home: $DEPLOYER_HOME"
echo "   Deploy Path: $DEPLOY_PATH"
echo ""
echo "⚠️  SECURITY NOTICE:"
echo "   - Default password: 'deployer123'"
echo "   - Change password immediately: passwd $DEPLOYER_USER"
echo "   - Or disable password login and use SSH keys only"
echo ""
echo "🔑 To set up SSH key authentication for deployer:"
echo "   1. On your local machine, generate SSH key (if you don't have one):"
echo "      ssh-keygen -t ed25519 -C \"deployer@solana-bot\""
echo ""
echo "   2. Copy your public key to the server:"
echo "      ssh-copy-id $DEPLOYER_USER@<server-ip>"
echo ""
echo "   3. Or manually add your public key to:"
echo "      $DEPLOYER_HOME/.ssh/authorized_keys"
echo ""
echo "📋 Next steps:"
echo "1. Change the deployer password:"
echo "   passwd $DEPLOYER_USER"
echo ""
echo "2. Set up SSH key authentication (recommended)"
echo ""
echo "3. Switch to deployer user:"
echo "   su - $DEPLOYER_USER"
echo ""
echo "4. Edit the configuration file:"
echo "   nano $DEPLOY_PATH/.env"
echo ""
echo "5. Deploy the application (as deployer):"
echo "   cd $DEPLOY_PATH"
echo "   docker-compose up -d"
echo ""
echo "6. View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🔧 For GitHub Actions deployment, use:"
echo "   VPS_USER: $DEPLOYER_USER"
echo "   VPS_PATH: $DEPLOY_PATH"
echo ""
echo "================================================"
