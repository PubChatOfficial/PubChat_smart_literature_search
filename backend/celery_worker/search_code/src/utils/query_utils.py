"""
检索式相关工具函数

包含 JSON 提取、检索式清理、过滤条件构建等功能
"""

import re
import json
import logging

# Configure the logger for this module
logger = logging.getLogger(__name__)



# ============================================================
# 固定英文键名（AI 返回 JSON 的标准键名）
# ============================================================
FIXED_KEYS = [
    "score",
    "research_objective",
    "study_type",
    "research_method",
    "study_population",
    "main_results",
    "conclusions",
    "highlights"
]

# ============================================================
# 键名近义词映射（用于容错匹配）
# ============================================================
ALIAS_MAP = {
    # score 的变体
    "score": ["score", "relevance_score", "relevance score", "匹配性评分", "匹配度评分",
              "相关性评分", "评分", "分数", "puntuación", "score de pertinence",
              "punteggio", "relevanzbewertung", "оценка"],

    # research_objective 的变体
    "research_objective": ["research_objective", "research objective", "objective",
                          "研究目的", "目的", "objetivo", "objectif", "obiettivo",
                          "forschungsziel", "цель"],

    # study_type 的变体
    "study_type": ["study_type", "study type", "type", "研究类型", "类型",
                   "tipo de estudio", "type d'étude", "tipo di studio",
                   "studientyp", "тип исследования"],

    # research_method 的变体
    "research_method": ["research_method", "research method", "method", "methodology",
                        "研究方法", "方法", "método", "méthode", "metodo",
                        "forschungsmethode", "метод"],

    # study_population 的变体
    "study_population": ["study_population", "study population", "population",
                         "subjects", "participants", "研究对象", "对象", "人群",
                         "población", "population d'étude", "popolazione",
                         "studienpopulation", "популяция"],

    # main_results 的变体
    "main_results": ["main_results", "main results", "results", "findings",
                     "主要研究结果", "研究结果", "结果", "resultados",
                     "résultats", "risultati", "hauptergebnisse", "результаты"],

    # conclusions 的变体
    "conclusions": ["conclusions", "conclusion", "conclusions_and_significance",
                    "研究结论与意义", "研究结论", "结论", "conclusiones",
                    "conclusions et signification", "conclusioni",
                    "schlussfolgerungen", "выводы"],

    # highlights 的变体
    "highlights": ["highlights", "innovations", "highlights_and_innovations",
                   "研究亮点或创新点", "研究亮点", "亮点", "创新点",
                   "aspectos destacados", "points forts", "punti salienti",
                   "highlights und innovationen", "основные моменты"]
}


def extract_with_fuzzy_match(parsed_json: dict, pmid: str = "N/A") -> dict:
    """
    使用近义词映射从解析后的 JSON 中提取标准化字段

    Args:
        parsed_json: 已解析的 JSON 字典
        pmid: 文章 PMID（用于日志记录）

    Returns:
        标准化后的字典，使用 FIXED_KEYS 作为键名
    """
    if not parsed_json or not isinstance(parsed_json, dict):
        return {}

    result = {}

    # 将原始键名转为小写，方便匹配
    lowercase_json = {}
    original_keys = {}
    for k, v in parsed_json.items():
        lower_k = k.lower().strip()
        lowercase_json[lower_k] = v
        original_keys[lower_k] = k

    # 对每个标准键名，尝试从近义词中匹配
    for standard_key in FIXED_KEYS:
        aliases = ALIAS_MAP.get(standard_key, [standard_key])
        matched = False

        for alias in aliases:
            alias_lower = alias.lower().strip()
            if alias_lower in lowercase_json:
                result[standard_key] = lowercase_json[alias_lower]
                matched = True
                # 如果匹配到的不是标准键名，记录日志
                if alias_lower != standard_key:
                    logging.debug(f"🔄 PMID {pmid}: Mapped '{original_keys[alias_lower]}' -> '{standard_key}'")
                break

        if not matched:
            result[standard_key] = ""
            logging.debug(f"⚠️ PMID {pmid}: No match found for '{standard_key}'")

    return result


def extract_json_from_response(response_str: str, pmid: str = "N/A") -> dict:
    """
    从AI响应中提取JSON对象，处理各种格式问题

    Args:
        response_str: AI模型的原始响应字符串
        pmid: 文章PMID（用于日志记录）

    Returns:
        解析后的JSON字典，如果失败返回None，格式错误返回 "MALFORMED_JSON"

    处理的情况：
    - Markdown代码块标记 ```json ... ```
    - JSON前后的文字说明
    - 双大括号 {{...}}
    - 多余的空白字符
    - 常见的结尾文字（如"完成"、"done"等）
    """
    if not response_str or not isinstance(response_str, str):
        logging.warning(f"⚠️ Invalid response for article {pmid}: empty or not a string.")
        return None

    try:
        # 步骤1: 清理markdown代码块标记和常见的多余文字
        cleaned = response_str.strip()

        # 移除markdown代码块
        cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.IGNORECASE)

        # 移除常见的结尾文字（中英文）
        cleaned = re.sub(r'\s*done\s*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*完成\s*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*以上.*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*希望.*帮助.*$', '', cleaned, flags=re.IGNORECASE)

        cleaned = cleaned.strip()

        # 步骤2: 使用字符串索引方法提取JSON
        start_index = cleaned.find('{')
        last_index = cleaned.rfind('}')

        # 边界检查
        if start_index == -1 or last_index == -1 or start_index >= last_index:
            logging.warning(f"⚠️ No valid JSON boundaries found for article {pmid}.")
            logging.debug(f"   Response preview: {response_str[:200]}...")
            return None

        # 提取JSON字符串
        json_str = cleaned[start_index:last_index + 1]

        # 步骤3: 处理可能的双大括号问题
        if json_str.startswith('{{') and json_str.endswith('}}'):
            try:
                json.loads(json_str)
            except json.JSONDecodeError:
                logging.info(f"   Detected double braces for article {pmid}, removing outer layer.")
                json_str = json_str[1:-1].strip()

        # 步骤4: 解析JSON
        parsed = json.loads(json_str)

        # 步骤5: 验证是否为空对象
        if not parsed:
            logging.info(f"⚪ Article {pmid} returned empty JSON (not matched).")
            return None

        logging.debug(f"✅ Successfully extracted JSON for article {pmid}.")
        return parsed

    except json.JSONDecodeError as e:
        logging.warning(f"⚠️ JSON decode error for article {pmid}: {e}")
        logging.debug(f"   Original response: {response_str[:200]}...")
        if 'json_str' in locals():
            logging.debug(f"   Extracted JSON string for retry: {json_str[:200]}...")
        return "MALFORMED_JSON"

    except Exception as e:
        logging.error(f"❌ Unexpected error extracting JSON for article {pmid}: {e}", exc_info=True)
        return None


def clean_pubmed_query(query: str) -> str:
    """
    清理 PubMed 检索式，主要修复不匹配的括号

    Args:
        query: 原始检索式

    Returns:
        清理后的检索式
    """
    query = query.strip()
    # 如果检索式以 '((' 开头且括号不平衡，移除第一个括号
    if query.startswith('((') and query.count('(') != query.count(')'):
        temp_query = query[1:]
        if temp_query.count('(') == temp_query.count(')'):
            logging.info("   - 🔧 Cleaned query by removing an extra opening parenthesis.")
            return temp_query
    return query


def normalize_time_separator(time_value: str) -> str:
    """
    规范化时间范围分隔符，统一转换为英文冒号
    
    支持的分隔符：
    - 英文冒号 : (标准)
    - 中文冒号 ：
    - 英文破折号 -
    - 中文破折号 —
    - 英文波浪线 ~
    - 中文波浪线 ～ 〜
    
    Args:
        time_value: 用户输入的时间范围，如 "2020-2024" 或 "2020～2024"
    
    Returns:
        标准化后的时间范围，如 "2020:2024"
    """
    if not time_value:
        return time_value
    
    # 定义所有需要转换的分隔符
    separators = [
        '：',  # 中文冒号 (U+FF1A)
        '—',   # 中文破折号 (U+2014)
        '–',   # 英文短破折号 (U+2013)
        '-',   # 英文破折号/连字符
        '～',  # 中文波浪线 (U+FF5E)
        '〜',  # 波浪线 (U+301C)
        '~',   # 英文波浪线
    ]
    
    result = time_value.strip()
    for sep in separators:
        result = result.replace(sep, ':')
    
    return result


def build_search_filters_string(search_filters: dict) -> str:
    """
    将搜索过滤器字典转换为 PubMed 检索式的限制条件字符串

    Args:
        search_filters: 包含各种过滤条件的字典

    Returns:
        格式化的过滤条件字符串，如 "AND 2020:2024[dp] AND Nature[Journal]"
    """
    if not search_filters:
        return ""

    filter_parts = []

    # PubMed 字段映射
    field_mapping = {
        "time": "[dp]",
        "author": "[Author]",
        "first_author": "[Author - First]",
        "last_author": "[Author - Last]",
        "affiliation": "[Affiliation]",
        "journal": "[Journal]"
    }

    for key, value in search_filters.items():
        if value:
            if key == "custom":
                filter_parts.append(f"({value})")
            elif key in field_mapping:
                # 对时间字段进行分隔符规范化
                if key == "time":
                    value = normalize_time_separator(value)
                filter_parts.append(f"({value}{field_mapping[key]})")

    if filter_parts:
        return " AND " + " AND ".join(filter_parts)
    return ""

