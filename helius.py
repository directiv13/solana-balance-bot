"""Helius RPC integration for fetching Solana wallet balances."""
import httpx
import logging
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)


class HeliusClient:
    """Async client for interacting with Helius RPC."""
    
    def __init__(self):
        """Initialize Helius client."""
        self.rpc_url = Config.HELIUS_RPC_URL
        self.usdt_mint = Config.USDT_MINT
        self.client: Optional[httpx.AsyncClient] = None
        self._request_id = 0
    
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
    
    async def get_usdt_balance(self, wallet_address: str) -> float:
        """
        Get USDT balance for a wallet address.
        
        Args:
            wallet_address: Solana wallet address
            
        Returns:
            USDT balance as float (in USDT, not lamports)
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        payload = {
            "method": "getTokenAccountsByOwner",
            "jsonrpc": "2.0",
            "params": [
                wallet_address,
                {"mint": self.usdt_mint},
                {"encoding": "jsonParsed", "commitment": "confirmed"}
            ],
            "id": self._get_next_id()
        }
        
        try:
            response = await self.client.post(self.rpc_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                logger.error(f"RPC error for {wallet_address}: {data['error']}")
                return 0.0
            
            result = data.get("result", {})
            value = result.get("value", [])
            
            if not value:
                # No USDT token accounts found
                return 0.0
            
            # Sum up all USDT token accounts (usually just one)
            total_balance = 0.0
            for account in value:
                try:
                    token_amount = account["account"]["data"]["parsed"]["info"]["tokenAmount"]
                    ui_amount = token_amount.get("uiAmount", 0.0)
                    if ui_amount:
                        total_balance += ui_amount
                except (KeyError, TypeError) as e:
                    logger.warning(f"Error parsing token amount for {wallet_address}: {e}")
                    continue
            
            return total_balance
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching balance for {wallet_address}: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"Unexpected error fetching balance for {wallet_address}: {e}")
            return 0.0
    
    async def get_multiple_balances(self, wallet_addresses: list[str]) -> dict[str, float]:
        """
        Get USDT balances for multiple wallet addresses.
        
        Args:
            wallet_addresses: List of Solana wallet addresses
            
        Returns:
            Dictionary mapping address to balance
        """
        balances = {}
        for address in wallet_addresses:
            balance = await self.get_usdt_balance(address)
            balances[address] = balance
        
        return balances
