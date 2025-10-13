from app.services.ai.base import BaseAIProvider

class GeminiProvider(BaseAIProvider):
    async def generate_outfit(self, prompt: str, user_profile: dict):
        pass