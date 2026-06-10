"""AI 管理器"""

from pathlib import Path
from typing import Dict
import yaml

from ai.providers.base import BaseAIProvider
from ai.providers.openai_compatible import OpenAICompatibleProvider
from utils.log import taobao_guanghe_logger


class AIManager:
    """AI 管理器"""

    def __init__(self, config_file: Path = Path("ai_config.yaml")):
        self.config_file = config_file
        self.config = self._load_config()
        self.providers: Dict[str, BaseAIProvider] = {}
        self.prompts = self.config.get('prompts', {})

        self._init_providers()

    def _load_config(self) -> dict:
        """加载配置文件"""
        if not self.config_file.exists():
            taobao_guanghe_logger.warning(f"⚠️ AI 配置文件不存在: {self.config_file}")
            return {}

        with open(self.config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _init_providers(self):
        """初始化 AI 提供商"""
        providers_config = self.config.get('providers', {})

        for name, config in providers_config.items():
            if not config.get('api_key'):
                continue

            try:
                if name in ['openai', 'qwen', 'deepseek']:
                    self.providers[name] = OpenAICompatibleProvider(config)

                taobao_guanghe_logger.info(f"✅ 初始化 AI 提供商: {name}")
            except Exception as e:
                taobao_guanghe_logger.error(f"❌ 初始化 {name} 失败: {str(e)}")

    def get_provider(self, name: str = None) -> BaseAIProvider:
        """获取 AI 提供商"""
        if name is None:
            name = self.config.get('default_provider', 'qwen')

        if name not in self.providers:
            raise ValueError(f"AI 提供商 {name} 未配置或不可用")

        return self.providers[name]

    async def generate_title(
        self,
        filename: str = "",
        description: str = "",
        keywords: str = "",
        provider: str = None,
    ) -> str:
        """生成标题"""
        prompt_config = self.prompts.get('title', {})
        system_prompt = prompt_config.get('system', '')
        template = prompt_config.get('template', '')

        prompt = template.format(
            filename=filename,
            description=description or "无",
            keywords=keywords or "无"
        )

        ai_provider = self.get_provider(provider)
        return await ai_provider.generate(prompt, system_prompt)

    async def generate_description(
        self,
        title: str,
        filename: str = "",
        keywords: str = "",
        provider: str = None,
    ) -> str:
        """生成描述"""
        prompt_config = self.prompts.get('description', {})
        system_prompt = prompt_config.get('system', '')
        template = prompt_config.get('template', '')

        prompt = template.format(
            title=title,
            filename=filename or "无",
            keywords=keywords or "无"
        )

        ai_provider = self.get_provider(provider)
        return await ai_provider.generate(prompt, system_prompt)

    async def generate_tags(
        self,
        title: str,
        description: str = "",
        provider: str = None,
    ) -> list[str]:
        """生成标签"""
        prompt_config = self.prompts.get('tags', {})
        system_prompt = prompt_config.get('system', '')
        template = prompt_config.get('template', '')

        prompt = template.format(
            title=title,
            description=description or "无"
        )

        ai_provider = self.get_provider(provider)
        result = await ai_provider.generate(prompt, system_prompt)

        tags = [tag.strip() for tag in result.split(',') if tag.strip()]
        return tags
