"""Helius RPC integration for fetching Solana wallet balances."""
import asyncio
import base64
import struct
import httpx
import logging
from typing import Optional, Dict, List
from solders.pubkey import Pubkey
from spl.token.instructions import get_associated_token_address
from config import Config

logger = logging.getLogger(__name__)


class HeliusClient:
    """Async client for interacting with Helius RPC with optimized batch requests."""
    
    # Rate limiting: 10 requests per second
    RATE_LIMIT_REQUESTS = 10
    RATE_LIMIT_PERIOD = 1.0  # seconds
    
    # Batch size for getMultipleAccounts (Solana limit is 100)
    BATCH_SIZE = 100
    
    def __init__(self):
        """Initialize Helius client."""
        self.rpc_url = Config.HELIUS_RPC_URL
        self.usdt_mint = Pubkey.from_string(Config.USDT_MINT)
        self.client: Optional[httpx.AsyncClient] = None
        self._request_id = 0
        self._rate_limiter = asyncio.Semaphore(self.RATE_LIMIT_REQUESTS)
        self._rate_limit_reset_time = 0
        self._ata_cache: Dict[str, str] = {}  # Cache for Associated Token Addresses
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def _get_next_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id
    
    async def _rate_limited_request(self, payload: dict) -> dict:
        """
        Make a rate-limited request to the RPC.
        
        Args:
            payload: JSON-RPC payload
            
        Returns:
            Response JSON
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self._rate_limiter:
            # Check if we need to wait for rate limit reset
            current_time = asyncio.get_event_loop().time()
            if current_time < self._rate_limit_reset_time:
                wait_time = self._rate_limit_reset_time - current_time
                await asyncio.sleep(wait_time)
            
            # Update rate limit reset time
            self._rate_limit_reset_time = asyncio.get_event_loop().time() + (self.RATE_LIMIT_PERIOD / self.RATE_LIMIT_REQUESTS)
            
            try:
                response = await self.client.post(self.rpc_url, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP error in RPC request: {e}")
                raise
    
    def _get_ata_address(self, wallet_address: str) -> str:
        """
        Get Associated Token Address for a wallet (cached).
        
        Args:
            wallet_address: Solana wallet address
            
        Returns:
            Associated Token Address as string
        """
        if wallet_address in self._ata_cache:
            return self._ata_cache[wallet_address]
        
        try:
            wallet_pubkey = Pubkey.from_string(wallet_address)
            ata = get_associated_token_address(wallet_pubkey, self.usdt_mint)
            ata_str = str(ata)
            self._ata_cache[wallet_address] = ata_str
            return ata_str
        except Exception as e:
            logger.error(f"Error deriving ATA for {wallet_address}: {e}")
            return ""
    
    def _parse_token_account(self, account_data: Optional[dict]) -> float:
        """
        Parse token account data using fast binary parsing.
        
        Args:
            account_data: Account data from getMultipleAccounts
            
        Returns:
            USDT balance as float
        """
        if not account_data or "data" not in account_data:
            return 0.0
        
        try:
            # Decode base64 data
            raw_data = base64.b64decode(account_data["data"][0])
            
            # SPL Token account layout:
            # - Bytes 0-31: mint (32 bytes)
            # - Bytes 32-63: owner (32 bytes)
            # - Bytes 64-71: amount (uint64, little-endian)
            # - ...more fields
            
            if len(raw_data) < 72:
                return 0.0
            
            # Extract amount (8 bytes starting at byte 64)
            amount_raw = struct.unpack("<Q", raw_data[64:72])[0]
            
            # USDT has 6 decimals
            return amount_raw / 1_000_000
            
        except Exception as e:
            logger.warning(f"Error parsing token account data: {e}")
            return 0.0
    
    async def get_total_usdt_balance(self, wallet_addresses: List[str]) -> float:
        """
        Get total USDT balance across multiple wallets using optimized batch requests.
        
        Args:
            wallet_addresses: List of Solana wallet addresses
            
        Returns:
            Total USDT balance as float
        """
        if not wallet_addresses:
            return 0.0
        
        # Derive all ATA addresses
        ata_list = []
        wallet_to_ata = {}
        for wallet in wallet_addresses:
            ata = self._get_ata_address(wallet)
            if ata:
                ata_list.append(ata)
                wallet_to_ata[ata] = wallet
        
        if not ata_list:
            logger.warning("No valid wallet addresses to query")
            return 0.0
        
        total_usdt = 0.0
        
        # Process in batches of 100 (Solana's getMultipleAccounts limit)
        for i in range(0, len(ata_list), self.BATCH_SIZE):
            batch = ata_list[i:i + self.BATCH_SIZE]
            
            payload = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "getMultipleAccounts",
                "params": [
                    batch,
                    {"encoding": "base64", "commitment": "confirmed"}
                ]
            }
            
            try:
                data = await self._rate_limited_request(payload)
                
                if "error" in data:
                    logger.error(f"RPC error in batch {i}-{i+len(batch)}: {data['error']}")
                    continue
                
                result = data.get("result", {})
                accounts = result.get("value", [])
                
                # Parse each account
                for account in accounts:
                    if account:
                        balance = self._parse_token_account(account)
                        total_usdt += balance
                        
            except Exception as e:
                logger.error(f"Error fetching batch {i}-{i+len(batch)}: {e}")
                continue
        
        return total_usdt
    
    async def get_multiple_balances(self, wallet_addresses: List[str]) -> Dict[str, float]:
        """
        Get USDT balances for multiple wallet addresses (individual balances).
        
        Args:
            wallet_addresses: List of Solana wallet addresses
            
        Returns:
            Dictionary mapping address to balance
        """
        if not wallet_addresses:
            return {}
        
        # Derive all ATA addresses
        ata_list = []
        wallet_to_ata = {}
        ata_to_wallet = {}
        
        for wallet in wallet_addresses:
            ata = self._get_ata_address(wallet)
            if ata:
                ata_list.append(ata)
                wallet_to_ata[wallet] = ata
                ata_to_wallet[ata] = wallet
        
        balances = {wallet: 0.0 for wallet in wallet_addresses}
        
        # Process in batches of 100
        for i in range(0, len(ata_list), self.BATCH_SIZE):
            batch = ata_list[i:i + self.BATCH_SIZE]
            
            payload = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "getMultipleAccounts",
                "params": [
                    batch,
                    {"encoding": "base64", "commitment": "confirmed"}
                ]
            }
            
            try:
                data = await self._rate_limited_request(payload)
                
                if "error" in data:
                    logger.error(f"RPC error in batch {i}-{i+len(batch)}: {data['error']}")
                    continue
                
                result = data.get("result", {})
                accounts = result.get("value", [])
                
                # Parse each account and map back to wallet address
                for idx, account in enumerate(accounts):
                    if account and idx < len(batch):
                        ata = batch[idx]
                        wallet = ata_to_wallet.get(ata)
                        if wallet:
                            balance = self._parse_token_account(account)
                            balances[wallet] = balance
                        
            except Exception as e:
                logger.error(f"Error fetching batch {i}-{i+len(batch)}: {e}")
                continue
        
        return balances
    
    async def get_usdt_balance(self, wallet_address: str) -> float:
        """
        Get USDT balance for a single wallet address.
        
        Args:
            wallet_address: Solana wallet address
            
        Returns:
            USDT balance as float
        """
        balances = await self.get_multiple_balances([wallet_address])
        return balances.get(wallet_address, 0.0)
