"""Pushover integration for sending push notifications."""
import httpx
import logging
from typing import List
from config import Config

logger = logging.getLogger(__name__)


class PushoverClient:
    """Client for sending Pushover notifications."""
    
    PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
    
    def __init__(self):
        """Initialize Pushover client."""
        self.app_token = Config.PUSHOVER_APP_TOKEN
    
    async def send_alert(self, user_keys: List[str], title: str, message: str, priority: int = 1):
        """
        Send a Pushover alert to multiple users.
        
        Args:
            user_keys: List of Pushover user keys
            title: Notification title
            message: Notification message
            priority: Priority level (-2 to 2, default 1 for high priority)
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            for user_key in user_keys:
                try:
                    payload = {
                        "token": self.app_token,
                        "user": user_key,
                        "title": title,
                        "message": message,
                        "priority": priority,
                    }
                    
                    response = await client.post(self.PUSHOVER_API_URL, data=payload)
                    response.raise_for_status()
                    
                    result = response.json()
                    if result.get("status") != 1:
                        logger.error(f"Pushover error for user {user_key}: {result}")
                    else:
                        logger.info(f"Pushover alert sent to user {user_key}")
                        
                except httpx.HTTPError as e:
                    logger.error(f"HTTP error sending Pushover to {user_key}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error sending Pushover to {user_key}: {e}")
