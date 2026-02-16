# Solana Balance Bot

A Telegram bot that tracks USDT balances across multiple Solana wallets, sends regular updates to a Telegram channel, and alerts via Pushover when the total balance drops below a threshold.

## Features

- 📊 Track multiple Solana wallet addresses
- 💰 Real-time USDT balance monitoring using Helius RPC
- 📱 Telegram bot with interactive commands
- 📢 Automated channel notifications every 60 seconds
- 🔔 Pushover alerts when balance falls below 1,000,000 USDT
- 🗄️ SQLite database for persistent storage
- 🐳 Docker containerization for easy deployment
- 🚀 CI/CD pipeline with GitHub Actions

## Architecture

```
┌─────────────────┐
│  Telegram Bot   │ ◄─── User Commands
└────────┬────────┘
         │
         │
┌────────▼────────┐      ┌──────────────┐
│  Main App       │◄────►│   Database   │
│  (Background    │      │  (aiosqlite) │
│   Sync Loop)    │      └──────────────┘
└────────┬────────┘
         │
    ┌────┴─────┬──────────┐
    │          │          │
┌───▼───┐  ┌──▼──────┐ ┌─▼────────┐
│Helius │  │Telegram │ │ Pushover │
│  RPC  │  │ Channel │ │  Alerts  │
└───────┘  └─────────┘ └──────────┘
```

## Tech Stack

- **Python 3.11+**
- **python-telegram-bot** - Telegram bot framework
- **aiosqlite** - Async SQLite database
- **httpx** - Async HTTP client for API calls
- **Docker & Docker Compose** - Containerization
- **GitHub Actions** - CI/CD pipeline

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Display welcome message and available commands |
| `/add <addr1> <addr2> ...` | Add wallet address(es) to tracking |
| `/remove <addr1> <addr2> ...` | Remove wallet address(es) from tracking |
| `/balance` | Show total USDT balance (forces balance update) |
| `/top_5` | List top 5 wallets by USDT balance |
| `/enable_pushover <user_key>` | Subscribe to Pushover notifications |
| `/disable_pushover` | Unsubscribe from Pushover notifications |

## Database Schema

### tracked_wallets
```sql
CREATE TABLE tracked_wallets (
    address TEXT PRIMARY KEY
);
```

### balances
```sql
CREATE TABLE balances (
    address TEXT PRIMARY KEY,
    amount REAL DEFAULT 0,
    last_updated TIMESTAMP,
    FOREIGN KEY (address) REFERENCES tracked_wallets(address)
);
```

### pushover_subscriptions
```sql
CREATE TABLE pushover_subscriptions (
    user_id TEXT PRIMARY KEY,
    user_key TEXT NOT NULL
);
```

## Setup & Installation

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for containerized deployment)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Helius API Key (from [Helius](https://www.helius.dev/))
- Pushover App Token (from [Pushover](https://pushover.net/))

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd solana_balance_bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

### Docker Deployment

1. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **View logs**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the bot**
   ```bash
   docker-compose down
   ```

## VPS Deployment with GitHub Actions

### Prerequisites

1. A Linux VPS with Docker and Docker Compose installed
2. SSH access to the VPS
3. GitHub repository with the code

### Setup GitHub Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `VPS_SSH_KEY` | Private SSH key for VPS access | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `VPS_HOST` | VPS IP address or hostname | `192.168.1.100` or `myserver.com` |
| `VPS_USER` | SSH username | `root` or `ubuntu` |
| `VPS_PATH` | Deployment path on VPS | `/opt/solana_balance_bot` |

### VPS Setup

1. **SSH into your VPS**
   ```bash
   ssh user@your-vps-ip
   ```

2. **Install Docker and Docker Compose**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # Install Docker Compose
   sudo apt-get update
   sudo apt-get install docker-compose-plugin
   ```

3. **Create deployment directory**
   ```bash
   mkdir -p /opt/solana_balance_bot
   cd /opt/solana_balance_bot
   ```

4. **Create .env file**
   ```bash
   nano .env
   # Add your configuration (see .env.example)
   ```

### Deploy

Push to the `main` branch or manually trigger the workflow:

```bash
git add .
git commit -m "Deploy to production"
git push origin main
```

The GitHub Actions workflow will:
1. Connect to your VPS via SSH
2. Copy the latest code
3. Build the Docker image
4. Restart the container
5. Show deployment logs

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram bot token from BotFather |
| `TELEGRAM_CHANNEL_ID` | Yes | - | Telegram channel ID for notifications |
| `HELIUS_API_KEY` | Yes | - | Helius RPC API key |
| `PUSHOVER_APP_TOKEN` | Yes | - | Pushover application token |
| `DATABASE_PATH` | No | `./data/bot.db` | SQLite database file path |
| `SYNC_INTERVAL` | No | `60` | Balance sync interval in seconds |
| `ALERT_THRESHOLD` | No | `1000000` | USDT threshold for Pushover alerts |

### Getting API Keys

#### Telegram Bot Token
1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions
3. Save the bot token provided

#### Telegram Channel ID
1. Create a Telegram channel
2. Add your bot as an administrator
3. Use [@getidsbot](https://t.me/getidsbot) to get the channel ID
4. Format: `@channel_username` or `-100XXXXXXXXX`

#### Helius API Key
1. Visit [Helius](https://www.helius.dev/)
2. Sign up for an account
3. Create a new project
4. Copy the API key

#### Pushover App Token
1. Visit [Pushover](https://pushover.net/)
2. Create an account
3. Create a new application
4. Copy the API token

## Monitoring

### View Logs

**Docker:**
```bash
docker-compose logs -f
```

**Local:**
```bash
python main.py
```

### Check Container Status

```bash
docker-compose ps
```

### Database Inspection

```bash
sqlite3 data/bot.db
.tables
SELECT * FROM tracked_wallets;
SELECT * FROM balances;
```

## Troubleshooting

### Bot not responding
- Check if the container is running: `docker-compose ps`
- Check logs: `docker-compose logs -f`
- Verify Telegram bot token in `.env`

### No balance updates
- Verify Helius API key is valid
- Check network connectivity
- Review logs for API errors

### Pushover notifications not working
- Verify Pushover app token
- Check user keys in database
- Test with `/enable_pushover <user_key>`

### Database locked errors
- Ensure only one instance is running
- Check file permissions on `data/` directory

## Development

### Project Structure

```
solana_balance_bot/
├── .github/
│   └── workflows/
│       └── deploy.yml       # GitHub Actions CI/CD
├── bot.py                   # Telegram bot handlers
├── config.py                # Configuration management
├── database.py              # Database operations
├── helius.py                # Helius RPC client
├── main.py                  # Main application entry point
├── pushover.py              # Pushover notification client
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker image definition
├── docker-compose.yml       # Docker Compose configuration
├── .env.example             # Example environment variables
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

### Adding New Features

1. Create a new branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Test locally
4. Commit and push: `git push origin feature/my-feature`
5. Create a pull request

## Security Considerations

- ⚠️ Never commit `.env` file to Git
- ⚠️ Keep SSH keys secure
- ⚠️ Use environment variables for all secrets
- ⚠️ Regularly update dependencies
- ⚠️ Limit SSH access to your VPS
- ⚠️ Use strong passwords and keys

## License

MIT License - feel free to use this project for your own purposes.

## Support

For issues, questions, or contributions, please open an issue on GitHub.

## Acknowledgments

- [Helius](https://www.helius.dev/) - Solana RPC provider
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram bot framework
- [Pushover](https://pushover.net/) - Push notification service
