"""Main application entry point with background sync and alert logic."""
import asyncio
import logging
from datetime import datetime
from telegram.ext import Application
from database import Database
from helius import HeliusClient
from pushover import PushoverClient
from bot import TelegramBot
from config import Config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class BalanceMonitor:
    """Monitor wallet balances and send alerts."""
    
    def __init__(self, db: Database, telegram_app: Application):
        """Initialize balance monitor."""
        self.db = db
        self.telegram_app = telegram_app
        self.pushover = PushoverClient()
        self.last_alert_state = None  # Track if we're above or below threshold
        self.running = False
    
    async def sync_balances(self) -> float:
        """
        Sync all wallet balances from Helius using optimized batch requests.
        
        Uses getMultipleAccounts with batches of 100 wallets per request
        and binary parsing for maximum performance. Rate limited to 10 req/s.
        
        Returns:
            Total USDT balance across all wallets
        """
        wallets = await self.db.get_all_wallets()
        
        if not wallets:
            logger.info("No wallets to sync")
            return 0.0
        
        logger.info(f"Syncing balances for {len(wallets)} wallet(s)")
        
        # Fetch balances from Helius using optimized batch requests
        # This uses getMultipleAccounts (100 wallets per request) with binary parsing
        async with HeliusClient() as helius:
            balances = await helius.get_multiple_balances(wallets)
        
        # Update database with individual balances
        for address, balance in balances.items():
            await self.db.update_balance(address, balance)
        
        total = sum(balances.values())
        logger.info(f"Total USDT balance: {total:,.2f}")
        
        return total
    
    async def send_telegram_notification(self, total_balance: float):
        """Send balance notification to Telegram channel."""
        try:
            wallet_count = len(await self.db.get_all_wallets())
            message = (
                f"📊 *Balance Update*\n\n"
                f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"💼 Tracked Wallets: {wallet_count}\n"
                f"💰 Total USDT: {total_balance:,.2f}\n"
            )
            
            if total_balance < Config.ALERT_THRESHOLD_LOW:
                message += f"\n⚠️ *Alert: Balance below {Config.ALERT_THRESHOLD_LOW:,.0f} USDT threshold!*"
            elif total_balance > Config.ALERT_THRESHOLD_HIGH:
                message += f"\n🎉 *Alert: Balance exceeds {Config.ALERT_THRESHOLD_HIGH:,.0f} USDT threshold!*"
            
            await self.telegram_app.bot.send_message(
                chat_id=Config.TELEGRAM_CHANNEL_ID,
                text=message,
                parse_mode="Markdown"
            )
            logger.info("Telegram notification sent")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
    
    async def check_and_send_alerts(self, total_balance: float):
        """Check thresholds and send Pushover alerts if needed."""
        # Determine current state
        if total_balance < Config.ALERT_THRESHOLD_LOW:
            current_state = "low"
        elif total_balance > Config.ALERT_THRESHOLD_HIGH:
            current_state = "high"
        else:
            current_state = "normal"
        
        # Send alert only when crossing a threshold (state change)
        if current_state != self.last_alert_state:
            # Get all Pushover subscriptions
            subscriptions = await self.db.get_all_pushover_subscriptions()
            
            if subscriptions:
                user_keys = [user_key for _, user_key in subscriptions]
                
                # Send appropriate alert based on state
                if current_state == "low":
                    logger.warning(f"Balance below LOW threshold: {total_balance:,.2f} USDT")
                    await self.pushover.send_alert(
                        user_keys=user_keys,
                        title="⚠️ Low USDT Balance Alert",
                        message=f"Total balance dropped to {total_balance:,.2f} USDT (below {Config.ALERT_THRESHOLD_LOW:,.0f})",
                        priority=1
                    )
                    logger.info(f"LOW threshold alert sent to {len(user_keys)} subscriber(s)")
                    
                elif current_state == "high":
                    logger.warning(f"Balance above HIGH threshold: {total_balance:,.2f} USDT")
                    await self.pushover.send_alert(
                        user_keys=user_keys,
                        title="🎉 High USDT Balance Alert",
                        message=f"Total balance reached {total_balance:,.2f} USDT (above {Config.ALERT_THRESHOLD_HIGH:,.0f})",
                        priority=1
                    )
                    logger.info(f"HIGH threshold alert sent to {len(user_keys)} subscriber(s)")
                    
                elif current_state == "normal" and self.last_alert_state is not None:
                    # Balance returned to normal range (between thresholds)
                    logger.info(f"Balance returned to normal range: {total_balance:,.2f} USDT")
            
            # Update state
            self.last_alert_state = current_state
    
    async def sync_loop(self):
        """Main sync loop that runs every SYNC_INTERVAL seconds."""
        logger.info(f"Starting sync loop (interval: {Config.SYNC_INTERVAL}s)")
        self.running = True
        
        while self.running:
            try:
                # Sync balances
                total_balance = await self.sync_balances()
                
                # Send Telegram notification
                await self.send_telegram_notification(total_balance)
                
                # Check alerts
                await self.check_and_send_alerts(total_balance)
                
            except Exception as e:
                logger.error(f"Error in sync loop: {e}", exc_info=True)
            
            # Wait for next sync
            await asyncio.sleep(Config.SYNC_INTERVAL)
    
    def stop(self):
        """Stop the sync loop."""
        logger.info("Stopping sync loop")
        self.running = False


async def main():
    """Main application entry point."""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated")
        
        # Initialize database
        db = Database()
        await db.connect()
        logger.info("Database connected")
        
        # Build Telegram bot
        telegram_bot = TelegramBot(db)
        application = telegram_bot.build_application()
        
        # Initialize application
        await application.initialize()
        await application.start()
        logger.info("Telegram bot started")
        
        # Start polling in the background
        asyncio.create_task(application.updater.start_polling())
        
        # Start balance monitor
        monitor = BalanceMonitor(db, application)
        
        try:
            # Run sync loop
            await monitor.sync_loop()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            # Cleanup
            monitor.stop()
            await application.stop()
            await application.shutdown()
            await db.close()
            logger.info("Application shutdown complete")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
