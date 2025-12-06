import asyncio
import logging
from app.bot import bot, dp, setup_bot, shutdown_bot
from app.services.webapp.ngrok_helper import initialize_ngrok_url
from app.utils.logger import setup_logger

logger = logging.getLogger(__name__)

async def main():
    # Initialize ngrok URL
    await initialize_ngrok_url()
    
    # Setup logging
    setup_logger()
    
    try:
        # Initialize bot
        await setup_bot()
        
        # Start polling
        await dp.start_polling(bot)
    finally:
        await shutdown_bot()

if __name__ == "__main__":
    asyncio.run(main())