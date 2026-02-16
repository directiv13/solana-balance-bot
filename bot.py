"""Telegram bot handlers for managing wallets and viewing balances."""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from database import Database
from helius import HeliusClient
from config import Config

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for wallet management and balance queries."""
    
    def __init__(self, db: Database):
        """Initialize Telegram bot."""
        self.db = db
        self.application = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""

        welcome_message = (
            "🤖 *Solana Wallet Balance Bot*\n\n"
            "Available commands:\n"
        )
        
        if self._is_admin(update.effective_user.id):
            welcome_message += (
                "/add <addr1> <addr2> ... - Add wallet(s) to tracking\n"
                "/remove <addr1> <addr2> ... - Remove wallet(s) from tracking\n"
                "/balance - Show total USDT balance (forces update)\n"
            )

        welcome_message += (
            "/top_5 - List top 5 wallets by USDT balance\n"
            "/enable_pushover <user_key> - Subscribe to Pushover alerts\n"
            "/disable_pushover - Unsubscribe from Pushover alerts"
        )
        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command to add wallet addresses."""

        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text(
                "❌ You do not have permission to use this command."
            )
            return

        if not context.args:
            await update.message.reply_text(
                "❌ Please provide at least one wallet address.\n"
                "Usage: /add <address1> <address2> ..."
            )
            return
        
        addresses = context.args
        added = await self.db.add_wallets(addresses)
        
        if added == 0:
            await update.message.reply_text(
                "ℹ️ All provided addresses are already being tracked."
            )
        else:
            await update.message.reply_text(
                f"✅ Successfully added {added} wallet(s) to tracking."
            )
    
    async def remove_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remove command to remove wallet addresses."""

        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text(
                "❌ You do not have permission to use this command."
            )
            return

        if not context.args:
            await update.message.reply_text(
                "❌ Please provide at least one wallet address.\n"
                "Usage: /remove <address1> <address2> ..."
            )
            return
        
        addresses = context.args
        removed = await self.db.remove_wallets(addresses)
        
        if removed == 0:
            await update.message.reply_text(
                "ℹ️ None of the provided addresses were being tracked."
            )
        else:
            await update.message.reply_text(
                f"✅ Successfully removed {removed} wallet(s) from tracking."
            )
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command to show total balance with forced update."""

        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text(
                "❌ You do not have permission to use this command."
            )
            return

        await update.message.reply_text("🔄 Fetching latest balances...")
        
        # Get all wallets
        wallets = await self.db.get_all_wallets()
        
        if not wallets:
            await update.message.reply_text(
                "ℹ️ No wallets are being tracked. Use /add to add wallets."
            )
            return
        
        # Fetch fresh balances from Helius
        async with HeliusClient() as helius:
            balances = await helius.get_multiple_balances(wallets)
        
        # Update database
        for address, balance in balances.items():
            await self.db.update_balance(address, balance)
        
        # Calculate total
        total = sum(balances.values())
        
        await update.message.reply_text(
            f"💰 *Total USDT Balance*\n\n"
            f"Tracked Wallets: {len(wallets)}\n"
            f"Total Balance: {total:,.2f} USDT",
            parse_mode="Markdown"
        )
    
    async def top_5_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /top_5 command to show top 5 wallets by balance."""
        top_wallets = await self.db.get_top_wallets(5)
        
        if not top_wallets:
            await update.message.reply_text(
                "ℹ️ No wallets are being tracked. Use /add to add wallets."
            )
            return
        
        message = "🏆 *Top 5 Wallets by USDT Balance*\n\n"
        for idx, (address, balance) in enumerate(top_wallets, 1):
            # Truncate address for readability
            short_addr = f"{address[:4]}...{address[-4:]}"
            message += f"{idx}. `{short_addr}` - {balance:,.2f} USDT\n"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def enable_pushover_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /enable_pushover command to subscribe to Pushover notifications."""
        if not context.args or len(context.args) != 1:
            await update.message.reply_text(
                "❌ Please provide your Pushover user key.\n"
                "Usage: /enable_pushover <user_key>"
            )
            return
        
        user_id = str(update.effective_user.id)
        user_key = context.args[0]
        
        await self.db.add_pushover_subscription(user_id, user_key)
        
        await update.message.reply_text(
            "✅ Pushover notifications enabled!\n"
            "You will receive alerts when total USDT balance falls below 1,000,000."
        )
    
    async def disable_pushover_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /disable_pushover command to unsubscribe from Pushover notifications."""
        user_id = str(update.effective_user.id)
        removed = await self.db.remove_pushover_subscription(user_id)
        
        if removed:
            await update.message.reply_text(
                "✅ Pushover notifications disabled."
            )
        else:
            await update.message.reply_text(
                "ℹ️ You were not subscribed to Pushover notifications."
            )
    
    def setup_handlers(self, application: Application):
        """Set up command handlers."""
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("add", self.add_command))
        application.add_handler(CommandHandler("remove", self.remove_command))
        application.add_handler(CommandHandler("balance", self.balance_command))
        application.add_handler(CommandHandler("top_5", self.top_5_command))
        application.add_handler(CommandHandler("enable_pushover", self.enable_pushover_command))
        application.add_handler(CommandHandler("disable_pushover", self.disable_pushover_command))
    
    def build_application(self) -> Application:
        """Build and return the Telegram application."""
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers(application)
        self.application = application
        return application
    
    def _is_admin(self, user_id: int) -> bool:
        """Check if a user is an admin."""
        return user_id in Config.ADMIN_USER_IDS
