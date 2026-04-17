"""
文献检索工作流模块

LiteratureWorkFlow 类封装了完整的文献检索和筛选流程
"""

import os
import logging
import time
import signal
import concurrent.futures
import concurrent.futures
from typing import List
import zipfile
import psycopg2 


# Add parent directory to path to allow imports from common_utils
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .ConfigLoader import ConfigLoader
from .WorkflowState import WorkflowState
from .ArticleScreener import ArticleScreener, ScreeningController, create_screen_task
from .utils.query_utils import clean_pubmed_query, build_search_filters_string

from .clients.PubmedClient import PubMedClient
from .clients.EuropePMCClient import EuropePMCClient
from .utils.data_processor import (
    parse_pubmed_xml, parse_europepmc_json, generate_formatted_excel, generate_ris_file,
    filter_articles_by_journal, get_journal_filter_display, enrich_articles_with_journal_info
)
from .utils.pmid_buffer import PMIDBuffer
from .clients import UnifiedAIClient

# 全局终止标志（用于优雅停止）
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Ctrl+C (SIGINT) and Termination (SIGTERM) signal handler"""
    global _shutdown_requested
    if _shutdown_requested:
        # Second signal, force exit
        local_logger = logging.getLogger(__name__)
        local_logger.info(f"\n⚠️ Force quit requested (Signal: {signum}). Exiting immediately...")
        os._exit(1)
    else:
        _shutdown_requested = True
        local_logger = logging.getLogger(__name__)
        local_logger.info(f"\n⏹️ Shutdown requested (Signal: {signum}). Waiting for current tasks to finish...")
        local_logger.info("   (Send signal again to force quit)")


class SearchWorkflow:
    """文献检索工作流类"""

    def __init__(self, task_id: str, user_query: str, output_language: str, llm_config: dict, search_settings: dict = None,
                search_filters: dict = None, journal_filters: dict = None, custom_result_dir: str = None, custom_log_dir: str = None):
        """
        初始化工作流

        Args:
            task_id: 任务编号
            outputlanguae: 输出语言 
            search_settings: 搜索设置
            user_query: 用户研究问题
            search_filters: 搜索过滤条件（PubMed 检索层面）
            journal_filters: 期刊过滤条件（AI 筛选前过滤）
            custom_result_dir: 自定义结果输出目录（可选）
            custom_log_dir: 自定义日志输出目录（可选）
            auto_run: 是否自动运行（默认True）

            task_id = "task_001"
            user_query = "nAMD抗VEGF治疗应答不良的最新进展"
            outputlanguae = "zh"
            llm_config = {
                "model": '',
                "api": ''
            }
            search_settings = {
                        "max_refinement_attempts": 30,
                        "min_study_threshold": 100
                    }
            search_filters = {
                "time": '2020:2024',
                "author": '',
                "first_author": '',
                "last_author": '',
                "affiliation": '',
                "journal": '',
                "custom": ''
            }
            journal_filters = {
                "impact_factor": '>3',
                "jcr_zone": 'q1-q4',
                "cas_zone": '1-4'
            }
        """
        # 1. 加载配置
        # self.config主要包含工作流参数，如AI提供商、最大检索轮次、目标文献数量，输出语言等
        self.config = ConfigLoader.load_env_config(output_language , search_settings)
        self.language_config = ConfigLoader.load_language_config(self.config["output_language"])

        # 2. 工作流状态
        self.state = WorkflowState()

        # 2. 成员变量
        self.user_query = user_query
        self.state.task_number = task_id
        self.state.outputlanguage = output_language
        # self.state.api_keys = api_keys
        self.state.search_settings = search_settings
        self.state.search_filters = search_filters or {}
        self.state.journal_filters = journal_filters or {}

        # 4. 初始化状态
        
        self.state.max_refinement_attempts = self.config["max_refinement_attempts"]
        # self.state.journal_filters = self.journal_filters  # 保存到状态中

        # 5. 设置文件路径（包含期刊过滤条件，以及可选的自定义目录）
        self.state.setup_file_paths(
            task_id, 
            search_filters, 
            journal_filters, 
            custom_result_dir=custom_result_dir, 
            custom_log_dir=custom_log_dir
        )

        # 6. 设置日志
        self.logger = self._setup_logging(task_id)
        
        # 7. 初始化 Redis
        self._init_redis()

        self._log_search_info()

        # 8. 初始化客户端
        self._initialize_clients(llm_config)

        # 8. 记录开始时间
        self._start_time = time.time()

        # 9. 自动运行
        self.run()
    
    def _setup_logging(self, task_id) -> logging.Logger:
        """设置项目专用日志"""
        # setup_logging()
        
        # self.project_logger = logging.getLogger()
        
        # 1. 准备 FileHandler
        file_handler = logging.FileHandler(self.state.log_file, mode='a', encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # 2. 配置工作流主 Logger
        task_logger = logging.getLogger(f"LiteratureSearch_{task_id}")
        task_logger.setLevel(logging.INFO)
        task_logger.propagate = False  # 不向上传播到 Root/Celery
        
        # 清除旧 handlers 避免重复
        if task_logger.hasHandlers():
            task_logger.handlers.clear()
        task_logger.addHandler(file_handler)

        # 3. 配置 src 包 Logger (统一客户端、工具类等)
        # 捕获所有 src.* 下产生的日志
        src_logger = logging.getLogger("src")
        src_logger.setLevel(logging.INFO)
        src_logger.propagate = False # 不向上传播到 Root/Celery
        
        # 清除旧 handlers
        if src_logger.hasHandlers():
            src_logger.handlers.clear()
        src_logger.addHandler(file_handler)

        # 🔇 禁用第三方库的 INFO 日志
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("google_genai.models").setLevel(logging.WARNING)
        
        task_logger.info(f"✅ Log system initialized for Task: {task_id}")

        return task_logger
    
    def _init_redis(self):
        """初始化 Redis 连接"""
        import redis
        try:
            # 使用 docker-compose 中定义的服务名 'redis'
            self.redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
            self.redis_expire_time = 1800 # 30分钟过期
            self.logger.info("✅ Redis connection established for progress updates.")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to connect to Redis: {e}")
            self.redis_client = None

    def _update_redis_status(self, status: str):
        """更新任务状态 'Pending' | 'Running' | 'Success' | 'Failed' | 'Stopped'"""
        if not self.redis_client: return
        try:
            key = f"task:{self.state.task_number}:info"
            self.redis_client.hset(key, "status", status)
            self.redis_client.expire(key, self.redis_expire_time)
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to update Redis status: {e}")

    def _update_redis_progress(self):
        """更新检索进度"""
        if not self.redis_client: return
        try:
            import json
            key = f"task:{self.state.task_number}:info"
            progress_data = {
                "current_round": self.state.current_round,
                "current_round_retrieved_articles": self.state.current_round_retrieved_articles, # 需要在 state 中维护这个值
                "total_selected_articles": self.state.get_article_count(),
                "total_retrieved_articles": self.state.total_retrieved_articles, # 需要维护总检索数
                "max_round": self.state.search_settings["max_refinement_attempts"],
                "auto_stop_articles": self.state.search_settings["min_study_threshold"]
            }
            self.redis_client.hset(key, "progress", json.dumps(progress_data))
            self.redis_client.expire(key, self.redis_expire_time)
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to update Redis progress: {e}")

    def _push_redis_retrieval(self, title: str, content: str):
        """追加检索记录"""
        if not self.redis_client: return
        try:
            import json
            key = f"task:{self.state.task_number}:retrieval"
            data = {
                "retrieval_title": title,
                "retrieval_content": content
            }
            self.redis_client.rpush(key, json.dumps(data))
            self.redis_client.expire(key, self.redis_expire_time)
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to push Redis retrieval: {e}")

    def _push_redis_articles(self, articles: List[dict]):
        """追加新筛选的文章 (逐个写入)"""
        if not self.redis_client: return
        try:
            import json
            key = f"task:{self.state.task_number}:articles"
            
            # 记录第一个作为 debug
            if articles:
                 self.logger.info(f"💾 DEBUG Redis Push: Sample Article 1 IF: {articles[0].get('latest_if')} | JCR: {articles[0].get('jcr_zone')}")

            # 计算起始编号
            start_index = self.state.get_article_count() - len(articles) + 1
            
            for idx, art in enumerate(articles):
                mapped = {
                    "no.": start_index + idx,
                    "score": art.get('score', ''),
                    "journal_name": art.get('journal', ''),
                    "article_title": art.get('title', ''),
                    "publication_date": str(art.get('publication_date', '')),
                    "research_objective": art.get('research_objective', ''),
                    "study_type": art.get('study_type', ''),
                    "research_method": art.get('research_method', ''),
                    "study_population": art.get('study_population', ''),
                    "main_results": art.get('main_results', ''),
                    "conclusions_and_significance": art.get('conclusions', ''),
                    "highlights_and_innovations": art.get('highlights', ''),
                    "first_author": art.get('first_author', ''),
                    "corresponding_author": art.get('corresponding_author', ''),
                    "first_author_affiliation": art.get('first_author_affiliation', ''),
                    "issn": art.get('issn', ''),
                    "category_partition": art.get('cas_zone', ''),
                    "jcr_partition": art.get('jcr_zone', ''),
                    "latest_if": art.get('latest_if', ''),
                    "5-year_if": art.get('five_year_if', ''),
                    "ranking": art.get('ranking', ''),
                    "pmid": art.get('pmid', ''),
                    "pubmed_link": art.get('pubmed_link', ''),
                    "pmc_link": art.get('pmc_link', '')
                }
                
                # 逐个写入 Redis
                self.redis_client.rpush(key, json.dumps(mapped))
                
            # 设置过期时间
            self.redis_client.expire(key, self.redis_expire_time)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to push Redis articles: {e}")

    
    def _log_search_info(self) -> None:
        """记录检索信息"""
        filters_log = ""
        if self.state.search_filters:
            filter_parts = []
            for key in ["time", "author", "first_author", "last_author", "affiliation", "journal", "custom"]:
                if self.state.search_filters.get(key):
                    filter_parts.append(f"{key}={self.state.search_filters[key]}")
            if filter_parts:
                filters_log = f" with filters: [{', '.join(filter_parts)}]"

        self.logger.info(f"🚀 Workflow started for query: '{self.user_query}'{filters_log}")
        
        # Redis 更新状态
        self._update_redis_status('Running')
        self._update_redis_progress()

        # 记录期刊过滤条件
        if self.state.journal_filters:
            journal_filter_display = get_journal_filter_display(self.state.journal_filters)
            self.logger.info(f"📰 Journal quality filter enabled: {journal_filter_display}")

        if self.state.is_continuing:
            self.logger.info("🔄 Continuing existing project.")
        else:
            self.logger.info("🆕 Starting new project.")

    def _initialize_clients(self, llm_config) -> None:
        """初始化 AI 和 PubMed/Europe PMC 客户端"""
        self.logger.info("2️⃣ Initializing clients...")

        # 使用统一的 AI 客户端（传递 task_id 用于 429 错误记录）
        self.ai_client = UnifiedAIClient(llm_config, task_id=self.state.task_number)
        self.logger.info(f"   - 🧠 AI Provider set to: {llm_config}")

        # PubMed 客户端（用于 esearch 和 fallback）
        self.pubmed_client = PubMedClient()
        
        # Europe PMC 客户端（用于主 efetch）
        self.europepmc_client = EuropePMCClient()
        self.logger.info("   - 🌍 Europe PMC client initialized (primary efetch source)")
        
        # PMID 缓存管理器（用于 PubMed 补充）
        self.pmid_buffer = PMIDBuffer(
            threshold=self.config["min_study_threshold"],
            trigger_ratio=0.9
        )
    
    def run(self) -> None:
        """执行主工作流"""
        global _shutdown_requested
        _shutdown_requested = False  # 重置终止标志
        
        # 注册信号处理器 (SIGINT 和 SIGTERM)
        original_int_handler = signal.signal(signal.SIGINT, _signal_handler)
        original_term_handler = signal.signal(signal.SIGTERM, _signal_handler)
        
        try:
            max_workers = self.config["ai_max_workers"] + 1
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers, 
                thread_name_prefix='Workflow'
            ) as executor:
                self._main_loop(executor)
            
            if _shutdown_requested:
                self.logger.info("⏹️ Workflow stopped by user request.")
                self._update_redis_status('Stopped') # User requested: Status should be 'Stopped'
            else:
                self.logger.info("🎉 Workflow completed successfully or reached max attempts!")
                self._update_redis_status('Success')
            
        except KeyboardInterrupt:
            self.logger.warning("⏹️ Workflow interrupted by user (Ctrl+C).")
            self._update_redis_status('Stopped')
        except Exception as e:
            self.logger.critical(f"💥 A critical error occurred during the workflow: {e}", exc_info=True)
            self._update_redis_status('Failed')
            raise
        finally:
            # 恢复原始信号处理器
            signal.signal(signal.SIGINT, original_int_handler)
            signal.signal(signal.SIGTERM, original_term_handler)
            self._finalize()
    
    def _main_loop(self, executor: concurrent.futures.ThreadPoolExecutor) -> None:
        """主循环"""
        # 加载数据
        self.state.load_pmids()
        # 设置语言配置，以便加载文章时正确映射列名
        self.state.language_config = self.language_config
        self.state.load_articles()
        
        # 初始化任务编号
        # self.state.task_number = self.state.get_new_task_number()
        
        # 初始化或加载评分标准和检索式
        if not self.state.is_continuing:
            self._generate_initial_criteria_and_query(executor)
        else:
            if not self.state.load_existing_project(self.user_query):
                return
        
        # 状态变量
        query_generation_future = None
        
        # 主检索循环
        for attempt in range(self.config["max_refinement_attempts"]):
            # 检查终止标志
            if _shutdown_requested:
                self.logger.info("⏹️ Shutdown requested, exiting main loop...")
                break
            
            current_round = attempt + 1
            self.state.current_round = current_round
            
            if not self.state.current_query:
                self.logger.error("❌ No current query to process. Exiting.")
                break
            
            # 🚀 第一轮优化：使用预先获取的数据（避免重复 esearch/efetch）
            if current_round == 1 and not self.state.is_continuing and hasattr(self, '_first_round_search_result'):
                self.logger.info(f"🔎 [Task {self.state.task_number}/Round 1] Using pre-fetched search result...")
                search_result = self._first_round_search_result
                new_pmids = self._first_round_pmids
                
                if not search_result or search_result.get("count", 0) == 0:
                    self.logger.warning(f"⚠️ [Task {self.state.task_number}/Round 1] yielded no results.")
                    # 清理临时变量
                    delattr(self, '_first_round_search_result')
                    delattr(self, '_first_round_pmids')
                    if hasattr(self, '_first_round_xml_future'):
                        delattr(self, '_first_round_xml_future')
                    continue
                    
                total_found = search_result.get("count", 0)
                new_found = len(new_pmids)
                self.logger.info(f"✅ Pre-fetched: {total_found} articles, {new_found} new")
                
                # 清理临时变量
                if hasattr(self, '_first_round_search_result'):
                    delattr(self, '_first_round_search_result')
                if hasattr(self, '_first_round_pmids'):
                    delattr(self, '_first_round_pmids')
                if hasattr(self, '_first_round_xml_future'):
                    delattr(self, '_first_round_xml_future')
                
                # 批量处理
                if new_pmids:
                    goal_achieved, query_generation_future = self._process_batches(
                        new_pmids, executor, current_round, query_generation_future
                    )
                    if goal_achieved:
                        return
                        
                continue
            
            self.logger.info(f"🔎 [Task {self.state.task_number}/Round {current_round}/{self.config['max_refinement_attempts']}] Using query: {self.state.current_query[:100]}...")

            # 🚀 立即推送 Redis（不等待 PubMed 验证）
            self._push_redis_retrieval(f"Round {current_round}", self.state.current_query)

            # 执行检索
            search_result = self._execute_search()

            if not search_result or search_result.get("count", 0) == 0:
                self.logger.warning(f"⚠️ [Task {self.state.task_number}/Round {current_round}] yielded no results.")
                if current_round >= self.config["max_refinement_attempts"]:
                    break

            # 📅 获取下一个检索式
                self.state.current_query = self._get_next_query(query_generation_future, current_round, 0)
                self.state.append_search_query(self.state.current_query, current_round + 1, 0, 0)
                # 🔄 Redis: Push empty retrieval for next round attempt? Or wait until it runs.
                query_generation_future = None
                continue

            # 处理检索结果
            all_pmids = search_result.get("idlist", [])
            total_found = search_result.get("count", 0)
            new_pmids = self.state.get_new_pmids(all_pmids)
            new_found = len(new_pmids)
            
            # 更新状态计数 - 这里只重置当前轮次计数，不直接累计 total（在 batch 中累计实际获取数）
            self.state.current_round_retrieved_articles = 0 # 重置为0，在 _process_batches 中累加
            if not hasattr(self.state, 'total_retrieved_articles'):
                 self.state.total_retrieved_articles = 0
            # self.state.total_retrieved_articles += new_found  <-- 移除，不使用 PMID 数量

            self.logger.info(f"✅ Search found {total_found} articles. {new_found} are new.")

            # 保存检索式 & Redis 推送
            if current_round == 1 and not self.state.is_continuing:
                self.state.save_search_query(self.state.current_query, self.user_query, current_round, total_found, new_found)
                # Redis push moved to before search
            else:
                self.state.append_search_query(self.state.current_query, current_round, total_found, new_found)
                # Redis push moved to before search
            
            # Redis: Update progress counters
            self._update_redis_progress()

            if not new_pmids:
                self.logger.warning("⚠️ No new PMIDs to process from this query.")
                if current_round >= self.config["max_refinement_attempts"]:
                    break

                self.state.current_query = self._get_next_query(query_generation_future, current_round, 0)
                query_generation_future = None
                continue

            # 批量处理
            goal_achieved, query_generation_future = self._process_batches(
                new_pmids, executor, current_round, query_generation_future
            )

            if goal_achieved:
                return

            # 检查是否完成
            if current_round >= self.config["max_refinement_attempts"]:
                break

            # 准备下一轮检索式
            if query_generation_future:
                try:
                    next_query = clean_pubmed_query(query_generation_future.result().strip().strip('`'))
                    self.logger.info(f"- ✅ Pre-generated query ready: {next_query[:150]}...")
                    self.state.current_query = next_query
                    query_generation_future = None
                except Exception as e:
                    self.logger.error(f"❌ Failed to get pre-generated query: {e}")
                    self.state.current_query = self._generate_next_query_sync(current_round, len(new_pmids))
            else:
                self.logger.warning("   No pre-generated query was scheduled. Breaking loop.")
                break

    def _execute_search(self) -> dict:
        """执行 PubMed 检索"""
        filters_string = build_search_filters_string(self.state.search_filters)
        query_to_send = f"{self.state.current_query}{filters_string}" if filters_string else self.state.current_query
        return self.pubmed_client.esearch(query_to_send)

    def _get_next_query(self, future, current_round: int, new_count: int) -> str:
        """获取下一个检索式"""
        if future:
            self.logger.info("   Waiting for pre-generated query...")
            return clean_pubmed_query(future.result().strip().strip('`'))
        else:
            self.logger.info("   Generating a new query synchronously...")
            return self._generate_next_query_sync(current_round, new_count)

    def _generate_next_query_sync(self, current_round: int, new_count: int) -> str:
        """同步生成下一个检索式"""
        result = self.ai_client.refine_pubmed_query(
            self.user_query,
            self.state.current_query,
            new_count,
            current_round,
            self.state.get_article_count(),
            self.config["max_refinement_attempts"],
            self.config["min_study_threshold"]
        )
        return clean_pubmed_query(result.strip().strip('`'))

    def _generate_initial_criteria_and_query(self, executor) -> None:
        """
        并行生成初始评分标准和检索式，并优化执行顺序：
        1. 并行启动：评分标准生成 + 检索式生成
        2. 检索式完成 → 立即 esearch + efetch (不等评分标准)
        3. 保存检索式 MD
        4. 等待评分标准完成 → 保存评分标准 MD
        5. 返回，准备开始筛选
        """
        self.logger.info("3️⃣ Starting parallel generation of scoring criteria and initial query...")

        # 并行启动两个 AI 任务
        criteria_future = executor.submit(
            self.ai_client.generate_scoring_criteria,
            self.user_query,
            self.language_config
        )
        query_future = executor.submit(
            self.ai_client.generate_pubmed_query,
            self.user_query,
            1
        )

        # 等待检索式完成（通常比评分标准快）
        self.logger.info("4️⃣ Waiting for initial search query...")
        self.state.current_query = clean_pubmed_query(query_future.result().strip().strip('`'))
        self.logger.info(f"   - ✅ Initial search query generated: {self.state.current_query[:100]}...")
        
        # 🚀 立即推送 Redis（不等待 PubMed 验证）
        self._push_redis_retrieval("Round 1", self.state.current_query)

        # 立即执行 esearch（不等待评分标准）
        self.logger.info("5️⃣ Executing first search (parallel with scoring criteria)...")
        search_result = self._execute_search()
        
        if search_result and search_result.get("count", 0) > 0:
            all_pmids = search_result.get("idlist", [])
            total_found = search_result.get("count", 0)
            new_pmids = self.state.get_new_pmids(all_pmids)
            new_found = len(new_pmids)
            
            # 保存检索式 MD（此时评分标准可能还在生成中）
            self.state.save_search_query(self.state.current_query, self.user_query, 1, total_found, new_found)
            
            # Redis: Push Round 1 info
            self.state.current_round = 1
            self.state.current_round_retrieved_articles = 0 # 重置为0，在 _process_batches 中累加
            if not hasattr(self.state, 'total_retrieved_articles'):
                 self.state.total_retrieved_articles = 0
            # self.state.total_retrieved_articles += new_found <-- 移除
            # self._push_redis_retrieval("Round 1", self.state.current_query) # Moved to before search
            self._update_redis_progress()
            
            self.logger.info(f"   - ✅ Search found {total_found} articles, {new_found} new")
            
            # 🚀 立即预取第一批 PMID（与评分标准生成并行）
            first_batch_size = 150
            first_batch_pmids = new_pmids[:first_batch_size]
            self.logger.info(f"   - 🌍 Pre-fetching first {len(first_batch_pmids)} articles from Europe PMC (parallel with scoring criteria)...")
            
            # 在后台线程中预取 Europe PMC 数据
            self._first_round_prefetch_future = executor.submit(
                self.europepmc_client.fetch_by_pmids,
                first_batch_pmids
            )
            
            # 保存 PMID 列表供 _main_loop 使用
            self._first_round_pmids = new_pmids
            self._first_round_search_result = search_result
        else:
            self.logger.warning("   - ⚠️ First search returned no results")
            self._first_round_pmids = []
            self._first_round_search_result = search_result
            self._first_round_prefetch_future = None
            # 仍然保存检索式 MD
            self.state.save_search_query(self.state.current_query, self.user_query, 1, 0, 0)

        # 等待评分标准完成
        self.logger.info("6️⃣ Waiting for scoring criteria...")
        scoring_criteria = criteria_future.result()
        self.state.save_scoring_criteria(scoring_criteria, self.user_query)
        self.logger.info("   - ✅ Scoring criteria generated and saved")

    def _process_batches(self, new_pmids: List[str], executor, current_round: int,
                         query_future) -> tuple:
        """
        批量处理 PMIDs

        Args:
            new_pmids: 要处理的 PMID 列表
            executor: 线程池执行器
            current_round: 当前轮次
            query_future: 预生成的检索式 Future

        Returns:
            (goal_achieved, query_generation_future)
        """
        # 🚀 动态批次大小：第一轮第一批用小批次，让用户快速看到结果
        first_batch_size = 150  # 第一批：快速出结果
        normal_batch_size = self.config["batch_size"]  # 后续批次：高效处理（默认600）
        
        # 计算批次数量（考虑第一批较小）
        if current_round == 1 and len(new_pmids) > first_batch_size:
            # 第一轮：第一批 150，剩余按 600 分批
            remaining = len(new_pmids) - first_batch_size
            remaining_batches = (remaining + normal_batch_size - 1) // normal_batch_size
            total_batches = 1 + remaining_batches
        else:
            # 非第一轮：全部按正常大小分批
            total_batches = (len(new_pmids) + normal_batch_size - 1) // normal_batch_size
            
        prefetch_future = None
        prefetch_batch_index = None
        
        # 🚀 PubMed 补充预取 Future（达到90%时异步启动）
        pubmed_supplement_future = None
        # 🚀 PubMed 补充准备好的文章（合并到下一批次）
        pubmed_supplement_articles = []
        
        # 🔢 创建筛选控制器（用于早期停止）
        controller = ScreeningController(
            threshold=self.config["min_study_threshold"],
            initial_count=self.state.get_article_count()
        )
        
        # 用于追踪当前处理位置
        current_position = 0

        for i in range(total_batches):
            # 检查终止标志
            if _shutdown_requested:
                self.logger.info("⏹️ Shutdown requested, stopping batch processing...")
                break
            # 🚀 动态确定当前批次大小
            if current_round == 1 and i == 0:
                current_batch_size = first_batch_size
            else:
                current_batch_size = normal_batch_size
            
            batch_start = current_position
            batch_end = min(current_position + current_batch_size, len(new_pmids))
            pmids_to_fetch = new_pmids[batch_start:batch_end]
            current_position = batch_end
            
            is_last_batch = (i == total_batches - 1)

            self.logger.info(f"📦 [Task {self.state.task_number}/Round {current_round}] Processing batch {i+1}/{total_batches} ({len(pmids_to_fetch)} PMIDs).")

            # 预生成下一轮检索式
            if is_last_batch and current_round < self.config["max_refinement_attempts"]:
                self.logger.info(f"⚡ Starting pre-generation of the next query...")
                query_future = executor.submit(
                    self.ai_client.refine_pubmed_query,
                    self.user_query,
                    self.state.current_query,
                    len(new_pmids),
                    current_round,
                    self.state.get_article_count(),
                    self.config["max_refinement_attempts"],
                    self.config["min_study_threshold"]
                )

            # 🌍 获取文献（优先 Europe PMC，失败则 PubMed fallback）
            # 🚀 第一轮第一批次：使用预取的 Europe PMC 数据
            if current_round == 1 and i == 0 and hasattr(self, '_first_round_prefetch_future') and self._first_round_prefetch_future:
                self.logger.info(f"  ⚡ Using pre-fetched Europe PMC data (parallel with scoring criteria)...")
                articles_in_batch, used_pubmed_fallback = self._fetch_batch(
                    pmids_to_fetch, self._first_round_prefetch_future, 0, 0
                )
                self._first_round_prefetch_future = None  # 清除预取数据
            else:
                articles_in_batch, used_pubmed_fallback = self._fetch_batch(
                    pmids_to_fetch, prefetch_future, prefetch_batch_index, i
                )
            
            prefetch_future = None
            prefetch_batch_index = None

            # 🚀 检查 PubMed 补充是否已完成，如果还在运行则等待一小段时间
            if pubmed_supplement_future:
                # 给 PubMed efetch 最多 2 秒的等待时间
                import concurrent.futures
                try:
                    # 等待最多 2 秒，如果完成则获取结果
                    xml_result = pubmed_supplement_future.result(timeout=2)
                    supplement_articles = self._prepare_pubmed_supplement_articles(xml_result)
                    if supplement_articles:
                        pubmed_supplement_articles.extend(supplement_articles)
                        self.logger.info(f"  📦 PubMed supplement ready: {len(supplement_articles)} articles prepared for this batch")
                    pubmed_supplement_future = None  # 成功处理，清除 Future
                except concurrent.futures.TimeoutError:
                    # 2 秒内未完成，继续处理当前批次，下一批次再合并
                    # 保留 pubmed_supplement_future，下一批次继续检查
                    self.logger.info(f"  ⏳ PubMed supplement still running, will merge in next batch")
                except Exception as e:
                    self.logger.warning(f"  ⚠️ PubMed supplement preparation failed: {e}")
                    pubmed_supplement_future = None  # 出错，清除 Future
            
            # 🚀 合并 PubMed 补充的文章到当前批次
            if pubmed_supplement_articles:
                original_count = len(articles_in_batch) if articles_in_batch else 0
                if articles_in_batch:
                    articles_in_batch.extend(pubmed_supplement_articles)
                else:
                    articles_in_batch = pubmed_supplement_articles
                self.logger.info(f"  🔄 Merged {len(pubmed_supplement_articles)} PubMed supplement articles into batch ({original_count} + {len(pubmed_supplement_articles)} = {len(articles_in_batch)})")
                pubmed_supplement_articles = []  # 清空，避免重复合并

            if not articles_in_batch:
                self.logger.warning(f"⚠️ No articles with abstract in batch {i+1}. Skipping.")
                # 仍然更新 PMIDs
                self.state.update_pmids(pmids_to_fetch)
                self.state.save_pmids()
                continue

            self.logger.info(f"  ...fetched {len(articles_in_batch)} articles with abstracts.")

            # 📊 更新实际检索计数 (Data Collection Point Corrected)
            fetched_count = len(articles_in_batch)
            self.state.current_round_retrieved_articles += fetched_count
            
            if not hasattr(self.state, 'total_retrieved_articles'):
                 self.state.total_retrieved_articles = 0
            self.state.total_retrieved_articles += fetched_count
            
            # 立即更新 Redis 进度
            self._update_redis_progress()

            # 🔍 期刊过滤（在 AI 筛选前）
            # 注意：articles_in_batch 现在已经是元数据字典列表
            if self.state.journal_filters:
                # 执行期刊过滤
                csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "search_code", "documents", "2025影响因子+2025年中科院分区.csv")
                filtered_articles, filter_stats = filter_articles_by_journal(
                    articles_in_batch,
                    self.state.journal_filters,
                    csv_path,
                    self.logger
                )

                # 更新统计
                self.state.update_journal_filter_stats(filter_stats)

                # 如果过滤后没有文章，跳过本批次
                if not filtered_articles:
                    self.logger.info(f"  ⚠️ No articles passed journal filter in this batch.")
                    # 仍然更新 PMIDs
                    self.state.update_pmids(pmids_to_fetch)
                    self.state.save_pmids()
                    continue

            # 用过滤后的文章替换
                articles_in_batch = filtered_articles
                self.logger.info(f"  📰 After journal filter: {len(articles_in_batch)} articles to screen.")

            # 🌍 预取下一批（使用 Europe PMC）
            if not is_last_batch:
                # 计算下一批次的 PMIDs
                next_batch_start = current_position
                next_batch_end = min(current_position + normal_batch_size, len(new_pmids))
                next_pmids = new_pmids[next_batch_start:next_batch_end]
                self.logger.info(f"  ⚡ Starting Europe PMC prefetch for batch {i+2}/{total_batches} ({len(next_pmids)} PMIDs)...")
                prefetch_future = executor.submit(self.europepmc_client.fetch_by_pmids, next_pmids)
                prefetch_batch_index = i + 1

            # 筛选文献（使用控制器支持早期停止）
            screened = self._screen_batch(articles_in_batch, executor, current_round, controller)

            # 持久化
            if screened:
                # 🛠️ Enrich for Redis (using robust logic from excel gen)
                csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "search_code", "documents", "2025影响因子+2025年中科院分区.csv")
                screened_enriched = enrich_articles_with_journal_info(
                    screened, csv_path, self.logger
                )

                self.state.add_articles(screened_enriched)
                # Redis 更新
                self._push_redis_articles(screened_enriched)
                self._update_redis_progress()
                
                self.logger.info(f"➕ Accumulated {len(screened)} new articles. Total: {self.state.get_article_count()}.")
                csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "search_code", "documents", "2025影响因子+2025年中科院分区.csv")
                generate_formatted_excel(
                    self.state.screened_articles,
                    csv_path,
                    self.state.excel_file,
                    self.language_config
                )
                # Generate RIS file for reference management software
                generate_ris_file(
                    self.state.screened_articles,
                    self.state.ris_file
                )
            
            # 🎯 检查是否应该触发 PubMed 补充请求（90% 阈值）
            # 异步启动预取，不阻塞主流程
            total_included = self.state.get_article_count()
            if pubmed_supplement_future is None and self.pmid_buffer.should_trigger(total_included):
                self.logger.info(f"🎯 90% threshold reached! Starting async PubMed supplement prefetch...")
                buffered_pmids = self.pmid_buffer.get_all_and_clear()
                if buffered_pmids:
                    # 🚀 异步启动 PubMed efetch，不等待结果
                    pubmed_supplement_future = executor.submit(
                        self.pubmed_client.efetch_by_pmids, buffered_pmids
                    )
                    self.logger.info(f"  ⚡ PubMed efetch started for {len(buffered_pmids)} PMIDs (running in background)")

            # 更新 PMIDs
            self.state.update_pmids(pmids_to_fetch)
            self.state.save_pmids()
            self.logger.info(f"💾 Updated master PMID list with {len(pmids_to_fetch)} PMIDs.")

            total_included = self.state.get_article_count()
            self.logger.info(f"🏁 Batch {i+1} finished. Total matching articles: {total_included}.")

            # 检查是否达到目标（通过控制器或状态检查）
            if controller.should_stop() or total_included >= self.config["min_study_threshold"]:
                self.logger.info(f"🎉 Goal achieved! Found {total_included} studies (threshold: {self.config['min_study_threshold']}).")
                # ⏹️ 已达到目标，不再需要 PubMed 补充
                if pubmed_supplement_future:
                    self.logger.info(f"  ⏹️ Skipping PubMed supplement (goal already reached)")
                    pubmed_supplement_future.cancel()  # 取消预取
                if query_future:
                    query_future.cancel()
                return True, None

        # 🚀 在所有批次结束后，处理异步 PubMed 补充结果（如果有）
        if pubmed_supplement_future:
            self._process_pubmed_supplement_result(pubmed_supplement_future, executor, controller)
            
        self.logger.info(f"🏁 All batches for current query complete.")
        return False, query_future

    def _fetch_batch(self, pmids: List[str], prefetch_future, prefetch_index: int, current_index: int) -> tuple:
        """
        获取批次数据（优先使用 Europe PMC，PubMed 作为 fallback）
        
        流程：
        1. 检查是否有预取的 Europe PMC 数据
        2. 如果没有预取或预取失败，直接调用 Europe PMC
        3. 如果 Europe PMC 完全失败，fallback 到 PubMed
        4. 解析结果，有摘要的文献返回，无摘要的加入缓存
        
        Args:
            pmids: 要获取的 PMID 列表
            prefetch_future: Europe PMC 预取的 Future
            prefetch_index: 预取的批次索引
            current_index: 当前批次索引
        
        Returns:
            Tuple[List[dict], bool]:
                - 有摘要的文献元数据列表（可直接用于 AI 筛选）
                - 是否使用了 PubMed fallback
        """
        use_pubmed_fallback = False
        json_data = None
        missing_pmids = []
        
        # 尝试使用 Europe PMC（优先使用预取数据）
        try:
            # 检查是否有预取的 Europe PMC 数据
            if prefetch_future and prefetch_index == current_index:
                # 注：日志已在 _process_batches 中打印，这里不重复
                try:
                    json_data, missing_pmids = prefetch_future.result(timeout=60)
                    if json_data:
                        self.logger.info(f"  ✅ Prefetched Europe PMC data retrieved successfully")
                    else:
                        # 预取失败，重新请求
                        self.logger.warning(f"  ⚠️ Prefetch returned empty, fetching synchronously...")
                        json_data, missing_pmids = self.europepmc_client.fetch_by_pmids(pmids)
                except Exception as e:
                    self.logger.warning(f"  ⚠️ Prefetch failed ({e}), fetching synchronously...")
                    json_data, missing_pmids = self.europepmc_client.fetch_by_pmids(pmids)
            else:
                # 没有预取，直接请求
                self.logger.info(f"  🌍 Fetching {len(pmids)} articles from Europe PMC...")
                json_data, missing_pmids = self.europepmc_client.fetch_by_pmids(pmids)
            
            if json_data is None:
                # Europe PMC 完全失败，fallback 到 PubMed
                raise Exception("Europe PMC returned None")
            
            # 解析 Europe PMC 返回的 JSON
            articles_with_abstract, no_abstract_recent, no_abstract_old = parse_europepmc_json(
                json_data, self.logger
            )
            
            # 将缺失的 PMID 和无摘要的近90天文献加入缓存
            if missing_pmids:
                self.pmid_buffer.add_missing_pmids(missing_pmids)
                self.logger.info(f"  📦 Added {len(missing_pmids)} missing PMIDs to buffer")
            
            if no_abstract_recent:
                self.pmid_buffer.add_no_abstract_pmids(no_abstract_recent)
                self.logger.info(f"  📦 Added {len(no_abstract_recent)} no-abstract PMIDs (recent) to buffer")
            
            if no_abstract_old:
                self.logger.info(f"  🗑️ Discarded {len(no_abstract_old)} no-abstract PMIDs (old, >90 days)")
            
            self.logger.info(f"  ✅ Europe PMC: {len(articles_with_abstract)} articles ready for screening")
            
            return articles_with_abstract, use_pubmed_fallback
            
        except Exception as e:
            # Europe PMC 失败，使用 PubMed fallback
            self.logger.warning(f"  ⚠️ Europe PMC failed ({e}), falling back to PubMed...")
            use_pubmed_fallback = True
            
            try:
                # 检查是否有预取的数据 --- REMOVED INCORRECT LOGIC
                # 如果进入 fallback，说明 Europe PMC 失败或预取的数据无效
                # 因此必须直接从 PubMed 获取新的 XML 数据
                self.logger.info(f"  🔄 Fetching from PubMed (fallback)...")
                xml_data = self.pubmed_client.efetch_by_pmids(pmids)
                
                if not xml_data:        
                    self.logger.error(f"  ❌ PubMed fallback also failed")
                    return [], use_pubmed_fallback
                
                # 解析 PubMed XML
                articles = parse_pubmed_xml(xml_data, self.logger)
                
                # 使用原有的 extract_article_metadata 提取元数据
                from .utils.data_processor import extract_article_metadata
                articles_with_abstract = []
                
                for article in articles:
                    metadata = extract_article_metadata(article)
                    abstract = metadata.get("abstract", "")
                    
                    # 检查是否有实际摘要内容
                    if abstract and abstract.strip() and abstract != "No abstract available.":
                        metadata["_source"] = "pubmed_fallback"
                        articles_with_abstract.append(metadata)
                    else:
                        # PubMed 也没有摘要，直接丢弃
                        pmid = metadata.get("pmid", "unknown")
                        self.logger.debug(f"  🗑️ Discarding PMID {pmid}: no abstract in PubMed")
                
                self.logger.info(f"  ✅ PubMed fallback: {len(articles_with_abstract)} articles ready for screening")
                
                return articles_with_abstract, use_pubmed_fallback
                
            except Exception as e2:
                self.logger.error(f"  ❌ PubMed fallback also failed: {e2}")
                return [], use_pubmed_fallback

    def _process_pubmed_supplement(self, executor, controller: ScreeningController) -> None:
        """
        处理 PubMed 补充请求（当达到 90% 阈值时触发）
        
        流程：
        1. 获取缓存中的所有 PMID
        2. 调用 PubMed efetch 获取文献
        3. 解析并过滤有摘要的文献
        4. 异步进行 AI 筛选
        5. 合并到已筛选文献列表
        
        Args:
            executor: 线程池执行器
            controller: 筛选控制器
        """
        # 获取缓存中的所有 PMID
        buffered_pmids = self.pmid_buffer.get_all_and_clear()
        
        if not buffered_pmids:
            self.logger.info("📦 No PMIDs in buffer to supplement")
            return
        
        self.logger.info(f"🔄 Processing PubMed supplement for {len(buffered_pmids)} PMIDs...")
        
        try:
            # 调用 PubMed efetch
            xml_data = self.pubmed_client.efetch_by_pmids(buffered_pmids)
            
            if not xml_data:
                self.logger.warning("⚠️ PubMed supplement request failed, skipping")
                return
            
            # 解析 PubMed XML
            articles = parse_pubmed_xml(xml_data, self.logger)
            
            # 提取元数据并过滤有摘要的文献
            from .utils.data_processor import extract_article_metadata
            articles_with_abstract = []
            
            for article in articles:
                metadata = extract_article_metadata(article)
                abstract = metadata.get("abstract", "")
                
                if abstract and abstract.strip() and abstract != "No abstract available.":
                    metadata["_source"] = "pubmed_supplement"
                    articles_with_abstract.append(metadata)
                else:
                    pmid = metadata.get("pmid", "unknown")
                    self.logger.debug(f"  🗑️ Discarding PMID {pmid}: no abstract in PubMed supplement")
            
            if not articles_with_abstract:
                self.logger.info("📦 No articles with abstract in PubMed supplement")
                return
            
            self.logger.info(f"📦 PubMed supplement: {len(articles_with_abstract)} articles with abstract")
            
            # 期刊过滤（如果有）
            if self.state.journal_filters:
                csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "search_code", "documents", "2025影响因子+2025年中科院分区.csv")
                filtered_articles, filter_stats = filter_articles_by_journal(
                    articles_with_abstract,
                    self.state.journal_filters,
                    csv_path,
                    self.logger
                )
                
                self.state.update_journal_filter_stats(filter_stats)
                
                if not filtered_articles:
                    self.logger.info("📦 No articles passed journal filter in PubMed supplement")
                    return
                
                articles_with_abstract = filtered_articles
            
            # AI 筛选
            screened = self._screen_batch(articles_with_abstract, executor, 0, controller)
            
            if screened:
                self.state.add_articles(screened)
                self.logger.info(f"➕ PubMed supplement added {len(screened)} articles. Total: {self.state.get_article_count()}.")
                
                # 更新输出文件
                csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "search_code", "documents", "2025影响因子+2025年中科院分区.csv")
                generate_formatted_excel(
                    self.state.screened_articles,
                    csv_path,
                    self.state.excel_file,
                    self.language_config
                )
                generate_ris_file(
                    self.state.screened_articles,
                    self.state.ris_file
                )
            
        except Exception as e:
            self.logger.error(f"❌ PubMed supplement failed: {e}")
            # 不抛出异常，继续主流程

    def _prepare_pubmed_supplement_articles(self, xml_data) -> List[dict]:
        """
        准备 PubMed 补充的文章（解析、过滤），但不执行 AI 筛选
        
        Args:
            xml_data: PubMed efetch 返回的 XML 数据
        
        Returns:
            准备好的文章元数据列表（可直接加入批次进行 AI 筛选）
        """
        if not xml_data:
            return []
        
        try:
            # 解析 PubMed XML
            articles = parse_pubmed_xml(xml_data, self.logger)
            
            if not articles:
                return []
            
            # 提取元数据并过滤有摘要的文献
            from .utils.data_processor import extract_article_metadata
            articles_with_abstract = []
            
            for article in articles:
                metadata = extract_article_metadata(article)
                abstract = metadata.get("abstract", "")
                
                if abstract and abstract.strip() and abstract != "No abstract available.":
                    metadata["_source"] = "pubmed_supplement"
                    articles_with_abstract.append(metadata)
            
            if not articles_with_abstract:
                self.logger.info("📦 No articles with abstract in PubMed supplement")
                return []
            
            self.logger.info(f"📦 PubMed supplement: {len(articles_with_abstract)} articles with abstract")
            
            # 期刊过滤（如果有）
            if self.state.journal_filters:
                csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "search_code", "documents", "2025影响因子+2025年中科院分区.csv")
                filtered_articles, filter_stats = filter_articles_by_journal(
                    articles_with_abstract,
                    self.state.journal_filters,
                    csv_path,
                    self.logger
                )
                
                self.state.update_journal_filter_stats(filter_stats)
                
                if not filtered_articles:
                    self.logger.info("📦 No articles passed journal filter in PubMed supplement")
                    return []
                
                return filtered_articles
            
            return articles_with_abstract
            
        except Exception as e:
            self.logger.error(f"❌ PubMed supplement preparation failed: {e}")
            return []

    def _process_pubmed_supplement_result(self, supplement_future, executor, controller: ScreeningController) -> None:
        """
        处理异步 PubMed 补充预取的结果
        
        Args:
            supplement_future: PubMed efetch 的 Future 对象
            executor: 线程池执行器
            controller: 筛选控制器
        """
        try:
            self.logger.info("🔄 Processing async PubMed supplement result...")
            
            # 获取预取结果（此时应该已经完成）
            xml_data = supplement_future.result(timeout=60)
            
            if not xml_data:
                self.logger.warning("⚠️ PubMed supplement prefetch returned empty")
                return
            
            # 解析 PubMed XML
            articles = parse_pubmed_xml(xml_data, self.logger)
            
            # 提取元数据并过滤有摘要的文献
            from .utils.data_processor import extract_article_metadata
            articles_with_abstract = []
            
            for article in articles:
                metadata = extract_article_metadata(article)
                abstract = metadata.get("abstract", "")
                
                if abstract and abstract.strip() and abstract != "No abstract available.":
                    metadata["_source"] = "pubmed_supplement"
                    articles_with_abstract.append(metadata)
            
            if not articles_with_abstract:
                self.logger.info("📦 No articles with abstract in PubMed supplement")
                return
            
            self.logger.info(f"📦 PubMed supplement: {len(articles_with_abstract)} articles with abstract")
            
            # 期刊过滤（如果有）
            if self.state.journal_filters:
                csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "search_code", "documents", "2025影响因子+2025年中科院分区.csv")
                filtered_articles, filter_stats = filter_articles_by_journal(
                    articles_with_abstract,
                    self.state.journal_filters,
                    csv_path,
                    self.logger
                )
                
                self.state.update_journal_filter_stats(filter_stats)
                
                if not filtered_articles:
                    self.logger.info("📦 No articles passed journal filter in PubMed supplement")
                    return
                
                articles_with_abstract = filtered_articles
            
            # AI 筛选
            screened = self._screen_batch(articles_with_abstract, executor, 0, controller)
            
            if screened:
                self.state.add_articles(screened)
                self.logger.info(f"➕ PubMed supplement added {len(screened)} articles. Total: {self.state.get_article_count()}.")
                
                # 更新输出文件
                csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "search", "documents", "2025影响因子+2025年中科院分区.csv")
                generate_formatted_excel(
                    self.state.screened_articles,
                    csv_path,
                    self.state.excel_file,
                    self.language_config
                )
                generate_ris_file(
                    self.state.screened_articles,
                    self.state.ris_file
                )
        
        except Exception as e:
            self.logger.error(f"❌ PubMed supplement result processing failed: {e}")
            # 不抛出异常，继续主流程

    def _screen_batch(self, articles: List[dict], executor, current_round: int,
                       controller: ScreeningController) -> List[dict]:
        """
        筛选一批文献（支持早期停止）
        
        Args:
            articles: 待筛选的文献列表
            executor: 线程池执行器
            current_round: 当前轮次
            controller: 筛选控制器（用于早期停止和计数）
        
        Returns:
            筛选通过的文献列表
        """
        futures = {}
        
        # 提交任务（检查是否应该停止）
        for article in articles:
            if controller.should_stop():
                self.logger.info(f"⏹️ Goal reached ({controller.threshold} articles), stopping new screening tasks")
                break
            
            pmid = article.get("pmid", article.get("PMID", "unknown"))
            future = executor.submit(
                create_screen_task,
                article,
                self.user_query,
                self.ai_client,
                self.state.scoring_criteria,
                controller.get_count(),
                current_round,
                self.language_config,
                controller
            )
            futures[future] = pmid
        
        # 收集结果
        screened = []
        for future in concurrent.futures.as_completed(futures):
            pmid = futures[future]
            try:
                result = future.result()
                if result:
                    screened.append(result)
            except Exception as e:
                self.logger.error(f"❌ Error screening PMID {pmid}: {e}")
        
        return screened
    
    def _close_logging(self):
       # 1. 获取 Root Logger
        root_logger = logging.getLogger()
        
        # 2. 寻找属于当前文件的 Handler
        handlers_to_remove = []
        target_log_file = os.path.abspath(self.state.log_file)

        for handler in root_logger.handlers:
            # 只处理 FileHandler
            if isinstance(handler, logging.FileHandler):
                # 检查这个 handler 写入的文件是不是当前任务的文件
                if os.path.abspath(handler.baseFilename) == target_log_file:
                    handlers_to_remove.append(handler)
        
        # 3. 移除并关闭
        for handler in handlers_to_remove:
            try:
                handler.close()
                root_logger.removeHandler(handler)
            except Exception as e:
                root_logger.error(f"❌ 关闭日志句柄失败: {e}")

    def _finalize(self) -> None:
        """收尾工作"""
        # 获取会话统计
        session = self.state.session_stats
        prev_pmids = session.get("previous_pmids", 0)
        prev_articles = session.get("previous_articles", 0)
        session_new_articles = session.get("session_new_articles", 0)
        total_pmids = len(self.state.retrieved_pmids)
        total_articles = self.state.get_article_count()
        session_new_pmids = total_pmids - prev_pmids

        # 最终统计
        summary_lines = [
            "="*50,
            " F I N A L  S U M M A R Y",
            "="*50,
            f"🔄 Total rounds of search attempts: {self.state.current_round}",
        ]

        # 检索文章统计（区分之前和本次）
        if prev_pmids > 0:
            summary_lines.extend([
                f"📚 Retrieved Articles (PMIDs saved to CSV):",
                f"   • This session: {session_new_pmids}",
                f"   • Previous (from CSV): {prev_pmids}",
                f"   • Total: {total_pmids}",
            ])
        else:
            summary_lines.append(f"📚 Total Retrieved Articles: {total_pmids}")

        # 期刊过滤统计
        if self.state.has_journal_filters():
            journal_filter_display = get_journal_filter_display(self.state.journal_filters)
            stats = self.state.get_journal_filter_stats()
            # total_before_filter 已经是所有输入文章的数量（包括没有ISSN的）
            before = stats["total_before_filter"]
            after = stats["total_after_filter"]
            filtered_out = before - after
            filter_rate = (filtered_out / before * 100) if before > 0 else 0

            summary_lines.extend([
                f"📰 Journal Filter (articles actually returned by PubMed):",
                f"   • Filter: {journal_filter_display}",
                f"   • Before: {before} → After: {after} | Filtered out: {filtered_out} ({filter_rate:.1f}%)",
                f"🤖 Total AI Screened Articles: {after}",
            ])

        # 筛选文章统计（区分之前和本次）
        if prev_articles > 0:
            summary_lines.extend([
                f"🎯 Selected Articles (passed AI screening):",
                f"   • This session: {session_new_articles}",
                f"   • Previous (from XLSX): {prev_articles}",
                f"   • Total: {total_articles}",
            ])
        else:
            summary_lines.append(f"🎯 Total Selected Articles: {total_articles}")

        summary_lines.append("="*50)

        # Token 使用统计（按模型分类）
        if hasattr(self.ai_client, 'token_stats') and self.ai_client.token_stats:
            stats = self.ai_client.token_stats
            summary_lines.append("📊 Token Usage Statistics (by Model):")
            summary_lines.append("-"*50)

            # 汇总统计
            total_input = 0
            total_output = 0
            total_tokens = 0
            total_calls = 0

            # 按模型输出统计
            for model_name, model_stats in stats.items():
                summary_lines.extend([
                    f"📌 {model_name}:",
                    f"   • API Calls: {model_stats['api_calls']:,}",
                    f"   • Input: {model_stats['input_tokens']:,} | Output: {model_stats['output_tokens']:,} | Total: {model_stats['total_tokens']:,}",
                    "-"*50
                ])
                total_input += model_stats['input_tokens']
                total_output += model_stats['output_tokens']
                total_tokens += model_stats['total_tokens']
                total_calls += model_stats['api_calls']

            # 汇总
            summary_lines.extend([
                "📊 TOTAL:",
                f"   • API Calls: {total_calls:,}",
                f"   • Input: {total_input:,} | Output: {total_output:,} | Total: {total_tokens:,}",
            ])

        # 任务总时间
        if hasattr(self, '_start_time'):
            elapsed = time.time() - self._start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            if hours > 0:
                time_str = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                time_str = f"{minutes}m {seconds}s"
            else:
                time_str = f"{seconds}s"
            summary_lines.append(f"⏱️ Total Duration: {time_str}")
        
        summary_lines.append("="*50)

        # 输出统计
        self.logger.info("\n")
        for line in summary_lines:
            self.logger.info(line)

        # 关闭日志处理器
        self.logger.info(f"💾 Project log saved to: {self.state.log_file}")
        # 安全关闭日志
        self._close_logging()
        
        # 压缩文件并上传数据库
        if not _shutdown_requested:
            self._finalize_files()

    def _finalize_files(self):
        """压缩文件并写入数据库"""
        try:
            task_id = self.state.task_number
            result_dir = self.state.result_dir # Use correct result_dir attribute
            
            # 待压缩的文件列表
            files_to_zip = [
                f"{task_id}_pmids.csv",
                f"{task_id}_results.xlsx",
                f"{task_id}_scoring_criteria.md",
                f"{task_id}_search_queries.md",
                f"{task_id}.ris"
            ]
            
            zip_filename = f"{task_id}_results.zip"
            zip_filepath = os.path.join(result_dir, zip_filename)
            
            # 1. 压缩文件
            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files_to_zip:
                    file_path = os.path.join(result_dir, file)
                    if os.path.exists(file_path):
                        zipf.write(file_path, arcname=file)
            
            if not os.path.exists(zip_filepath):
               self.logger.warning("Failed to create zip file.")
               raise Exception("Failed to create zip file.")

            # 2. 计算大小 (MB)
            file_size_bytes = os.path.getsize(zip_filepath)
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            # 3. 写入数据库
            db_config = {
                "database": os.getenv("POSTGRES_DB"),
                "user": os.getenv("POSTGRES_USER"), 
                "password": os.getenv("POSTGRES_PASSWORD"),
                "host": os.getenv("POSTGRES_HOST"),
                "port": os.getenv("POSTGRES_PORT")
            }
            
            download_link = f"search-document/{zip_filename}" # 假设相对路径或根据需求调整

            conn = None
            try:
                conn = psycopg2.connect(**db_config)
                with conn.cursor() as cur:
                    try:
                        # 3.1 插入文档记录
                        insert_query = """
                            INSERT INTO "userSchema"."documents" 
                            (task_id, size, user_query, created_time, download_link)
                            VALUES (%s, %s, %s, NOW(), %s)
                        """
                        cur.execute(insert_query, (
                            task_id, 
                            file_size_mb, 
                            self.user_query, 
                            download_link
                        ))

                        # # 3.2 更新任务状态并扣减用户次数 (在一个事务中)
                        # # 更新任务状态为 completed
                        # cur.execute("""
                        #     UPDATE "userSchema"."tasks" 
                        #     SET status = 'completed' 
                        #     WHERE id = %s
                        # """, (task_id,))

                        # # 更新用户状态：is_running = false 并 扣减次数
                        # # 注意：只有在任务真正完成时才扣减次数
                        # cur.execute("""
                        #     UPDATE "userSchema"."users" 
                        #     SET is_running = false, 
                        #         available_times = available_times - 1 
                        #     WHERE id = %s
                        # """, (self.user_id,))
                        
                        conn.commit()
                        self.logger.info(f"✅ Zip file metadata inserted. Task marked completed. User quota decremented. Size: {file_size_mb:.2f}MB")
                    
                    except Exception as db_err:
                        conn.rollback() # 回滚事务
                        self.logger.error(f"❌ Database transaction failed: {db_err}")
                        raise db_err
        
                # 3.5 Update Redis with download link
                try:
                     self.redis_client.hset(
                        f"task:{task_id}:info",
                        mapping={"download_link": download_link}
                    )
                except Exception as e:
                    self.logger.error(f"Failed to update Redis with download link: {e}")

                # # 3.6 Invalidate User Detail Cache in Redis
                # try:
                #     user_detail_key = f"user_detail:{self.user_id}"
                #     self.redis_client.delete(user_detail_key)
                #     self.logger.info(f"Invalidated Redis user cache: {user_detail_key}")
                # except Exception as e:
                #     self.logger.error(f"Failed to invalidate Redis user cache: {e}")
            
            except Exception as e:
                self.logger.error(f"❌ Database connection or operation failed: {e}")
                raise
            finally:
                if conn:
                    conn.close()

            # 4. 删除原文件
            for file in files_to_zip:
                file_path = os.path.join(result_dir, file)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        self.logger.warning(f"Failed to delete {file}: {e}")
                        raise
            
            self.logger.info("✅ Original files deleted after compression.")

        except Exception as e:
            self.logger.error(f"❌ Finalize files failed: {e}")
            raise


