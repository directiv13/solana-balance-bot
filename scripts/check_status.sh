#!/bin/bash
# VPS debugging script - run this on the VPS to check the bot status

echo "================================================"
echo "Solana Balance Bot - Status Check"
echo "================================================"
echo ""

# Check if Docker is running
echo "🐳 Docker service status:"
systemctl is-active docker || echo "❌ Docker is not running!"
echo ""

# Check if docker compose is available
echo "🔧 Docker Compose version:"
docker compose version
echo ""

# Navigate to deployment directory
DEPLOY_PATH="/opt/solana_balance_bot"
if [ ! -d "$DEPLOY_PATH" ]; then
    echo "❌ Deployment directory not found: $DEPLOY_PATH"
    exit 1
fi

cd $DEPLOY_PATH

# Check .env file
echo "📄 Configuration file:"
if [ -f .env ]; then
    echo "✅ .env file exists"
    echo "   Lines in .env: $(wc -l < .env)"
else
    echo "❌ .env file not found!"
fi
echo ""

# Check container status
echo "📊 Container status:"
docker compose ps
echo ""

# Check if container exists
if docker ps -a --format '{{.Names}}' | grep -q "solana-balance-bot"; then
    echo "✅ Container exists"
    
    # Check if running
    if docker ps --format '{{.Names}}' | grep -q "solana-balance-bot"; then
        echo "✅ Container is running"
    else
        echo "❌ Container is stopped"
        echo ""
        echo "📝 Last 100 log lines:"
        docker compose logs --tail=100
    fi
else
    echo "❌ Container does not exist"
fi
echo ""

# Show recent logs
echo "📝 Recent logs (last 50 lines):"
docker compose logs --tail=50
echo ""

# Check disk space
echo "💾 Disk space:"
df -h $DEPLOY_PATH
echo ""

# Check data directory
echo "📁 Data directory:"
if [ -d "data" ]; then
    ls -lh data/
else
    echo "⚠️  Data directory not found"
fi
echo ""

echo "================================================"
echo "Diagnostic commands:"
echo "================================================"
echo "View live logs:    docker compose logs -f"
echo "Restart container: docker compose restart"
echo "Rebuild & start:   docker compose up -d --build"
echo "Stop container:    docker compose down"
echo "Check config:      cat .env"
echo "Enter container:   docker compose exec solana-balance-bot bash"
echo ""
