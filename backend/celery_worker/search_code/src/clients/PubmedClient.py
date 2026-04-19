import logging
import os
import random
import requests
import threading
from typing import Dict, Optional, List

# Configure the logger for this module
logger = logging.getLogger(__name__)


class PubMedAPIKeyManager:
    """
    管理多个PubMed API密钥，支持自动切换。

    当遇到API错误时，自动切换到下一个可用的API密钥。
    线程安全，支持并发环境下的API密钥切换。
    """
    def __init__(self, api_keys: List[str]):
        """
        初始化API密钥管理器

        Args:
            api_keys: API密钥列表
        """
        if not api_keys or len(api_keys) == 0:
            raise ValueError("At least one PubMed API key must be provided")

        self.api_keys = api_keys
        self.lock = threading.Lock()

        # 如果有多个API密钥，随机选择起始索引以实现负载均衡
        if len(api_keys) > 1:
            self.current_index = random.randint(0, len(api_keys) - 1)
            logger.info(f"🔑 PubMed API Key Manager initialized with {len(api_keys)} keys. Starting with key #{self.current_index + 1}.")
        else:
            self.current_index = 0
            logger.info(f"🔑 PubMed API Key Manager initialized with {len(api_keys)} key(s).")

    def get_current_key(self) -> str:
        """
        获取当前使用的API密钥

        Returns:
            当前API密钥
        """
        with self.lock:
            return self.api_keys[self.current_index]

    def get_current_index(self) -> int:
        """
        获取当前API密钥的索引

        Returns:
            当前索引（从0开始）
        """
        with self.lock:
            return self.current_index

    def get_random_key(self) -> tuple[str, int]:
        """
        随机选择一个API密钥（每次请求时调用，实现负载均衡）

        Returns:
            (随机选择的API密钥, 索引)
        """
        with self.lock:
            if len(self.api_keys) == 1:
                return self.api_keys[0], 0
            random_index = random.randint(0, len(self.api_keys) - 1)
            return self.api_keys[random_index], random_index

    def switch_to_next_key(self) -> tuple[str, int]:
        """
        切换到下一个API密钥（循环）

        Returns:
            (新的API密钥, 新的索引)
        """
        with self.lock:
            old_index = self.current_index
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            new_key = self.api_keys[self.current_index]

            logger.warning(f"🔄 Switching PubMed API key: #{old_index + 1} → #{self.current_index + 1} (out of {len(self.api_keys)} keys).")

            return new_key, self.current_index


class PubMedClient:
    """
    A client for interacting with the NCBI PubMed E-utilities API.

    This class provides methods to search for articles (Esearch) and fetch
    their detailed data (Efetch), including robust error handling and API key rotation.

    支持多API密钥自动切换，当遇到API错误时自动切换到下一个可用密钥。
    """
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    def __init__(self):
        """
        Initializes the PubMed client.

        支持从环境变量读取多个API密钥（用分号分隔）。
        当遇到API错误时，自动切换到下一个API密钥。

        环境变量格式：
        PUBMED_API_KEY=key1;key2;key3
        或
        PUBMED_API_KEY=key1
        """
        api_keys = ["29563e85a140f011f08508d6d71c452e3d08","da361bdd993c85a319b6b8bf482f979dc508","9b0de3da446aabd777cb6825a77867197008","a1eb6228a2b76e101564b689bffc94f95508","1d9a1cfbe06b7202316651255afa71209208","9fc9e852f1648e302c5bcb2d5f8558d46408","fbf5ffab87c121c8eeaaa1c4278727299608"]

        self.api_key_manager = PubMedAPIKeyManager(api_keys)
        self.api_key = self.api_key_manager.get_current_key()
        logger.info(f"🚀 PubMed client initialized with {len(api_keys)} API key(s).")

    def esearch(self, term: str, retmax: str = "100000") -> Optional[Dict]:
        """
        Performs a search on PubMed using the Esearch utility.

        支持API密钥随机轮询：
        - 每次请求时随机选择一个API密钥（负载均衡）
        - 遇到API错误时，重试并随机选择新的API密钥

        Args:
            term: The search term or query.
            retmax: Maximum number of PMIDs to retrieve (default: 100000 to get all results)

        Returns:
            A dictionary containing the 'webenv', 'querykey', 'count', and 'idlist'
            from the search result, or None if the search fails.
        """
        # Check query length - PubMed has limits
        if len(term) > 4000:
            logger.warning(f"✂️ Query length ({len(term)}) exceeds recommended limit. Truncating...")
            term = term[:4000]
            logger.warning(f"✂️ Truncated query: {term}")

        max_attempts = len(self.api_key_manager.api_keys) if self.api_key_manager else 1
        attempt = 0

        while attempt < max_attempts:
            # 每次请求时随机选择一个API密钥
            if self.api_key_manager:
                current_api_key, current_key_index = self.api_key_manager.get_random_key()
            else:
                current_api_key = None
                current_key_index = 0

            endpoint = f"{self.BASE_URL}esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": term,
                "usehistory": "y",
                "retmode": "json",
                "retmax": retmax,
            }
            if current_api_key:
                params["api_key"] = current_api_key

            try:
                logger.info(f"🔍 Executing Esearch for term: {term[:100]}... (retmax={retmax}, API Key #{current_key_index + 1})")
                response = requests.post(endpoint, data=params, timeout=60)

                # Log response details for debugging
                logger.debug(f"Response status code: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")

                response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

                # Check if response content is empty
                if not response.text.strip():
                    logger.error("❌ Received empty response from PubMed API")
                    logger.error(f"   Response status: {response.status_code}")
                    logger.error(f"   Response headers: {dict(response.headers)}")
                    raise ValueError("Empty response from PubMed API")

                # Check for maintenance page
                if "Maintenance in progress" in response.text or "maintenance" in response.text.lower():
                    logger.error("🚧 PubMed/NCBI is currently under maintenance!")
                    logger.error("The service is temporarily unavailable. Please try again later.")
                    if "24+ hours" in response.text:
                        logger.error("⏰ Maintenance may last 24+ hours according to the maintenance page.")
                    raise ValueError("PubMed API is under maintenance")

                # Check if response is HTML instead of JSON
                if response.text.strip().startswith('<?xml') or response.text.strip().startswith('<html'):
                    logger.error("❌ Received HTML/XML response instead of JSON from PubMed API")
                    logger.error("   This usually indicates a service error or maintenance.")
                    logger.error(f"   Response content preview: {response.text[:300]}")
                    raise ValueError("PubMed API returned HTML instead of JSON")

                # Log first 200 characters of response for debugging
                logger.debug(f"Response content preview: {response.text[:200]}")

                data = response.json()
                esearch_result = data.get("esearchresult")

                if not esearch_result:
                    logger.error("❌ Esearch result is missing from the API response.")
                    logger.error(f"   Full response: {response.text}")
                    return None

                count = int(esearch_result.get("count", 0))
                idlist = esearch_result.get("idlist", [])
                logger.info(f"✅ Esearch found {count} articles, retrieved {len(idlist)} PMIDs.")

                return {
                    "webenv": esearch_result.get("webenv"),
                    "querykey": esearch_result.get("querykey"),
                    "count": count,
                    "idlist": idlist,
                }

            except (requests.exceptions.RequestException, ValueError) as e:
                attempt += 1
                logger.error(f"⚠️ PubMed API error (Attempt {attempt}/{max_attempts}, API Key #{current_key_index + 1}): {e}")

                # 如果有多个API密钥且未达到最大尝试次数，重试（下次循环会随机选择新的密钥）
                if self.api_key_manager and attempt < max_attempts:
                    logger.warning(f"   Will retry with a randomly selected API key...")
                    continue
                else:
                    # 没有更多密钥或已尝试所有密钥
                    logger.error(f"❌ All PubMed API key attempts failed. Aborting request.")
                    logger.error(f"   Request URL: {endpoint}")
                    logger.error(f"   Request params: {params}")
                    return None

        # 理论上不会到达这里
        raise Exception("Unexpected error in esearch")

    def efetch(self, webenv: str, query_key: str, retmax: str = "600") -> Optional[str]:
        """
        Fetches detailed article information from PubMed using the Efetch utility.

        支持API密钥随机轮询：
        - 每次请求时随机选择一个API密钥（负载均衡）
        - 遇到API错误时，重试并随机选择新的API密钥

        Args:
            webenv: The WebEnv identifier from a previous Esearch call.
            query_key: The QueryKey identifier from a previous Esearch call.
            retmax: Maximum number of articles to fetch (default: 600).

        Returns:
            A string containing the raw XML data of the fetched articles,
            or None if the fetch fails.
        """
        max_attempts = len(self.api_key_manager.api_keys) if self.api_key_manager else 1
        attempt = 0

        while attempt < max_attempts:
            # 每次请求时随机选择一个API密钥
            if self.api_key_manager:
                current_api_key, current_key_index = self.api_key_manager.get_random_key()
            else:
                current_api_key = None
                current_key_index = 0

            endpoint = f"{self.BASE_URL}efetch.fcgi"
            params = {
                "db": "pubmed",
                "webenv": webenv,
                "query_key": query_key,
                "retmode": "xml",
                "rettype": "abstract",
                "retmax": retmax,
            }
            if current_api_key:
                params["api_key"] = current_api_key

            try:
                logger.info(f"⬇️ Executing Efetch with WebEnv: {webenv} (retmax={retmax}, API Key #{current_key_index + 1})")
                response = requests.get(endpoint, params=params, timeout=60)
                response.raise_for_status()

                logger.info("✅ Efetch completed successfully.")
                return response.text

            except requests.exceptions.RequestException as e:
                attempt += 1
                logger.error(f"⚠️ PubMed Efetch API error (Attempt {attempt}/{max_attempts}, API Key #{current_key_index + 1}): {e}")

                # 如果有多个API密钥且未达到最大尝试次数，重试（下次循环会随机选择新的密钥）
                if self.api_key_manager and attempt < max_attempts:
                    logger.warning(f"   Will retry with a randomly selected API key...")
                    continue
                else:
                    # 没有更多密钥或已尝试所有密钥
                    logger.error(f"❌ All PubMed API key attempts failed for Efetch. Aborting request.")
                    raise

        # 理论上不会到达这里
        raise Exception("Unexpected error in efetch")

    def efetch_by_pmids(self, pmid_list: list, retmax: str = "600") -> Optional[str]:
        """
        Fetches detailed article information from PubMed using specific PMIDs.
        Uses POST request to avoid URL length limits.

        支持API密钥随机轮询：
        - 每次请求时随机选择一个API密钥（负载均衡）
        - 遇到API错误时，重试并随机选择新的API密钥

        Args:
            pmid_list: List of PMIDs to fetch.
            retmax: Maximum number of articles to fetch (default: 600).

        Returns:
            A string containing the raw XML data of the fetched articles,
            or None if the fetch fails.
        """
        if not pmid_list:
            logger.warning("⚠️ Empty PMID list provided to efetch_by_pmids.")
            return None

        # Limit the number of PMIDs to fetch
        pmids_to_fetch = pmid_list[:int(retmax)]
        pmid_string = ",".join(pmids_to_fetch)

        max_attempts = len(self.api_key_manager.api_keys) if self.api_key_manager else 1
        attempt = 0

        while attempt < max_attempts:
            # 每次请求时随机选择一个API密钥
            if self.api_key_manager:
                current_api_key, current_key_index = self.api_key_manager.get_random_key()
            else:
                current_api_key = None
                current_key_index = 0

            endpoint = f"{self.BASE_URL}efetch.fcgi"
            data = {
                "db": "pubmed",
                "id": pmid_string,
                "retmode": "xml",
                "rettype": "abstract",
            }
            if current_api_key:
                data["api_key"] = current_api_key

            try:
                logger.info(f"⬇️ Executing Efetch for {len(pmids_to_fetch)} specific PMIDs via POST (API Key #{current_key_index + 1})")
                response = requests.post(endpoint, data=data, timeout=60)
                response.raise_for_status()

                logger.info("✅ Efetch by PMIDs completed successfully.")
                return response.text

            except requests.exceptions.RequestException as e:
                attempt += 1
                logger.error(f"⚠️ PubMed Efetch by PMIDs API error (Attempt {attempt}/{max_attempts}, API Key #{current_key_index + 1}): {e}")

                # 如 果有多个API密钥且未达到最大尝试次数，重试（下次循环会随机选择新的密钥）
                if self.api_key_manager and attempt < max_attempts:
                    logger.warning(f"   Will retry with a randomly selected API key...")
                    continue
                else:
                    # 没有更多密钥或已尝试所有密钥
                    logger.error(f"❌ All PubMed API key attempts failed for Efetch by PMIDs. Aborting request.")
                    raise

        # 理论上不会到达这里
        raise Exception("Unexpected error in efetch_by_pmids")
    
    def _get_Api_Keys(self, key_name) -> dict:
        
        base_url_api_keys = os.getenv("BASE_URL_API")
        full_url_api_keys = f"{base_url_api_keys}/api_keys/{key_name}"
        try:
            response = requests.get(full_url_api_keys, timeout=5)
            
            if response.status_code == 200:
                # 返回 [{"api_name":..., "api_code":...}]
                return response.json() 
            else:
                logger.error(f"请求失败: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"连接API Key服务失败: {e}")
            return []

