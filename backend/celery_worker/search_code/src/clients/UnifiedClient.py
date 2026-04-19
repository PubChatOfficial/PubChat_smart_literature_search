"""
统一 AI 客户端

使用 LangChain 统一管理所有 AI 提供商，同时保留原有的：
- 多 API 密钥轮询
- 自动重试机制
- Token 使用统计
- Pro/Flash 模型分层
"""

import os
import logging
import random
import threading
import time
from collections import defaultdict
from typing import Optional
import requests

from langchain_core.messages import HumanMessage

# 本地导入
# from .AIModelProvider import get_provider_config, get_available_providers, ProviderConfig
from .AIPrompts import BaseClient, APIKeyManager

# 配置日志
logger = logging.getLogger(__name__)

# 线程本地变量，用于跟踪当前使用的 Key 编号
_thread_local = threading.local()


class KeyPool:
    """
    智能 Key 管理池（线程安全）
    
    当某个 Key 报以下错误时标记为"已耗尽"，本次任务不再使用它，
    直到所有 Key 都耗尽后才重置：
    - 429 (Too Many Requests) - 限流/配额耗尽
    - 401 (Unauthorized) - API Key 无效
    - 403 (Forbidden) - 权限不足/地区限制
    
    支持将错误记录到数据库以便后期分析（仅记录错误码，不记录完整错误消息）。
    """
    
    def __init__(self, keys: list, task_id: str = None, provider: str = None):
        self.all_keys = keys.copy()
        self.available_keys = keys.copy()
        self.exhausted_keys = set()
        self.lock = threading.Lock()
        self.task_id = task_id or "unknown"
        self.provider = provider or "unknown"
        random.shuffle(self.available_keys)  # 初始随机打乱
        
        # # API 错误记录地址（支持 401/402/403/429）
        # self._error_log_url = os.getenv("BASE_URL_API", "").rstrip("/") + "/api/4xx-error"
    
    def get_next_key(self) -> tuple:
        """
        获取下一个可用的 Key
        
        Returns:
            tuple: (key_index, key_value) 或 (None, None) 如果无可用 Key
        """
        with self.lock:
            if self.available_keys:
                key = random.choice(self.available_keys)
                idx = self.all_keys.index(key)
                return idx, key
            else:
                return None, None
    
    def mark_exhausted(self, key: str, error_code: str = None):
        """
        标记某个 Key 为已耗尽，并记录到数据库
        
        Args:
            key: API Key
            error_code: 错误码（如 "429", "401", "403"），简化记录
        """
        with self.lock:
            if key in self.available_keys:
                self.available_keys.remove(key)
                self.exhausted_keys.add(key)
                remaining = len(self.available_keys)
                total = len(self.all_keys)
                logger.warning(f"🚫 Key 已耗尽 (错误码: {error_code or 'unknown'})，剩余可用: {remaining}/{total}")
                
                # 📝 异步记录 API 错误到数据库（不阻塞主流程）
                self._log_api_error_async(key, error_code)
    
    def _log_api_error_async(self, key: str, error_code: str = None):
        """
        异步记录 API 错误到数据库（静默失败，不影响主流程）
        
        Args:
            key: API Key
            error_code: 简化的错误码（如 "429", "401", "402", "403"）
        """
        def _send_log():
            try:
                requests.post(
                    self._error_log_url,
                    json={
                        "task_id": self.task_id,
                        "key_name": self.provider,
                        "key_code": key,
                        "error_code": error_code or "unknown"  # 发送具体错误码
                    },
                    timeout=2  #快速超时，不阻塞
                )
                logger.debug(f"📝 API 错误 ({error_code}) 已记录到数据库")
            except Exception as e:
                logger.debug(f"⚠️ API 错误记录失败（不影响主流程）: {e}")
        
        # 使用线程异步发送，不阻塞主流程
        threading.Thread(target=_send_log, daemon=True).start()
    
    def reset_all(self):
        """重置所有 Key 为可用状态"""
        with self.lock:
            self.available_keys = self.all_keys.copy()
            random.shuffle(self.available_keys)
            self.exhausted_keys.clear()
            logger.info(f"♻️ 所有 Key 已重置，共 {len(self.all_keys)} 个可用")
    
    def is_all_exhausted(self) -> bool:
        """检查是否所有 Key 都已耗尽"""
        with self.lock:
            return len(self.available_keys) == 0
    
    @property
    def total_count(self) -> int:
        return len(self.all_keys)
    
    @property
    def available_count(self) -> int:
        with self.lock:
            return len(self.available_keys)


class UnifiedAIClient(BaseClient):
    """
    统一的 AI 客户端，使用 LangChain 管理所有提供商。
    
    继承自 BaseClient，保留所有原有的公共方法（Prompt模板）。
    只重新实现 _generate_content() 方法，使用 LangChain 进行 API 调用。
    
    使用示例：
        client = UnifiedAIClient("gemini")
        client = UnifiedAIClient("claude")
        client = UnifiedAIClient("deepseek")
        client = UnifiedAIClient("openrouter", model_pro="anthropic/claude-sonnet-4")
    """
    
    def __init__(
        self,
        llm_config: dict,
        task_id: str,
        model_pro: Optional[str] = None,
        model_flash: Optional[str] = None,
        custom_base_url: Optional[str] = None,
    ):
        """
        初始化统一客户端。
        
        Args:
            provider: 提供商名称（如 "gemini", "claude", "deepseek"）
            model_pro: 可选，覆盖默认的 Pro 模型
            model_flash: 可选，覆盖默认的 Flash 模型
            custom_base_url: 可选，自定义 API 端点
        """
        self.provider = "gemini"
        self.task_id = task_id
        # self.config = self._get_ProviderConfig(provider)         
        # 加载 API 密钥
        # api_keys_str = self.config["env_key"]
        # api_keys_list = [k["key_code"] for k in self._get_Api_Keys(api_keys_str)]
        api_keys_list = llm_config["api"]
        self.sdk_type = "google"


        self.api_key_manager = APIKeyManager(api_keys_list)
        
        # 确定模型名称（支持自定义覆盖）
        # self.model_pro_name = model_pro or self.config["model_pro"]
        # self.model_flash_name = model_flash or self.config["model_flash"]
        self.model_pro_name = "gemini-3.1-flash-lite-preview"
        self.model_flash_name = "gemini-flash-lite-latest"
        
        # 自定义 base_url
        # self.base_url = custom_base_url or self.config["base_url"]
        
        # 📊 Token 使用统计（按模型分类）
        self.token_stats = defaultdict(lambda: {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0
        })
        # 🔒 线程锁保护 token 统计
        self.token_stats_lock = threading.Lock()
        
        # 初始化 Key 池和模型
        self._init_key_pool_and_models()
        
        logger.info(f"✅ UnifiedAIClient 初始化成功: {llm_config}")
        logger.info(f"   📦 SDK 类型: {self.sdk_type}")
        logger.info(f"   🚀 Pro 模型: {self.model_pro_name}")
        logger.info(f"   ⚡ Flash 模型: {self.model_flash_name}")
        logger.info(f"   🔑 可用 Key: {self.key_pool.total_count} 个")
        # if self.base_url:
        #     logger.info(f"   🔗 API 端点: {self.base_url}")
    
    def _init_key_pool_and_models(self):
        """初始化 Key 池和模型构建器"""
        # 获取所有 API keys
        all_keys = self.api_key_manager.api_keys if self.api_key_manager else [self.api_key_manager.get_current_key()]
        
        # 创建智能 Key 池（传递 task_id 和 provider 用于 429 错误记录）
        self.key_pool = KeyPool(all_keys, task_id=self.task_id, provider=self.provider)
        logger.info(f"🔀 KeyPool initialized with {len(all_keys)} keys (task={self.task_id})")
        
        # 初始化模型构建器（根据 SDK 类型）
        # sdk_type = self.config["sdk_type"]
        self._init_model_builder(self.sdk_type)
    
    def _init_model_builder(self, sdk_type: str):
        """初始化模型构建器函数（根据 SDK 类型）"""
        if sdk_type == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._model_builder_pro = lambda key: ChatGoogleGenerativeAI(
                model=self.model_pro_name,
                google_api_key=key,
                temperature=0.1,
                max_retries=1,
                timeout=120,
            )
            self._model_builder_flash = lambda key: ChatGoogleGenerativeAI(
                model=self.model_flash_name,
                google_api_key=key,
                temperature=0.1,
                max_retries=0,
                timeout=30,
            )
        elif sdk_type == "anthropic":
            from langchain_anthropic import ChatAnthropic
            self._model_builder_pro = lambda key: ChatAnthropic(
                model=self.model_pro_name,
                anthropic_api_key=key,
                temperature=0.1,
                max_retries=0,
                timeout=30,
            )
            self._model_builder_flash = lambda key: ChatAnthropic(
                model=self.model_flash_name,
                anthropic_api_key=key,
                temperature=0.1,
                max_retries=0,
                timeout=30,
            )
        elif sdk_type == "openai_compatible":
            from langchain_openai import ChatOpenAI
            self._model_builder_pro = lambda key: ChatOpenAI(
                model=self.model_pro_name,
                api_key=key,
                base_url=self.base_url,
                temperature=0.1,
                timeout=40,
                max_retries=0,
            )
            self._model_builder_flash = lambda key: ChatOpenAI(
                model=self.model_flash_name,
                api_key=key,
                base_url=self.base_url,
                temperature=0.1,
                timeout=15,
                max_retries=0,
            )
        elif sdk_type == "cohere":
            from langchain_cohere import ChatCohere
            self._model_builder_pro = lambda key: ChatCohere(
                model=self.model_pro_name,
                cohere_api_key=key,
                temperature=0.1,
                max_retries=0,
                timeout=30,
            )
            self._model_builder_flash = lambda key: ChatCohere(
                model=self.model_flash_name,
                cohere_api_key=key,
                temperature=0.1,
                max_retries=0,
                timeout=30,
            )
        else:
            raise ValueError(f"未知的 SDK 类型: {sdk_type}")
        
        logger.info(f"🔧 Model builder initialized for {sdk_type}")

    def _generate_content(
        self,
        prompt: str,
        use_pro_model: bool = False,
        task_description: str = "AI Task",
        max_output_tokens: Optional[int] = None
    ) -> str:
        """
        【实现抽象方法】
        使用智能 KeyPool 管理 API Key，动态选择可用 Key。
        当某个 Key 报 429 时标记为已耗尽，直到所有 Key 都耗尽后才重置。
        """
        model_name = self.model_pro_name if use_pro_model else self.model_flash_name
        model_builder = self._model_builder_pro if use_pro_model else self._model_builder_flash

        # 🔄 重试轮次：所有 key 都失败后，等待 8秒/16秒，第 3 轮失败后退出
        max_rounds = 3
        wait_times = [0, 8, 16]

        for round_num in range(max_rounds):
            if round_num > 0:
                wait_seconds = wait_times[round_num]
                logger.warning(f"⏳ 所有 API key 已耗尽，等待 {wait_seconds} 秒后重置...")
                time.sleep(wait_seconds)
                self.key_pool.reset_all()
            
            # 尝试所有可用 Key
            while not self.key_pool.is_all_exhausted():
                key_idx, key = self.key_pool.get_next_key()
                if key is None:
                    break
                
                try:
                    # 动态创建模型并调用
                    model = model_builder(key)
                    
                    # 记录当前使用的 Key 到线程本地变量
                    _thread_local.current_key = key_idx + 1
                    _thread_local.total_keys = self.key_pool.total_count
                    
                    response = model.invoke([HumanMessage(content=prompt)])
                    response_text = response.content
                    
                    # Handle both string and list responses
                    if isinstance(response_text, list):
                        text_parts = []
                        for block in response_text:
                            if isinstance(block, dict) and 'text' in block:
                                text_parts.append(block['text'])
                            elif isinstance(block, str):
                                text_parts.append(block)
                        response_text = ''.join(text_parts)

                    # 📊 记录 Token 使用情况
                    token_info = self._record_token_usage(response, model_name)
                    
                    # 日志输出
                    key_info = f" 🔑Key[{key_idx + 1}/{self.key_pool.total_count}]"
                    if "Query" in task_description:
                        logger.info(f"⬅️ {self.provider}: {task_description} - Success{key_info}{token_info}, returned: {response_text[:150]}...")
                    else:
                        logger.info(f"⬅️ {self.provider}: {task_description} - Success{key_info}{token_info}")

                    return response_text

                except Exception as e:
                    error_str = str(e).lower()
                    
                    # 检查是否是需要切换 Key 或重试的错误
                    # 1. 配额/限流错误 (429)
                    is_rate_limit = any(keyword in error_str for keyword in ["rate", "quota", "429", "limit", "exhausted"])
                    # 2. 认证/权限/付费错误 (401/402/403) - API Key 无效、权限不足或需要付费
                    is_auth_error = any(keyword in error_str for keyword in ["401", "402", "403", "unauthorized", "forbidden", "invalid", "authentication", "permission", "payment", "billing"])
                    # 3. 网络抖动/SSL 错误（通常在代理环境下常见）
                    is_network_error = any(keyword in error_str for keyword in ["ssl", "connection", "unreachable", "timeout", "eof", "connection_error", "connecterror"])
                    # 4. 服务器错误 (5xx) - 服务端临时问题，应该重试
                    is_server_error = any(keyword in error_str for keyword in ["500", "502", "503", "504", "internal server error", "bad gateway", "service unavailable", "gateway timeout"])
                    
                    # 确定错误码（用于日志记录）
                    error_code = None
                    if "429" in error_str:
                        error_code = "429"
                    elif "401" in error_str:
                        error_code = "401"
                    elif "402" in error_str:
                        error_code = "402"
                    elif "403" in error_str:
                        error_code = "403"
                    elif "500" in error_str:
                        error_code = "500"
                    elif "502" in error_str:
                        error_code = "502"
                    elif "503" in error_str:
                        error_code = "503"
                    elif "504" in error_str:
                        error_code = "504"
                    elif is_rate_limit:
                        error_code = "429"  # 默认限流类错误归类为 429
                    elif is_auth_error:
                        error_code = "401"  # 默认认证类错误归类为 401
                    
                    if is_rate_limit:
                        # 429 限流/配额错误：标记 Key 为已耗尽
                        self.key_pool.mark_exhausted(key, error_code=error_code)
                        logger.warning(f"⚠️ {self.provider}: {task_description} - Key [{key_idx + 1}] 报 429/配额错误，尝试切换下一个 Key")
                    elif is_auth_error:
                        # 401/402/403 认证/付费/权限错误：标记 Key 为已耗尽
                        self.key_pool.mark_exhausted(key, error_code=error_code)
                        logger.warning(f"⚠️ {self.provider}: {task_description} - Key [{key_idx + 1}] 报 {error_code}/认证付费权限错误，尝试切换下一个 Key")
                    elif is_server_error:
                        # 5xx 服务器错误：不是 Key 的问题，等待后重试（不标记 Key 为耗尽）
                        logger.warning(f"⚠️ {self.provider}: {task_description} - 服务器错误 {error_code}: {e}，等待后重试...")
                        time.sleep(2)  # 服务器错误等待稍长一些
                    elif is_network_error:
                        # 网络错误：尝试切换下一个 Key 或重试
                        logger.warning(f"⚠️ {self.provider}: {task_description} - 网络/SSL 错误: {e} (Key [{key_idx + 1}])，尝试切换...")
                        # 稍微等待一下避开网络波动
                        time.sleep(1)
                    else:
                        # 非预期错误，直接失败
                        logger.error(f"❌ {self.provider}: {task_description} - 严重错误: {e}")
                        raise

            
            # 本轮所有 Key 都已耗尽
            if round_num >= max_rounds - 1:
                logger.error(f"❌ 已尝试 {max_rounds} 轮，所有 API key 均失败，退出任务")
                raise Exception(f"All API keys exhausted after {max_rounds} rounds")

        raise Exception(f"{self.provider} 调用失败: {task_description}")

    def _record_token_usage(self, response, model_name: str) -> str:
        """记录 Token 使用情况"""
        token_info = ""

        # LangChain 的 response 可能包含 usage_metadata
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            total_tokens = input_tokens + output_tokens

            with self.token_stats_lock:
                self.token_stats[model_name]["input_tokens"] += input_tokens
                self.token_stats[model_name]["output_tokens"] += output_tokens
                self.token_stats[model_name]["total_tokens"] += total_tokens
                self.token_stats[model_name]["api_calls"] += 1

            token_info = f" [Tokens: {input_tokens}↓ {output_tokens}↑ = {total_tokens}]"

        # 某些提供商可能使用 response_metadata
        elif hasattr(response, 'response_metadata') and response.response_metadata:
            metadata = response.response_metadata
            # OpenAI 格式
            if 'token_usage' in metadata:
                usage = metadata['token_usage']
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                total_tokens = usage.get('total_tokens', input_tokens + output_tokens)

                with self.token_stats_lock:
                    self.token_stats[model_name]["input_tokens"] += input_tokens
                    self.token_stats[model_name]["output_tokens"] += output_tokens
                    self.token_stats[model_name]["total_tokens"] += total_tokens
                    self.token_stats[model_name]["api_calls"] += 1

                token_info = f" [Tokens: {input_tokens}↓ {output_tokens}↑ = {total_tokens}]"

        return token_info

