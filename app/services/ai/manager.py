"""
AI Provider Manager
"""

import logging
from typing import Dict, Optional

from app.config.settings import settings
from app.services.ai.gemini import GeminiProvider

logger = logging.getLogger(__name__)

class AIManager:
    """Manages AI provider instances and operations"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.providers = {}
            self.active_provider = None
            self.initialized = False
    
    async def initialize(self):
        """Initialize AI providers"""
        if self.initialized:
            return
        
        try:
            # Initialize Gemini provider
            gemini_provider = GeminiProvider()
            self.providers['gemini'] = gemini_provider
            
            # Set as active provider
            self.active_provider = gemini_provider
            
            self.initialized = True
            logger.info("AI Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Manager: {e}", exc_info=True)
            raise
    
    async def generate_outfit(self, prompt: str, user_profile: Dict) -> Optional[Dict]:
        """
        Generate outfit using active AI provider
        
        Args:
            prompt: Prompt text for AI
            user_profile: User profile data
            
        Returns:
            Dict with AI response or None if failed
        """
        if not self.active_provider:
            logger.error("No active AI provider configured")
            return None
            
        try:
            result = await self.active_provider.generate_outfit(prompt, user_profile)
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate outfit: {e}", exc_info=True)
            return None
    
    def build_prompt(self, user_profile: Dict, season: str) -> str:
        """
        Build prompt using active provider
        
        Args:
            user_profile: User profile data
            season: Season for outfit
            
        Returns:
            Formatted prompt string
        """
        if not self.active_provider:
            logger.error("No active AI provider configured")
            return ""
            
        return self.active_provider.build_prompt(user_profile, season)
    
    def format_response(self, ai_response: str) -> str:
        """
        Format AI response using active provider
        
        Args:
            ai_response: Raw AI response
            
        Returns:
            Formatted response string
        """
        if not self.active_provider:
            logger.error("No active AI provider configured")
            return ai_response
            
        return self.active_provider.format_outfit_response(ai_response)


# Global instance
_manager = AIManager()

async def init_ai_manager():
    """Initialize global AI manager instance"""
    await _manager.initialize()

def get_ai_manager() -> AIManager:
    """Get global AI manager instance"""
    return _manager