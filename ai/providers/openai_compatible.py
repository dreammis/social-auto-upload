"""OpenAI Compatible 提供商"""

from openai import AsyncOpenAI
from ai.providers.base import BaseAIProvider
from utils.log import taobao_guanghe_logger


class OpenAICompatibleProvider(BaseAIProvider):
    """OpenAI Compatible API 提供商"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs
    ) -> str:
        """生成文本"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )

            content = response.choices[0].message.content
            taobao_guanghe_logger.info(f"🤖 AI 生成成功 ({self.model})")
            return content.strip()

        except Exception as e:
            taobao_guanghe_logger.error(f"❌ AI 生成失败: {str(e)}")
            raise
