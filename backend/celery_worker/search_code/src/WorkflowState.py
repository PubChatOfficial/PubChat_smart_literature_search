"""
工作流状态管理模块

管理工作流的状态和文件操作
"""

import os
import re
import logging
from datetime import datetime
from typing import Tuple, Set, List
from .RunningStatus import Status

from .utils.query_utils import build_search_filters_string

# Configure the logger for this module
logger = logging.getLogger(__name__)


class WorkflowState:
    """工作流状态管理类"""
    
    def __init__(self):
        """初始化状态"""
        # 核心状态
        self.retrieved_pmids: Set[str] = set()
        self.screened_articles: List[dict] = []
        self.current_round: int = 0
        self.scoring_criteria: str = ""
        self.is_continuing: bool = False

        # 核心参数
        self.task_number : str = ""
        self.current_query : str = ""
        self.outputlanguage : str = "en"
        self.search_settings : dict = {}
        self.search_filters: dict = {}
        self.journal_filters: dict = {}

        # 任务状态/任务执行参数
        self.status = Status.PENDING
        self.current_round = 0
        self.current_round_retrieved_articles = 0
        self.total_selected_articles = 0
        self.total_retrieved_articles = 0

        # 文件路径 - 使用相对于脚本的绝对路径
        self.result_dir: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "search_result")
        self.log_dir: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        self.criteria_file: str = ""
        self.query_file: str = ""
        self.pmid_file: str = ""
        self.excel_file: str = ""
        self.ris_file: str = ""
        self.log_file: str = ""

        # 配置引用
        self.max_refinement_attempts: int = 5
        
        # 期刊过滤相关
        self.journal_filter_stats: dict = {
            "total_before_filter": 0,
            "total_after_filter": 0,
            "total_no_issn": 0,
            "total_not_found": 0,
            "total_filtered_out": 0
        }
        
        # 会话统计（用于区分之前加载的和本次新增的）
        self.session_stats: dict = {
            "previous_pmids": 0,          # 之前从 CSV 加载的 PMID 数量
            "previous_articles": 0,       # 之前从 XLSX 加载的文章数量
            "session_new_articles": 0,    # 本次会话新增的筛选通过文章数量
        }
    
    def setup_file_paths(self, task_id: str, search_filters: dict = None, journal_filters: dict = None,
                        custom_result_dir: str = None, custom_log_dir: str = None) -> None:
        """
        设置项目文件路径

        Args:
            task_id: 任务编号
            search_filters: 搜索过滤条件（PubMed 检索层面）
            journal_filters: 期刊过滤条件（AI 筛选前过滤）
            custom_result_dir: 自定义结果输出目录（可选）
            custom_log_dir: 自定义日志输出目录（可选）
        """
        self.search_filters = search_filters or {}

        # 允许使用自定义目录
        if custom_result_dir:
            self.result_dir = custom_result_dir
        if custom_log_dir:
            self.log_dir = custom_log_dir

        # 确保输出目录存在
        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)
            logging.info(f"📁 Created directory: {self.result_dir}.")

        # 生成文件名前缀
        prefix = self._generate_filename_prefix(task_id, search_filters, journal_filters)

        # 设置文件路径
        self.criteria_file = os.path.join(self.result_dir, f"{prefix}_scoring_criteria.md")
        self.query_file = os.path.join(self.result_dir, f"{prefix}_search_queries.md")
        self.pmid_file = os.path.join(self.result_dir, f"{prefix}_pmids.csv")
        self.excel_file = os.path.join(self.result_dir, f"{prefix}_results.xlsx")
        self.ris_file = os.path.join(self.result_dir, f"{prefix}.ris")
        self.log_file = os.path.join(self.log_dir, f"{prefix}.log")

        # 检查是否是继续项目
        self.is_continuing = os.path.exists(self.criteria_file)

    def _generate_filename_prefix(self, task_id: str, search_filters: dict = None, journal_filters: dict = None) -> str:
        """生成文件名前缀"""
        prefix = task_id

        return prefix
    
    def save_scoring_criteria(self, scoring_criteria: str, user_query: str) -> None:
        """保存评分标准"""
        try:
            with open(self.criteria_file, 'w', encoding='utf-8') as f:
                f.write("# Scoring Criteria for Literature Matching\n\n")
                f.write(f"**User Query**: {user_query}\n\n")
                f.write("---\n\n")
                f.write(scoring_criteria)
                f.write(f"\n\n---\n\n*Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
            logging.info(f"🎯 Scoring criteria saved to {self.criteria_file}.")
            self.scoring_criteria = scoring_criteria
        except IOError as e:
            logging.error(f"❌ Failed to save scoring criteria: {e}")
    
    def save_search_query(self, search_query: str, user_query: str, 
                          round_number: int, total_found: int = 0, new_found: int = 0) -> None:
        """保存初始检索式"""
        if round_number > self.max_refinement_attempts:
            return
        try:
            filters_string = build_search_filters_string(self.search_filters)
            query_to_save = f"{search_query}{filters_string}" if filters_string else search_query
            
            with open(self.query_file, 'w', encoding='utf-8') as f:
                f.write("# Search Query Log\n\n")
                f.write(f"**User Query**: {user_query}\n\n")
                
                if self.search_filters:
                    f.write("**Search Filters**:\n")
                    filter_names = {
                        "time": "Time [dp]",
                        "author": "Author [Author]",
                        "first_author": "First Author [Author - First]",
                        "last_author": "Last Author [Author - Last]",
                        "affiliation": "Affiliation [Affiliation]",
                        "journal": "Journal [Journal]",
                        "custom": "Custom Filter"
                    }
                    for key, value in self.search_filters.items():
                        if value:
                            f.write(f"  - {filter_names.get(key, key)}: {value}\n")
                    f.write("\n")
                
                f.write("---\n\n")
                f.write("## Search History\n\n")
                f.write(f"## Task #{self.task_number}\n\n")
                f.write(f"**Task #{self.task_number} / Round #{round_number}:**\n")
                f.write(f"```\n{query_to_save}\n```\n\n")
                f.write(f"*Current Round Retrieved Articles: {total_found}*\n\n")
                f.write(f"*Current Round Retrieved New Articles: {new_found}*\n\n")
                f.write(f"*Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
            logging.info(f"📝 Initial search query saved (Task {self.task_number}/Round {round_number}).")
        except IOError as e:
            logging.error(f"❌ Failed to save search query: {e}")

    def append_search_query(self, search_query: str, round_number: int,
                            total_found: int = 0, new_found: int = 0) -> None:
        """追加检索式到日志"""
        if round_number > self.max_refinement_attempts:
            return
        try:
            filters_string = build_search_filters_string(self.search_filters)
            query_to_save = f"{search_query}{filters_string}" if filters_string else search_query

            with open(self.query_file, 'a', encoding='utf-8') as f:
                f.write(f"\n---\n\n")
                f.write(f"**Task #{self.task_number} / Round #{round_number}:**\n")
                f.write(f"```\n{query_to_save}\n```\n\n")
                f.write(f"*Current Round Retrieved Articles: {total_found}*\n\n")
                f.write(f"*Current Round Retrieved New Articles: {new_found}*\n\n")
                f.write(f"*Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
            logging.info(f"📝 Search query appended (Task {self.task_number}/Round {round_number}).")
        except IOError as e:
            logging.error(f"❌ Failed to append search query: {e}")

    def load_pmids(self) -> None:
        """加载已检索的 PMIDs"""
        from .utils.pubmed_utils import load_retrieved_pmids
        self.retrieved_pmids = load_retrieved_pmids(self.pmid_file)
        # 记录之前加载的 PMID 数量
        self.session_stats["previous_pmids"] = len(self.retrieved_pmids)
        logging.info(f"   - 📚 Loaded {len(self.retrieved_pmids)} previously retrieved PMIDs.")

    def save_pmids(self) -> None:
        """保存已检索的 PMIDs"""
        from .utils.pubmed_utils import save_retrieved_pmids
        save_retrieved_pmids(self.pmid_file, self.retrieved_pmids)

    def load_articles(self) -> None:
        """加载已筛选的文献"""
        if not self.is_continuing:
            return
        try:
            import pandas as pd
            # 读取所有 sheet (sheet_name=None 返回字典 {sheet_name: df})
            xls_data = pd.read_excel(self.excel_file, sheet_name=None)
            
            # 🔧 构建反向映射：显示名 -> 英文键名
            # 从语言配置获取字段映射
            reverse_field_map = {}
            if hasattr(self, 'language_config') and self.language_config and 'fields' in self.language_config:
                for eng_key, display_name in self.language_config['fields'].items():
                    reverse_field_map[display_name] = eng_key
            
            # 添加默认英文列名的映射（以防使用英文配置）
            default_english_map = {
                "No.": "index", "Journal Name": "journal", "Article Title": "title",
                "Publication Date": "publication_date", "Research Objective": "research_objective",
                "Study Type": "study_type", "Research Method": "research_method",
                "Study Population": "study_population", "Main Results": "main_results",
                "Conclusions and Significance": "conclusions", "Highlights and Innovations": "highlights",
                "First Author": "first_author", "Corresponding Author": "corresponding_author",
                "First Author Affiliation": "first_author_affiliation", "ISSN": "issn",
                "CAS Zone": "cas_zone", "JCR Zone": "jcr_zone", "Latest IF": "latest_if",
                "5-Year IF": "five_year_if", "Ranking": "ranking", "PMID": "pmid",
                "PubMed Link": "pubmed_link", "PMC Link": "pmc_link", "Full Text Link": "pmc_link",
                "Relevance Score": "score",
                # 🔧 旧版中文列名兼容性映射
                "PMC链接": "pmc_link", "全文链接": "pmc_link",
                "序号": "index", "期刊名称": "journal", "文章标题": "title",
                "发表时间": "publication_date", "研究目的": "research_objective",
                "研究类型": "study_type", "研究方法": "research_method",
                "研究对象": "study_population", "主要研究结果": "main_results",
                "研究结论与意义": "conclusions", "研究亮点或创新点": "highlights",
                "第一作者": "first_author", "通讯作者": "corresponding_author",
                "第一作者单位": "first_author_affiliation",
                "中科院分区": "cas_zone", "JCR分区": "jcr_zone", "最新IF": "latest_if",
                "5年IF": "five_year_if", "排名": "ranking", "PubMed链接": "pubmed_link",
                "匹配度评分": "score"
            }
            for display_name, eng_key in default_english_map.items():
                if display_name not in reverse_field_map:
                    reverse_field_map[display_name] = eng_key
            
            all_articles = []
            for sheet_name, df in xls_data.items():
                if not df.empty:
                    # 🔧 将显示名列名映射回英文键名
                    new_columns = {}
                    unmapped_cols = []
                    for col in df.columns:
                        if col in reverse_field_map:
                            new_columns[col] = reverse_field_map[col]
                        else:
                            new_columns[col] = col  # 保持原样
                            unmapped_cols.append(col)
                    
                    # 日志：显示映射结果
                    if unmapped_cols:
                        logging.debug(f"     Unmapped columns in '{sheet_name}': {unmapped_cols}")
                    
                    df = df.rename(columns=new_columns)
                    
                    # 将 NaN 替换为 None/空字符串，避免后续处理报错
                    df = df.where(pd.notnull(df), None)
                    records = df.to_dict('records')

                    # 🔧 从 sheet 名称恢复评分信息
                    # Sheet 名称格式如: "3分 (高度相关)", "2分 (中度相关)", "1分 (轻度相关)"
                    # 需要提取评分并恢复到每篇文章的 'score' 字段
                    score_from_sheet = sheet_name  # 直接使用 sheet 名称作为评分
                    for record in records:
                        # 如果文章没有评分字段，从 sheet 名称恢复
                        if not record.get('score'):
                            record['score'] = score_from_sheet

                    all_articles.extend(records)
                    logging.info(f"     - Loaded {len(records)} articles from sheet '{sheet_name}'")
            
            self.screened_articles = all_articles
            # 记录之前加载的文章数量
            self.session_stats["previous_articles"] = len(self.screened_articles)
            logging.info(f"   - 🔄 Loaded total {len(self.screened_articles)} existing articles from all sheets.")
        except (FileNotFoundError, Exception) as e:
            logging.warning(f"   - ⚠️ Could not load existing results: {e}. Starting fresh.")
            self.screened_articles = []

    def add_articles(self, articles: List[dict]) -> None:
        """添加筛选后的文献"""
        self.screened_articles.extend(articles)
        # 追踪本次会话新增的文章数量
        self.session_stats["session_new_articles"] += len(articles)

    def get_new_pmids(self, pmid_list: List[str]) -> List[str]:
        """获取未检索过的新 PMIDs"""
        return [pmid for pmid in pmid_list if pmid not in self.retrieved_pmids]

    def update_pmids(self, pmids: List[str]) -> None:
        """更新已检索的 PMIDs"""
        self.retrieved_pmids.update(pmids)

    def is_goal_achieved(self, threshold: int) -> bool:
        """检查是否达到目标"""
        return len(self.screened_articles) >= threshold

    def get_article_count(self) -> int:
        """获取已筛选文献数量"""
        return len(self.screened_articles)

    def update_journal_filter_stats(self, stats: dict) -> None:
        """
        更新期刊过滤统计

        Args:
            stats: {"before": int, "after": int, "no_issn": int, "not_found": int, "filtered_out": int}
        """
        self.journal_filter_stats["total_before_filter"] += stats.get("before", 0)
        self.journal_filter_stats["total_after_filter"] += stats.get("after", 0)
        self.journal_filter_stats["total_no_issn"] += stats.get("no_issn", 0)
        self.journal_filter_stats["total_not_found"] += stats.get("not_found", 0)
        self.journal_filter_stats["total_filtered_out"] += stats.get("filtered_out", 0)

    def get_journal_filter_stats(self) -> dict:
        """获取期刊过滤统计"""
        return self.journal_filter_stats

    def has_journal_filters(self) -> bool:
        """检查是否启用了期刊过滤"""
        return bool(self.journal_filters)

    def load_existing_project(self, user_query: str) -> bool:
        """
        加载现有项目的评分标准和最后的检索式

        Returns:
            是否成功加载
        """
        try:
            # 加载评分标准
            with open(self.criteria_file, 'r', encoding='utf-8') as f:
                self.scoring_criteria = f.read()

            # 加载最后的检索式
            with open(self.query_file, 'r', encoding='utf-8') as f:
                content = f.read()
                queries = re.findall(r'```\n(.*?)\n```', content, re.DOTALL)
                if queries:
                    from .utils.query_utils import clean_pubmed_query
                    self.current_query = clean_pubmed_query(queries[-1].strip())
                    logging.info(f"   - 🔄 Loaded last search query: {self.current_query[:100]}...")

                    # 追加新任务头
                    with open(self.query_file, 'a', encoding='utf-8') as qf:
                        qf.write(f"\n\n---\n\n## Task #{self.task_number}\n")
                    logging.info(f"   - 🚀 Starting new session: Task #{self.task_number}")
                    return True
                else:
                    raise FileNotFoundError("No queries found in file.")
        except (FileNotFoundError, Exception) as e:
            logging.error(f"❌ Critical error loading project files: {e}. Cannot continue.")
            return False

