"""
Europe PMC 客户端

提供与 Europe PMC API 交互的方法，用于获取文献详情。
作为 PubMed efetch 的主数据源，无需 API Key，限流更宽松。
"""

import html
import re
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# Configure the logger for this module
logger = logging.getLogger(__name__)


class EuropePMCClient:
    """
    Europe PMC API 客户端
    
    用于通过 PMID 批量获取文献详情，作为 PubMed efetch 的主数据源。
    
    特点：
    - 无需 API Key
    - 无批量限制（已测试 10000 篇）
    - 返回 JSON 格式，解析更简单
    
    注意事项：
    - 部分最新文献可能缺失
    - 部分文献可能缺少摘要
    - 标题可能包含 HTML 实体需要解码
    """
    
    # 🚀 使用 POST 端点（支持更大的查询）
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/searchPOST"
    
    def __init__(self):
        """初始化 Europe PMC 客户端"""
        logger.info("🌍 Europe PMC client initialized (no API key required)")
    
    def fetch_by_pmids(self, pmid_list: List[str], timeout: int = 15) -> Tuple[Optional[Dict], List[str]]:
        """
        通过 PMID 列表批量获取文献详情
        
        Args:
            pmid_list: PMID 列表
            timeout: 请求超时时间（秒），默认 60 秒（超时后自动 fallback 到 PubMed）
        
        Returns:
            Tuple[Optional[Dict], List[str]]:
                - 成功时返回 (解析后的 JSON 响应, [])
                - 失败时返回 (None, 原始 pmid_list)
        
        Example:
            client = EuropePMCClient()
            response, failed_pmids = client.fetch_by_pmids(['12345678', '87654321'])
        """
        if not pmid_list:
            logger.warning("⚠️ Empty PMID list provided to Europe PMC fetch")
            return None, []
        
        # 构建查询字符串: EXT_ID:pmid1 OR EXT_ID:pmid2 OR ...
        query_parts = [f"EXT_ID:{pmid}" for pmid in pmid_list]
        query_string = " OR ".join(query_parts)
        
        # POST 请求表单数据（不是 JSON）
        form_data = {
            "query": query_string,
            "format": "json",
            "resultType": "core",  # 返回完整信息（包括摘要、作者等）
            "pageSize": min(len(pmid_list) + 100, 1000),  # Europe PMC POST 最大 1000
        }
        
        try:
            logger.info(f"🌍 Fetching {len(pmid_list)} articles from Europe PMC (POST)...")
            
            # 🚀 使用 POST 请求（支持更大的 query 字符串）
            response = requests.post(
                self.BASE_URL,
                data=form_data,  # 表单数据，不是 JSON
                timeout=timeout
            )
            response.raise_for_status()
            
            # 解析 JSON 响应
            data = response.json()
            
            # 检查响应结构
            hit_count = data.get("hitCount", 0)
            result_list = data.get("resultList", {}).get("result", [])
            
            logger.info(f"✅ Europe PMC returned {hit_count} hits, {len(result_list)} results")
            
            # 检查是否有缺失的 PMID
            returned_pmids = {str(r.get("pmid", "")) for r in result_list if r.get("pmid")}
            requested_pmids = set(pmid_list)
            missing_pmids = requested_pmids - returned_pmids
            
            if missing_pmids:
                logger.info(f"   📋 Missing {len(missing_pmids)} PMIDs from Europe PMC")
            
            return data, list(missing_pmids)
            
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Europe PMC request timed out after {timeout}s")
            return None, pmid_list
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🔌 Europe PMC connection error: {e}")
            return None, pmid_list
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Europe PMC HTTP error: {e}")
            return None, pmid_list
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Europe PMC request error: {e}")
            return None, pmid_list
            
        except ValueError as e:
            # JSON 解析错误
            logger.error(f"❌ Europe PMC JSON parse error: {e}")
            return None, pmid_list
    
    @staticmethod
    def clean_title(title: str) -> str:
        """
        清理标题中的 HTML 实体和标签
        
        处理步骤：
        1. 解码 HTML 实体: &lt;i&gt; → <i>
        2. 移除 HTML 标签: <i>text</i> → text
        
        Args:
            title: 原始标题字符串
        
        Returns:
            清理后的标题
        """
        if not title:
            return title
        
        # 第一步：解码 HTML 实体
        decoded = html.unescape(title)
        
        # 第二步：移除 HTML 标签
        cleaned = re.sub(r'<[^>]+>', '', decoded)
        
        # 清理多余空格
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    @staticmethod
    def calculate_days_since_publication(pub_date_str: str) -> Optional[int]:
        """
        计算文献发表至今的天数
        
        Args:
            pub_date_str: 发表日期字符串，格式为 YYYY-MM-DD
        
        Returns:
            天数，如果解析失败返回 None
        """
        if not pub_date_str:
            return None
        
        try:
            # Europe PMC 日期格式: YYYY-MM-DD
            pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d")
            delta = datetime.now() - pub_date
            return delta.days
        except ValueError:
            # 尝试其他格式
            try:
                # 有时只有年月: YYYY-MM
                pub_date = datetime.strptime(pub_date_str, "%Y-%m")
                delta = datetime.now() - pub_date
                return delta.days
            except ValueError:
                try:
                    # 有时只有年份: YYYY
                    pub_date = datetime.strptime(pub_date_str, "%Y")
                    delta = datetime.now() - pub_date
                    return delta.days
                except ValueError:
                    logger.debug(f"⚠️ Unable to parse publication date: {pub_date_str}")
                    return None
    
    @staticmethod
    def is_within_days(pub_date_str: str, days: int = 90) -> bool:
        """
        判断文献是否在指定天数内发表
        
        Args:
            pub_date_str: 发表日期字符串
            days: 天数阈值，默认 90 天
        
        Returns:
            如果在指定天数内返回 True，否则返回 False
            如果无法判断，保守返回 True（避免误删新文献）
        """
        days_since = EuropePMCClient.calculate_days_since_publication(pub_date_str)
        
        if days_since is None:
            # 无法判断时保守处理，假设是新文献
            return True
        
        return days_since <= days
