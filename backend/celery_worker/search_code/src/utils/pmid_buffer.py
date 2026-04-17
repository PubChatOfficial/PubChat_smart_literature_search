"""
PMID 缓存管理器

累积需要向 PubMed 补充请求的 PMID，在达到 90% 目标时触发补充请求。
"""

import logging
from typing import List, Set, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class PMIDBuffer:
    """
    智能 PMID 缓存管理器
    
    用于累积 Europe PMC 无法获取或无摘要的 PMID，
    在适当时机触发 PubMed 补充请求。
    
    设计思路：
    - Europe PMC 缺失率仅约 1%，大部分情况下缓存 PMID 数量很少
    - 当已筛选文献达到目标的 90% 时触发补充，避免文献过多
    - 线程安全，支持并发环境
    
    触发条件：
    - 已筛选数量 >= 目标数量 * 0.9
    - 缓存中有 PMID
    
    Attributes:
        threshold: 目标文献数量阈值
        trigger_ratio: 触发比例，默认 0.9 (90%)
    """
    
    def __init__(self, threshold: int, trigger_ratio: float = 0.9):
        """
        初始化缓存管理器
        
        Args:
            threshold: 目标文献数量（min_study_threshold）
            trigger_ratio: 触发补充请求的比例，默认 0.9
        """
        self.threshold = threshold
        self.trigger_ratio = trigger_ratio
        self.trigger_count = int(threshold * trigger_ratio)
        
        # 缓存的 PMID（使用 Set 避免重复）
        self._missing_pmids: Set[str] = set()  # Europe PMC 完全未返回的
        self._no_abstract_pmids: Set[str] = set()  # 有返回但无摘要（近90天）
        
        # 线程锁
        self._lock = Lock()
        
        # 是否已触发过
        self._triggered = False
        
        logger.info(f"📦 PMID Buffer initialized: threshold={threshold}, "
                   f"trigger at {int(trigger_ratio * 100)}% ({self.trigger_count} articles)")
    
    def add_missing_pmids(self, pmids: List[str]) -> None:
        """
        添加 Europe PMC 完全未返回的 PMID
        
        Args:
            pmids: PMID 列表
        """
        if not pmids:
            return
        
        with self._lock:
            before_count = len(self._missing_pmids)
            self._missing_pmids.update(pmids)
            added = len(self._missing_pmids) - before_count
            
            if added > 0:
                logger.debug(f"📦 Buffer: added {added} missing PMIDs (total missing: {len(self._missing_pmids)})")
    
    def add_no_abstract_pmids(self, pmids: List[str]) -> None:
        """
        添加有返回但无摘要的 PMID（已在调用前过滤为近90天）
        
        Args:
            pmids: 近90天内无摘要的 PMID 列表
        """
        if not pmids:
            return
        
        with self._lock:
            before_count = len(self._no_abstract_pmids)
            self._no_abstract_pmids.update(pmids)
            added = len(self._no_abstract_pmids) - before_count
            
            if added > 0:
                logger.debug(f"📦 Buffer: added {added} no-abstract PMIDs (total: {len(self._no_abstract_pmids)})")
    
    def should_trigger(self, current_count: int) -> bool:
        """
        判断是否应该触发 PubMed 补充请求
        
        条件：
        1. 已筛选数量 >= 目标 * 90%
        2. 缓存中有 PMID
        3. 尚未触发过（避免重复触发）
        
        Args:
            current_count: 当前已筛选的文献数量
        
        Returns:
            是否应该触发
        """
        with self._lock:
            if self._triggered:
                return False
            
            has_pmids = len(self._missing_pmids) > 0 or len(self._no_abstract_pmids) > 0
            reached_threshold = current_count >= self.trigger_count
            
            if has_pmids and reached_threshold:
                # 直接计算 size，避免死锁（不调用 self.size property）
                buffer_size = len(self._missing_pmids) + len(self._no_abstract_pmids)
                logger.info(f"🎯 Trigger condition met: {current_count}/{self.threshold} "
                           f"(>= {self.trigger_count}), buffer has {buffer_size} PMIDs")
                return True
            
            return False
    
    def get_all_and_clear(self) -> List[str]:
        """
        获取所有缓存的 PMID 并清空缓存
        
        Returns:
            所有缓存的 PMID 列表（去重后）
        """
        with self._lock:
            all_pmids = list(self._missing_pmids | self._no_abstract_pmids)
            
            count_missing = len(self._missing_pmids)
            count_no_abstract = len(self._no_abstract_pmids)
            
            # 清空缓存
            self._missing_pmids.clear()
            self._no_abstract_pmids.clear()
            
            # 标记已触发
            self._triggered = True
            
            logger.info(f"📦 Buffer flushed: {len(all_pmids)} PMIDs "
                       f"(missing: {count_missing}, no-abstract: {count_no_abstract})")
            
            return all_pmids
    
    def force_flush(self) -> List[str]:
        """
        强制获取所有 PMID（工作流结束时调用）
        
        与 get_all_and_clear 相同，但不检查触发条件
        
        Returns:
            所有缓存的 PMID 列表
        """
        with self._lock:
            all_pmids = list(self._missing_pmids | self._no_abstract_pmids)
            
            if all_pmids:
                logger.info(f"📦 Force flush: {len(all_pmids)} PMIDs remaining in buffer")
            
            # 清空缓存
            self._missing_pmids.clear()
            self._no_abstract_pmids.clear()
            
            return all_pmids
    
    @property
    def size(self) -> int:
        """返回当前缓存的 PMID 总数"""
        with self._lock:
            return len(self._missing_pmids) + len(self._no_abstract_pmids)
    
    @property
    def missing_count(self) -> int:
        """返回缺失的 PMID 数量"""
        with self._lock:
            return len(self._missing_pmids)
    
    @property
    def no_abstract_count(self) -> int:
        """返回无摘要的 PMID 数量"""
        with self._lock:
            return len(self._no_abstract_pmids)
    
    @property
    def is_triggered(self) -> bool:
        """返回是否已触发过"""
        with self._lock:
            return self._triggered
    
    def reset_trigger(self) -> None:
        """重置触发状态（用于测试或特殊场景）"""
        with self._lock:
            self._triggered = False
            logger.debug("📦 Buffer trigger state reset")
    
    def get_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            包含详细统计的字典
        """
        with self._lock:
            return {
                "total": len(self._missing_pmids) + len(self._no_abstract_pmids),
                "missing": len(self._missing_pmids),
                "no_abstract": len(self._no_abstract_pmids),
                "threshold": self.threshold,
                "trigger_count": self.trigger_count,
                "triggered": self._triggered
            }
