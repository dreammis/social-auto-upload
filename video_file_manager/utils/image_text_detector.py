"""
图片文字识别器
用于识别图片中最大的文字，基于DeepSeek VL2模型实现
"""
from pathlib import Path
from typing import Union, Optional, Dict, Any, List
import logging
import aiohttp
import asyncio
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class APIError(Exception):
    """API调用相关错误"""
    pass

class ImageTextDetector:
    """
    图片文字识别器 - 专门用于识别图片中最大的文字
    基于DeepSeek VL2模型实现
    """
    def __init__(
        self, 
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: str = "Qwen/Qwen2-VL-72B-Instruct",
        timeout: int = 30,
        max_retries: int = 3,
        max_concurrent: int = 5  # 最大并发数
    ):
        """
        初始化图片文字识别器
        
        Args:
            api_key: SiliconFlow API密钥（可选，默认从环境变量获取）
            api_base: API基础URL（可选，默认从环境变量获取）
            model: 使用的模型名称
            timeout: API调用超时时间（秒）
            max_retries: 最大重试次数
            max_concurrent: 最大并发请求数
        """
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        if not self.api_key:
            raise ValueError("未设置API密钥，请在.env文件中设置SILICONFLOW_API_KEY")
            
        self.api_base = (api_base or os.getenv('SILICONFLOW_API_BASE', 'https://api.siliconflow.cn/v1')).rstrip('/')
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_concurrent = max_concurrent
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """确保aiohttp会话存在"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._session
        
    async def _ensure_semaphore(self) -> asyncio.Semaphore:
        """确保信号量存在"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def detect_text(
        self, 
        image_url: str,
        prompt: str = "请识别这张图片中最大的文字是什么？只需要返回文字内容，不需要其他解释。",
        stop: list = []
    ) -> str:
        """
        识别单个图片中的文字
        
        Args:
            image_url: 图片URL
            prompt: 提示词
            stop: 停止词列表
            
        Returns:
            str: 识别出的文字
            
        Raises:
            ValueError: 图片URL无效
            APIError: API调用失败
        """
        try:
            # 验证URL格式
            parsed_url = urlparse(image_url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                raise ValueError(f"无效的图片URL: {image_url}")
            
            # 准备API请求数据
            payload = {
                "model": self.model,
                "stop": stop,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            # 获取信号量
            semaphore = await self._ensure_semaphore()
            
            # 发送API请求
            session = await self._ensure_session()
            async with semaphore:  # 使用信号量控制并发
                for attempt in range(self.max_retries):
                    try:
                        async with session.post(
                            f"{self.api_base}/chat/completions",
                            json=payload,
                            timeout=self.timeout
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                text = result["choices"][0]["message"]["content"].strip()
                                
                                # 移除可能存在的格式标记和额外空格
                                text = text.replace("{", "").replace("}", "").replace("标题简称：", "").strip()
                                return text
                                
                            else:
                                error_text = await response.text()
                                raise APIError(f"API调用失败 (HTTP {response.status}): {error_text}")
                                
                    except asyncio.TimeoutError:
                        if attempt == self.max_retries - 1:
                            raise APIError(f"API调用超时（已重试{attempt + 1}次）")
                        logger.warning(f"API调用超时，正在重试（第{attempt + 1}次）...")
                        await asyncio.sleep(1 * (attempt + 1))  # 指数退避
                        
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            raise APIError(f"API调用失败: {str(e)}")
                        logger.warning(f"API调用失败，正在重试（第{attempt + 1}次）: {str(e)}")
                        await asyncio.sleep(1 * (attempt + 1))
                    
        except Exception as e:
            logger.error(f"识别失败: {str(e)}")
            raise

    async def detect_batch(
        self,
        image_urls: List[str],
        prompt: str = "请识别这张图片中最大的文字是什么？只需要返回文字内容，不需要其他解释。",
        stop: list = []
    ) -> List[Dict[str, str]]:
        """
        批量识别多个图片中的文字
        
        Args:
            image_urls: 图片URL列表
            prompt: 提示词
            stop: 停止词列表
            
        Returns:
            List[Dict[str, str]]: 识别结果列表，每个元素为 {"url": "图片URL", "text": "识别结果", "error": "错误信息"}
        """
        tasks = []
        for url in image_urls:
            task = asyncio.create_task(self._process_single_url(url, prompt, stop))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for url, result in zip(image_urls, results):
            if isinstance(result, Exception):
                processed_results.append({
                    "url": url,
                    "text": None,
                    "error": str(result)
                })
            else:
                processed_results.append({
                    "url": url,
                    "text": result,
                    "error": None
                })
        
        return processed_results
    
    async def _process_single_url(self, url: str, prompt: str, stop: list) -> str:
        """处理单个URL的包装方法，用于错误处理"""
        try:
            return await self.detect_text(url, prompt, stop)
        except Exception as e:
            raise e
            
    async def close(self):
        """关闭资源"""
        if self._session and not self._session.closed:
            await self._session.close()
            
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

# 创建默认实例
detector = ImageTextDetector() 