import os
import httpx
from typing import Optional
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class NgrokConfig:
    """Manage ngrok tunnel URL"""
    
    _url: Optional[str] = None
    
    @classmethod
    async def get_public_url(cls) -> str:
        """Get ngrok public URL"""
        if cls._url:
            return cls._url
        
        # Try environment variable first
        # env_url = os.getenv("NGROK_PUBLIC_URL")
        # if env_url and (env_url.startswith('https://') or env_url.startswith('http://')):
        #     cls._url = env_url
        #     logger.info(f"✅ Loaded ngrok URL from environment: {env_url}")
        #     return env_url
        
        # Try to read from file (for local testing)
        url_file = Path("/tmp/shared/ngrok_url.txt")
        if url_file.exists():
            try:
                with open(url_file, 'r') as f:
                    url = f.read().strip()
                    if url and (url.startswith('https://') or url.startswith('http://')):
                        cls._url = url
                        logger.info(f"✅ Loaded ngrok URL from file: {url}")
                        return url
            except Exception as e:
                logger.debug(f"Error reading ngrok URL file: {e}")
        
        # Try ngrok API endpoint
        endpoints = [
            ("http://localhost:4040/api/tunnels", "Localhost"),
            ("http://127.0.0.1:4040/api/tunnels", "Loopback"),
            ("http://webapp:4040/api/tunnels", "Docker Network"),
        ]
        
        for endpoint, label in endpoints:
            try:
                logger.debug(f"Trying {label}: {endpoint}")
                async with httpx.AsyncClient(timeout=3.0, verify=False) as client:
                    resp = await client.get(endpoint)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("tunnels"):
                            for tunnel in data["tunnels"]:
                                if tunnel.get("proto") == "https":
                                    cls._url = tunnel["public_url"]
                                    logger.info(f"✅ Retrieved ngrok URL from {label}: {cls._url}")
                                    return cls._url
            except Exception as e:
                logger.debug(f"Error with {label}: {type(e).__name__}: {e}")
        
        logger.warning("⚠️  Could not get ngrok URL")
        return "http://localhost:8000"
    
    @classmethod
    async def get_public_url_with_retries(cls, max_retries: int = 10, delay: int = 2) -> str:
        """Get ngrok URL with retry logic"""
        for attempt in range(max_retries):
            url = await cls.get_public_url()
            if url != "http://localhost:8000":
                return url
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying ngrok URL... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
        
        logger.warning(f"Failed to get ngrok URL after {max_retries} attempts, using fallback")
        return "http://localhost:8000"
    
    @classmethod
    def set_url(cls, url: str) -> None:
        """Manually set ngrok URL"""
        cls._url = url
        logger.info(f"✅ ngrok URL set to: {url}")
    
    @classmethod
    def reset(cls) -> None:
        """Reset cached URL"""
        cls._url = None
        logger.info("ngrok URL cache reset")