"""Database module for managing wallets, balances, and Pushover subscriptions."""
import aiosqlite
from datetime import datetime
from typing import List, Optional, Tuple
from config import Config


class Database:
    """Async database handler using aiosqlite."""
    
    def __init__(self, db_path: str = None):
        """Initialize database handler."""
        self.db_path = db_path or Config.DATABASE_PATH
        self.db: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Connect to the database and create tables if needed."""
        self.db = await aiosqlite.connect(self.db_path)
        await self._create_tables()
    
    async def close(self):
        """Close the database connection."""
        if self.db:
            await self.db.close()
    
    async def _create_tables(self):
        """Create necessary tables if they don't exist."""
        async with self.db.cursor() as cursor:
            # Tracked wallets table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracked_wallets (
                    address TEXT PRIMARY KEY
                )
            """)
            
            # Balances table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS balances (
                    address TEXT PRIMARY KEY,
                    amount REAL DEFAULT 0,
                    last_updated TIMESTAMP,
                    FOREIGN KEY (address) REFERENCES tracked_wallets(address)
                        ON DELETE CASCADE
                )
            """)
            
            # Pushover subscriptions table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS pushover_subscriptions (
                    user_id TEXT PRIMARY KEY,
                    user_key TEXT NOT NULL
                )
            """)
            
            await self.db.commit()
    
    # Wallet management
    async def add_wallets(self, addresses: List[str]) -> int:
        """Add multiple wallet addresses to tracked_wallets."""
        async with self.db.cursor() as cursor:
            added = 0
            for address in addresses:
                try:
                    await cursor.execute(
                        "INSERT INTO tracked_wallets (address) VALUES (?)",
                        (address,)
                    )
                    # Initialize balance entry
                    await cursor.execute(
                        "INSERT INTO balances (address, amount, last_updated) VALUES (?, 0, ?)",
                        (address, datetime.now())
                    )
                    added += 1
                except aiosqlite.IntegrityError:
                    # Address already exists, skip
                    pass
            await self.db.commit()
            return added
    
    async def remove_wallets(self, addresses: List[str]) -> int:
        """Remove wallet addresses from tracked_wallets."""
        async with self.db.cursor() as cursor:
            removed = 0
            for address in addresses:
                # Remove from balances first
                await cursor.execute("DELETE FROM balances WHERE address = ?", (address,))
                # Remove from tracked_wallets
                result = await cursor.execute(
                    "DELETE FROM tracked_wallets WHERE address = ?",
                    (address,)
                )
                removed += result.rowcount
            await self.db.commit()
            return removed
    
    async def get_all_wallets(self) -> List[str]:
        """Get all tracked wallet addresses."""
        async with self.db.cursor() as cursor:
            await cursor.execute("SELECT address FROM tracked_wallets")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    # Balance management
    async def update_balance(self, address: str, amount: float):
        """Update balance for a specific wallet."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO balances (address, amount, last_updated)
                VALUES (?, ?, ?)
                ON CONFLICT(address) DO UPDATE SET
                    amount = excluded.amount,
                    last_updated = excluded.last_updated
            """, (address, amount, datetime.now()))
            await self.db.commit()
    
    async def get_balance(self, address: str) -> Optional[float]:
        """Get balance for a specific wallet."""
        async with self.db.cursor() as cursor:
            await cursor.execute(
                "SELECT amount FROM balances WHERE address = ?",
                (address,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None
    
    async def get_all_balances(self) -> List[Tuple[str, float]]:
        """Get all wallet balances."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                SELECT address, amount FROM balances
                ORDER BY amount DESC
            """)
            return await cursor.fetchall()
    
    async def get_total_balance(self) -> float:
        """Get the sum of all wallet balances."""
        async with self.db.cursor() as cursor:
            await cursor.execute("SELECT SUM(amount) FROM balances")
            row = await cursor.fetchone()
            return row[0] if row and row[0] else 0.0
    
    async def get_top_wallets(self, limit: int = 5) -> List[Tuple[str, float]]:
        """Get top N wallets by balance."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                SELECT address, amount FROM balances
                ORDER BY amount DESC
                LIMIT ?
            """, (limit,))
            return await cursor.fetchall()
    
    # Pushover subscriptions
    async def add_pushover_subscription(self, user_id: str, user_key: str) -> bool:
        """Add or update a Pushover subscription."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO pushover_subscriptions (user_id, user_key)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    user_key = excluded.user_key
            """, (user_id, user_key))
            await self.db.commit()
            return True
    
    async def remove_pushover_subscription(self, user_id: str) -> bool:
        """Remove a Pushover subscription."""
        async with self.db.cursor() as cursor:
            result = await cursor.execute(
                "DELETE FROM pushover_subscriptions WHERE user_id = ?",
                (user_id,)
            )
            await self.db.commit()
            return result.rowcount > 0
    
    async def get_all_pushover_subscriptions(self) -> List[Tuple[str, str]]:
        """Get all Pushover subscriptions (user_id, user_key)."""
        async with self.db.cursor() as cursor:
            await cursor.execute("SELECT user_id, user_key FROM pushover_subscriptions")
            return await cursor.fetchall()
