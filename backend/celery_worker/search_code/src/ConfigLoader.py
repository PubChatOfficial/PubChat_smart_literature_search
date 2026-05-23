"""
配置加载器模块

从 .env 文件和 JSON 文件加载工作流配置
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure the logger for this module
logger = logging.getLogger(__name__)

# 加载 .env 文件
load_dotenv()


class ConfigLoader:
    """配置加载器"""
    
    # 配置文件路径
    _language_config_path = None
    _language_config_cache = None

    @staticmethod
    def _get_bool_env(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def _get_int_env(name: str, default: int, minimum=None, maximum=None) -> int:
        value = os.getenv(name)
        try:
            parsed = int(value) if value is not None and str(value).strip() else default
        except (TypeError, ValueError):
            logger.warning(f"Invalid integer env {name}={value!r}; using default {default}")
            parsed = default
        if minimum is not None and parsed < minimum:
            logger.warning(f"Env {name}={parsed} below minimum {minimum}; using {minimum}")
            parsed = minimum
        if maximum is not None and parsed > maximum:
            logger.warning(f"Env {name}={parsed} above maximum {maximum}; using {maximum}")
            parsed = maximum
        return parsed

    @staticmethod
    def _get_float_env(name: str, default: float, minimum=None, maximum=None) -> float:
        value = os.getenv(name)
        try:
            parsed = float(value) if value is not None and str(value).strip() else default
        except (TypeError, ValueError):
            logger.warning(f"Invalid float env {name}={value!r}; using default {default}")
            parsed = default
        if minimum is not None and parsed < minimum:
            logger.warning(f"Env {name}={parsed} below minimum {minimum}; using {minimum}")
            parsed = minimum
        if maximum is not None and parsed > maximum:
            logger.warning(f"Env {name}={parsed} above maximum {maximum}; using {maximum}")
            parsed = maximum
        return parsed
    
    @classmethod
    def _get_language_config_path(cls) -> Path:
        """获取语言配置文件路径"""
        if cls._language_config_path is None:
            cls._language_config_path = Path(__file__).parent.parent / "documents" / "language_config.json"
        return cls._language_config_path
    
    @classmethod    
    def load_env_config(cls, output_language:str, search_setting: dict) -> dict:
        """
        从 .env 文件加载工作流配置
        
        Returns:
            包含工作流参数的字典
        """
        config = {}
        search_setting = search_setting or {}

        # AI 提供商（支持字符串名称或旧版数字ID）
        # 新格式：直接使用字符串名称（如 "gemini", "claude", "deepseek"）
        # config["ai_provider"] = "vectorengine"
        
        # 最大检索轮次
        max_attempts = cls._get_int_env("MAX_REFINEMENT_ATTEMPTS", 30, minimum=1)
        config["max_refinement_attempts"] = int(search_setting.get("max_refinement_attempts") or max_attempts)
        
        # 目标文献数量
        min_threshold = cls._get_int_env("MIN_STUDY_THRESHOLD", 100, minimum=1)
        config["min_study_threshold"] = int(search_setting.get("min_study_threshold") or min_threshold)

        # 输出语言
        output_lang = os.getenv("OUTPUT_LANGUAGE", "zh")
        config["output_language"] = str(output_language) if output_language else str(output_lang) 
        
        # AI 并发数 *
        config["ai_max_workers"] = cls._get_int_env("AI_MAX_WORKERS", 60, minimum=1)
        
        # 批次大小 *
        config["batch_size"] = cls._get_int_env("BATCH_SIZE", 600, minimum=1)

        # Embedding 预筛配置
        config["embedding_enabled"] = cls._get_bool_env("EMBEDDING_ENABLED", True)
        config["embedding_similarity_threshold"] = cls._get_float_env(
            "EMBEDDING_SIMILARITY_THRESHOLD", 0.75, minimum=-1.0, maximum=1.0
        )
        config["embedding_batch_size"] = cls._get_int_env("EMBEDDING_BATCH_SIZE", 50, minimum=1, maximum=100)
        config["embedding_initial_concurrency"] = cls._get_int_env("EMBEDDING_INITIAL_CONCURRENCY", 4, minimum=1)
        config["embedding_max_concurrency"] = cls._get_int_env("EMBEDDING_MAX_CONCURRENCY", 8, minimum=1)
        if config["embedding_initial_concurrency"] > config["embedding_max_concurrency"]:
            config["embedding_initial_concurrency"] = config["embedding_max_concurrency"]
        config["embedding_ramp_delay_seconds"] = cls._get_float_env("EMBEDDING_RAMP_DELAY_SECONDS", 3.0, minimum=0.0)
        config["embedding_max_retries"] = cls._get_int_env("EMBEDDING_MAX_RETRIES", 2, minimum=0)
        config["embedding_timeout_seconds"] = cls._get_int_env("EMBEDDING_TIMEOUT_SECONDS", 180, minimum=1)
        config["embedding_backpressure_limit"] = cls._get_int_env("EMBEDDING_BACKPRESSURE_LIMIT", 240, minimum=1)
        
        # 计算衍生阈值 *
        config["max_study_threshold"] = config["min_study_threshold"]
        
        return config
    
    @classmethod
    def load_all_language_configs(cls) -> dict:
        """
        加载所有语言配置
        
        Returns:
            包含所有语言配置的字典
        """
        if cls._language_config_cache is not None:
            return cls._language_config_cache
            
        config_path = cls._get_language_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._language_config_cache = json.load(f)
            return cls._language_config_cache
        except FileNotFoundError:
            logging.error(f"❌ Language config file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"❌ Failed to parse language config: {e}")
            raise
    
    @classmethod
    def load_language_config(cls, language_abbr: str) -> dict:
        """
        加载指定语言的配置
        
        Args:
            language_id: 语言ID (1=中文, 2=English, ...)
            
        Returns:
            语言配置字典
        """
        all_configs = cls.load_all_language_configs()
        
        config = all_configs[str(language_abbr)]
        logging.info(f"🌍 Output language set to: {config['name']} ({config['code']})")
        return config
