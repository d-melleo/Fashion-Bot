import logging
from app.config.ngrok import NgrokConfig

logger = logging.getLogger(__name__)

async def initialize_ngrok_url():
    """Initialize ngrok URL for webhook"""
    try:
        logger.info("🌐 Initializing ngrok URL...")
        url = await NgrokConfig.get_public_url_with_retries(max_retries=10, delay=1)
        logger.info(f"✅ Ngrok URL initialized: {url}")
        return url
    except Exception as e:
        logger.error(f"Failed to initialize ngrok URL: {e}")
        return "http://localhost:8000"