"""
文献筛选器模块

包含文献筛选和三级评分复核机制
"""

import re
import logging
import threading
from typing import Optional, Tuple

from .utils.query_utils import extract_json_from_response, extract_with_fuzzy_match
from .utils.data_processor import extract_article_metadata

# Configure the logger for this module
logger = logging.getLogger(__name__)


class ScreeningController:
    """
    筛选控制器（线程安全）
    
    用于在并行筛选过程中跟踪已纳入文献数量，
    并在达到目标阈值时停止接受新文献。
    """
    
    def __init__(self, threshold: int, initial_count: int = 0):
        """
        初始化控制器
        
        Args:
            threshold: 目标文献数量（MIN_STUDY_THRESHOLD）
            initial_count: 初始已纳入数量（用于续作项目）
        """
        self.threshold = threshold
        self._count = initial_count
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # 如果初始数量已达阈值，直接设置停止标志
        if self._count >= self.threshold:
            self._stop_event.set()
    
    def should_stop(self) -> bool:
        """检查是否应该停止接受新文献"""
        return self._stop_event.is_set()
    
    def increment_and_check(self, pmid: str = "") -> Tuple[int, bool]:
        """
        原子递增计数并检查是否达到阈值
        
        Args:
            pmid: 文献 PMID（用于日志显示）
        
        Returns:
            (当前计数, 是否刚刚达到阈值)
        """
        with self._lock:
            self._count += 1
            current = self._count
            just_reached = (current == self.threshold)
            is_overflow = (current > self.threshold)
            
            # 显示进度（用 📊 区分，超出阈值标注 OVERFLOW）
            if is_overflow:
                logging.info(f"📊 Article included [OVERFLOW {current}/{self.threshold}] PMID: {pmid}")
            else:
                logging.info(f"📊 Article included [{current}/{self.threshold}] PMID: {pmid}")
            
            if current >= self.threshold:
                if just_reached:
                    logging.info(f"🎉 Goal reached! Stopping new submissions. [{current}/{self.threshold}]")
                self._stop_event.set()
            
            return current, just_reached
    
    def get_count(self) -> int:
        """获取当前计数"""
        with self._lock:
            return self._count


def format_score_with_language(score: str, language_config: dict) -> str:
    """
    将纯数字评分映射为带语言描述的完整格式

    Args:
        score: 纯数字评分或已格式化的评分
        language_config: 语言配置字典

    Returns:
        格式化后的评分字符串
    """
    if not score:
        return "未评分"

    score = str(score).strip()

    # 尝试匹配纯数字
    match = re.search(r'^([123])$', score)
    if match:
        score_num = match.group(1)
        scoring_levels = language_config.get('scoring_levels', {})
        return scoring_levels.get(score_num, score)

    # 尝试从已格式化的字符串中提取数字
    match = re.search(r'([123])\s*(分|points?|puntos?|punto|Punkte?|балл[а]?|баллов)', score)
    if match:
        score_num = match.group(1)
        scoring_levels = language_config.get('scoring_levels', {})
        return scoring_levels.get(score_num, score)

    return score


class ArticleScreener:
    """文献筛选器（含三级评分复核）"""

    def __init__(self, ai_client, user_query: str, scoring_criteria: str, language_config: dict):
        """
        初始化筛选器

        Args:
            ai_client: AI客户端实例
            user_query: 用户查询
            scoring_criteria: 评分标准
            language_config: 语言配置
        """
        self.ai_client = ai_client
        self.user_query = user_query
        self.scoring_criteria = scoring_criteria
        self.language_config = language_config
        # 注意：不再使用 json_fields，AI 返回固定英文键名

    def screen(self, article_dict: dict, current_count: int, current_round: int,
               pre_extracted_metadata: dict = None,
               controller: 'ScreeningController' = None) -> Optional[dict]:
        """
        筛选单篇文献（含三级评分复核）

        Args:
            article_dict: 文献数据字典（原始 XML 解析结果或已提取的元数据）
            current_count: 当前已筛选数量
            current_round: 当前轮次
            pre_extracted_metadata: 预提取的元数据（如期刊过滤后已有，可直接使用）
            controller: 筛选控制器（用于早期停止）

        Returns:
            筛选结果字典，不匹配返回 None
        """
        # 如果已有预提取的元数据，直接使用；否则从 article_dict 提取
        if pre_extracted_metadata:
            metadata = pre_extracted_metadata
        elif "pmid" in article_dict and "abstract" in article_dict:
            # article_dict 已经是元数据格式
            metadata = article_dict
        else:
            # article_dict 是原始 XML 解析结果，需要提取元数据
            metadata = extract_article_metadata(article_dict)

        pmid = metadata.get("pmid", "N/A")

        # ⏹️ 早期停止检查：如果已达到目标，直接跳过（不调用 AI）
        if controller and controller.should_stop():
            logging.debug(f"⏹️ Skipping article {pmid} - threshold already reached")
            return None

        if not metadata["abstract"] or metadata["abstract"] == "No abstract available.":
            logging.warning(f"⚠️ Skipping article {pmid} due to missing abstract.")
            return None

        MAX_JSON_RETRIES = 3
        for i in range(MAX_JSON_RETRIES):
            try:
                # 第一次提取
                extracted_info_str = self.ai_client.extract_article_info(
                    metadata["abstract"],
                    self.user_query,
                    self.scoring_criteria,
                    current_count,
                    current_round,
                    self.language_config,
                    pmid=pmid
                )

                extracted_info = extract_json_from_response(extracted_info_str, pmid)

                # 成功提取
                if isinstance(extracted_info, dict):
                    logging.info(f"✅ Article {pmid} MATCHED user query. Extracted details.")

                    # 使用近义词匹配提取标准化字段
                    standardized_info = extract_with_fuzzy_match(extracted_info, pmid)

                    # 🔢 第一次评分通过，立即计数
                    if controller:
                        controller.increment_and_check(pmid)

                    result = self._build_result(metadata, standardized_info)

                    # 🔓 异步启动 Unpaywall 查询（如果没有 PMC 链接但有 DOI）
                    oa_future = None
                    oa_executor = None
                    if not metadata.get("pmcid") and metadata.get("doi"):
                        from concurrent.futures import ThreadPoolExecutor
                        from .utils.data_processor import get_oa_link_from_unpaywall
                        oa_executor = ThreadPoolExecutor(max_workers=1)
                        oa_future = oa_executor.submit(get_oa_link_from_unpaywall, metadata["doi"])
                        logging.info(f"🔍 PMID {pmid}: Querying Unpaywall (no PMC link)")

                    # 检测并补充空值字段
                    result = self._fill_missing_fields(result, metadata["abstract"], pmid)

                    # 三级评分复核（即使已达阈值，已纳入的文献仍需完成复核）
                    original_score = result["score"]
                    final_score = self._verify_score_three_level(
                        metadata["abstract"],
                        original_score,
                        pmid
                    )
                    result["score"] = final_score

                    # 🔓 获取 Unpaywall 查询结果（此时第二次评分已完成，Unpaywall 查询也应该完成了）
                    if oa_future:
                        try:
                            oa_link = oa_future.result(timeout=3)  # 最多再等 3 秒
                            if oa_link:
                                result["oa_link"] = oa_link
                                logging.info(f"🔓 PMID {pmid}: Found OA link from Unpaywall")
                            else:
                                logging.info(f"⚪ PMID {pmid}: No OA link found (or bronze excluded)")
                        except Exception as e:
                            logging.warning(f"⚠️ PMID {pmid}: Unpaywall query failed: {e}")
                        finally:
                            if oa_executor:
                                oa_executor.shutdown(wait=False)

                    return result

                # 不匹配
                elif extracted_info is None:
                    logging.info(f"⚪ Article {pmid} did not match user query. Skipping.")
                    return None

                # JSON格式错误，重试
                elif extracted_info == "MALFORMED_JSON":
                    logging.warning(f"⚠️ Malformed JSON for article {pmid}. Retry {i + 1}/{MAX_JSON_RETRIES}...")

            except Exception as e:
                logging.error(f"❌ Error screening article {pmid} on attempt {i + 1}: {e}", exc_info=True)

        logging.error(f"❌ Failed to get valid JSON for article {pmid} after {MAX_JSON_RETRIES} attempts.")
        return None

    def _build_result(self, metadata: dict, extracted_info: dict) -> dict:
        """
        构建结果字典（使用英文键名）

        Args:
            metadata: 文献元数据
            extracted_info: AI 提取的标准化信息（已使用 extract_with_fuzzy_match 处理）

        Returns:
            结果字典
        """
        return {
            # 基础字段（xlsx 使用）
            "index": "",
            "journal": metadata.get("journal"),
            "issn": metadata.get("issn"),
            "cas_zone": metadata.get("cas_zone", ""),
            "jcr_zone": metadata.get("jcr_zone", ""),
            "latest_if": metadata.get("latest_if", ""),
            "five_year_if": metadata.get("five_year_if", ""),
            "ranking": metadata.get("ranking", ""),
            "pmid": metadata.get("pmid"),
            "pmcid": metadata.get("pmcid"),
            "title": metadata.get("title"),
            "first_author": metadata.get("first_author"),
            "corresponding_author": metadata.get("corresponding_author"),
            "first_author_affiliation": metadata.get("first_affiliation"),
            "publication_date": metadata.get("publication_date"),
            # AI 提取的字段
            "score": format_score_with_language(
                extracted_info.get("score", ""),
                self.language_config
            ),
            "research_objective": extracted_info.get("research_objective", ""),
            "study_type": extracted_info.get("study_type", ""),
            "research_method": extracted_info.get("research_method", ""),
            "study_population": extracted_info.get("study_population", ""),
            "main_results": extracted_info.get("main_results", ""),
            "conclusions": extracted_info.get("conclusions", ""),
            "highlights": extracted_info.get("highlights", ""),
            # RIS 导出专用字段（不写入 xlsx）
            "abstract": metadata.get("abstract"),
            "doi": metadata.get("doi"),
            "volume": metadata.get("volume"),
            "issue": metadata.get("issue"),
            "pages": metadata.get("pages"),
            "journal_abbrev": metadata.get("journal_abbrev"),
            "language": metadata.get("language"),
            "keywords": metadata.get("keywords", []),
            "all_authors": metadata.get("all_authors", []),
        }

    def _fill_missing_fields(self, result: dict, abstract: str, pmid: str) -> dict:
        """
        检测并补充空值字段（单字段补充）

        Args:
            result: 当前结果字典
            abstract: 文献摘要
            pmid: 文献 PMID

        Returns:
            补充后的结果字典
        """
        # 需要检测的字段（不包含 score，因为 score 为空几乎不可能）
        fields_to_check = [
            "research_objective",
            "study_type",
            "research_method",
            "study_population",
            "main_results",
            "conclusions",
            "highlights"
        ]

        MAX_FILL_RETRIES = 2

        for field_key in fields_to_check:
            value = result.get(field_key, "")

            # 检测空值
            if not value or str(value).strip() == "":
                logging.warning(f"⚠️ PMID {pmid}: Field '{field_key}' is empty, attempting to fill...")

                for retry in range(MAX_FILL_RETRIES):
                    try:
                        # 调用单字段补充
                        filled_value = self.ai_client.fill_single_field(
                            abstract=abstract,
                            field_key=field_key,
                            user_query=self.user_query,
                            language_config=self.language_config,
                            pmid=pmid
                        )

                        if filled_value and str(filled_value).strip():
                            result[field_key] = filled_value.strip()
                            logging.info(f"✅ PMID {pmid}: Field '{field_key}' filled successfully")
                            break
                        else:
                            logging.warning(f"⚠️ PMID {pmid}: Field '{field_key}' fill returned empty (retry {retry + 1}/{MAX_FILL_RETRIES})")

                    except Exception as e:
                        logging.error(f"❌ PMID {pmid}: Failed to fill '{field_key}' (retry {retry + 1}/{MAX_FILL_RETRIES}): {e}")

                # 如果仍然为空，标记为 N/A
                if not result.get(field_key) or str(result.get(field_key)).strip() == "":
                    result[field_key] = "N/A"
                    logging.warning(f"⚠️ PMID {pmid}: Field '{field_key}' could not be filled, set to 'N/A'")

        return result

    def _verify_score_three_level(self, abstract: str, original_score: str, pmid: str) -> str:
        """
        三级评分复核机制

        流程：
        1. 第2次评分（独立评分）
        2. 系统比较两次评分
        3. 如果不一致，进行第3次评分（AI裁决）
        """
        try:
            logging.debug(f"🔍 PMID {pmid}: Starting 3-level verification (original: {original_score})")

            # 第2次评分
            second_score = self._get_second_score(abstract, pmid)

            if not second_score:
                logging.warning(f"⚠️ PMID {pmid}: 2nd scoring failed, keeping original")
                return original_score

            # 比较评分
            if original_score == second_score:
                logging.info(f"✅ PMID {pmid}: Scores consistent ({original_score})")
                return original_score

            # 第3次评分：AI裁决
            logging.warning(f"⚠️ PMID {pmid}: Scores inconsistent (1st: {original_score}, 2nd: {second_score})")

            final_score = self._arbitrate_score(abstract, original_score, second_score, pmid)
            logging.info(f"🔄 PMID {pmid}: Score corrected {original_score} → {final_score}")
            return final_score

        except Exception as e:
            logging.error(f"❌ PMID {pmid}: 3-level verification failed - {e}")
            return original_score

    def _get_second_score(self, abstract: str, pmid: str) -> Optional[str]:
        """第2次独立评分"""
        prompt = f"""# Task
Score the relevance of this literature abstract (1-3 scale).

# Scoring Criteria
{self.scoring_criteria}

# User Research Query
{self.user_query}

# Abstract
{abstract}

# Output
Reply with ONLY one number: 1, 2, or 3
- 3 = Highly relevant
- 2 = Moderately relevant
- 1 = Slightly relevant

Your answer (just the number):"""

        try:
            response = self.ai_client._generate_content(
                prompt,
                use_pro_model=False,
                task_description=f"Score Verification 2nd (PMID: {pmid})"
            )

            # 直接从响应中提取数字
            score = self._extract_score_from_response(response, pmid)
            if score:
                formatted = format_score_with_language(score, self.language_config)
                logging.debug(f"   2nd scoring: {score} → {formatted}")
                return formatted

            return None
        except Exception as e:
            logging.error(f"❌ PMID {pmid}: 2nd scoring failed - {e}")
            return None

    def _extract_score_from_response(self, response: str, pmid: str) -> Optional[str]:
        """
        从 AI 响应中提取评分数字
        支持多种格式：纯数字、JSON、带文字的数字等
        """
        if not response:
            return None

        response = response.strip()

        # 1. 尝试直接匹配纯数字 1/2/3
        if response in ['1', '2', '3']:
            return response

        # 2. 尝试从响应开头提取数字
        match = re.match(r'^([123])\b', response)
        if match:
            return match.group(1)

        # 3. 尝试解析 JSON
        json_data = extract_json_from_response(response, pmid)
        if isinstance(json_data, dict):
            score = json_data.get("score") or json_data.get("Score") or json_data.get("分数") or json_data.get("匹配性评分")
            if score:
                # 从评分字符串中提取数字
                score_str = str(score).strip()
                if score_str in ['1', '2', '3']:
                    return score_str
                match = re.search(r'([123])', score_str)
                if match:
                    return match.group(1)

        # 4. 从任意位置提取数字 1/2/3
        match = re.search(r'\b([123])\b', response)
        if match:
            return match.group(1)

        logging.warning(f"⚠️ PMID {pmid}: Could not extract score from response: {response[:100]}...")
        return None

    def _arbitrate_score(self, abstract: str, first_score: str, second_score: str, pmid: str) -> str:
        """第3次AI裁决评分"""
        # 从评分字符串中提取数字用于显示
        first_num = re.search(r'([123])', first_score)
        second_num = re.search(r'([123])', second_score)
        first_display = first_num.group(1) if first_num else first_score
        second_display = second_num.group(1) if second_num else second_score

        prompt = f"""# Task
Two independent scorers gave different scores. Choose the more accurate one.

# Scoring Criteria
{self.scoring_criteria}

# User Research Query
{self.user_query}

# Abstract
{abstract}

# Two Scores
- Score A: {first_display}
- Score B: {second_display}

# Output
Reply with ONLY one number: {first_display} or {second_display}

Your choice (just the number):"""

        try:
            response = self.ai_client._generate_content(
                prompt,
                use_pro_model=False,
                task_description=f"Score Arbitration 3rd (PMID: {pmid})"
            )

            # 使用通用的评分提取方法
            final_score = self._extract_score_from_response(response, pmid)
            if final_score:
                formatted = format_score_with_language(final_score, self.language_config)
                logging.info(f"   🎯 3rd arbitration result: {final_score} → {formatted}")
                return formatted

            # 裁决失败，选择较低的分数（保守）
            logging.warning(f"⚠️ PMID {pmid}: 3rd arbitration failed, choosing lower score")
            return min(first_score, second_score, key=lambda x: int(x[0]) if x and x[0].isdigit() else 0)

        except Exception as e:
            logging.error(f"❌ PMID {pmid}: 3rd arbitration failed - {e}")
            return min(first_score, second_score, key=lambda x: int(x[0]) if x and x[0].isdigit() else 0)


def create_screen_task(article_dict: dict, user_query: str, ai_client,
                       scoring_criteria: str, current_count: int,
                       current_round: int, language_config: dict,
                       controller: 'ScreeningController' = None) -> Optional[dict]:
    """
    创建筛选任务的便捷函数（用于并行处理）

    Args:
        article_dict: 文献数据
        user_query: 用户查询
        ai_client: AI客户端
        scoring_criteria: 评分标准
        current_count: 当前数量
        current_round: 当前轮次
        language_config: 语言配置
        controller: 筛选控制器（用于早期停止）

    Returns:
        筛选结果
    """
    screener = ArticleScreener(ai_client, user_query, scoring_criteria, language_config)
    return screener.screen(article_dict, current_count, current_round, controller=controller)
