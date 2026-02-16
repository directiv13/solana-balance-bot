"""Configuration module for the Solana balance bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
    
    # Helius RPC
    HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
    HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    
    # Pushover
    PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN")
    
    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/bot.db")
    
    # Sync settings
    SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "60"))
    
    # Alert settings
    ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "1000000"))
    
    # USDT Mint Address on Solana
    USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        required = [
            ("TELEGRAM_BOT_TOKEN", cls.TELEGRAM_BOT_TOKEN),
            ("TELEGRAM_CHANNEL_ID", cls.TELEGRAM_CHANNEL_ID),
            ("HELIUS_API_KEY", cls.HELIUS_API_KEY),
            ("PUSHOVER_APP_TOKEN", cls.PUSHOVER_APP_TOKEN),
        ]
        
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        # Ensure database directory exists
        db_path = Path(cls.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
