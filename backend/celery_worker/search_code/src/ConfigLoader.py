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

        # AI 提供商（支持字符串名称或旧版数字ID）
        # 新格式：直接使用字符串名称（如 "gemini", "claude", "deepseek"）
        config["ai_provider"] = "vectorengine"
        
        # 最大检索轮次
        max_attempts = os.getenv("MAX_REFINEMENT_ATTEMPTS")
        config["max_refinement_attempts"] = int(search_setting["max_refinement_attempts"]) if search_setting["max_refinement_attempts"] else int(max_attempts)
        
        # 目标文献数量
        min_threshold = os.getenv("MIN_STUDY_THRESHOLD")
        config["min_study_threshold"] = int(search_setting["min_study_threshold"]) if search_setting["min_study_threshold"] else int(min_threshold)

        # 输出语言
        output_lang = os.getenv("OUTPUT_LANGUAGE")
        config["output_language"] = str(output_language) if output_language else str(output_lang) 
        
        # AI 并发数 *
        max_workers = os.getenv("AI_MAX_WORKERS")
        config["ai_max_workers"] = int(max_workers)
        
        # 批次大小 *
        batch_size = os.getenv("BATCH_SIZE")
        config["batch_size"] = int(batch_size) 
        
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

