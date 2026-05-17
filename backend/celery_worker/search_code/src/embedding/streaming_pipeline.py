"""Streaming embedding prefilter pipeline."""

from __future__ import annotations

import csv
import logging
import math
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from pathlib import Path

from .models import EmbeddingBatchResult, EmbeddingDecision
from .providers.base import EmbeddingProvider
from .similarity import cosine_similarity
from .text_builder import ArticleTextBuilder

logger = logging.getLogger(__name__)


class StreamingEmbeddingScreeningPipeline:
    """Run embedding batches and immediately pass relevant articles to LLM screening."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        threshold: float = 0.75,
        batch_size: int = 50,
        initial_concurrency: int = 4,
        max_concurrency: int = 8,
        ramp_delay_seconds: float = 3.0,
        backpressure_limit: int = 240,
        audit_path: str = "",
    ):
        self.embedding_provider = embedding_provider
        self.threshold = threshold
        self.batch_size = batch_size
        self.initial_concurrency = min(initial_concurrency, max_concurrency)
        self.max_concurrency = max_concurrency
        self.ramp_delay_seconds = ramp_delay_seconds
        self.backpressure_limit = backpressure_limit
        self.audit_path = audit_path
        self.last_stats: dict = {}

    def screen_articles(
        self,
        articles: list[dict],
        query_vector: list[float],
        llm_executor,
        user_query: str,
        ai_client,
        scoring_criteria: str,
        current_round: int,
        language_config: dict,
        controller,
    ) -> list[dict]:
        from ..ArticleScreener import create_screen_task

        if not articles:
            return []

        batches = [articles[start : start + self.batch_size] for start in range(0, len(articles), self.batch_size)]
        started = time.perf_counter()
        ramp_at = started + self.ramp_delay_seconds
        next_batch_index = 0
        embedding_futures = {}
        llm_futures = {}
        screened: list[dict] = []

        stats = {
            "before_embedding": len(articles),
            "valid_text": 0,
            "passed": 0,
            "filtered_out": 0,
            "errors": 0,
            "embedding_batches": len(batches),
            "embedding_batch_latencies": [],
        }

        def collect_completed_llm(block: bool = False) -> None:
            if not llm_futures:
                return
            if block:
                done, _ = wait(llm_futures, return_when=FIRST_COMPLETED)
            else:
                done = {future for future in llm_futures if future.done()}
            for future in done:
                pmid = llm_futures.pop(future)
                try:
                    result = future.result()
                    if result:
                        screened.append(result)
                except Exception as error:
                    logger.error(f"❌ Error screening PMID {pmid}: {error}")

        def submit_llm(article: dict) -> None:
            if controller and controller.should_stop():
                return
            pmid = article.get("pmid", article.get("PMID", "unknown"))
            future = llm_executor.submit(
                create_screen_task,
                article,
                user_query,
                ai_client,
                scoring_criteria,
                controller.get_count() if controller else 0,
                current_round,
                language_config,
                controller,
            )
            llm_futures[future] = pmid

        def current_embedding_limit() -> int:
            return self.max_concurrency if time.perf_counter() >= ramp_at else self.initial_concurrency

        def submit_embedding_batches() -> None:
            nonlocal next_batch_index
            if controller and controller.should_stop():
                return
            while (
                next_batch_index < len(batches)
                and len(embedding_futures) < current_embedding_limit()
                and len(llm_futures) < self.backpressure_limit
                and not (controller and controller.should_stop())
            ):
                batch = batches[next_batch_index]
                next_batch_index += 1
                future = embedding_executor.submit(self._embed_batch, batch, query_vector)
                embedding_futures[future] = (next_batch_index, batch)

        logger.info(
            "🧭 Embedding prefilter: %s articles, batch_size=%s, threshold=%.4f, concurrency=%s→%s",
            len(articles),
            self.batch_size,
            self.threshold,
            self.initial_concurrency,
            self.max_concurrency,
        )

        with ThreadPoolExecutor(max_workers=self.max_concurrency, thread_name_prefix="Embedding") as embedding_executor:
            submit_embedding_batches()

            while embedding_futures or next_batch_index < len(batches):
                collect_completed_llm(block=False)
                if controller and controller.should_stop():
                    break

                if len(llm_futures) >= self.backpressure_limit:
                    collect_completed_llm(block=True)
                    continue

                submit_embedding_batches()

                if not embedding_futures:
                    continue

                timeout = 0.25
                if time.perf_counter() < ramp_at and next_batch_index < len(batches):
                    timeout = max(0.05, min(0.25, ramp_at - time.perf_counter()))

                done, _ = wait(embedding_futures, timeout=timeout, return_when=FIRST_COMPLETED)
                if not done:
                    continue

                for future in done:
                    batch_number, batch_articles = embedding_futures.pop(future)
                    try:
                        result = future.result()
                    except Exception as error:
                        message = str(error)[:500]
                        result = EmbeddingBatchResult(
                            [
                                EmbeddingDecision(
                                    article,
                                    str(article.get("pmid", article.get("PMID", ""))),
                                    ArticleTextBuilder.build(article),
                                    None,
                                    False,
                                    message,
                                )
                                for article in batch_articles
                            ],
                            0.0,
                            message,
                        )
                    stats["embedding_batch_latencies"].append(result.elapsed_seconds)
                    self._record_decisions(current_round, batch_number, result.decisions)

                    if result.error:
                        logger.warning(f"⚠️ Embedding batch {batch_number} failed: {result.error}")

                    passed_count = 0
                    for decision in result.decisions:
                        if decision.text:
                            stats["valid_text"] += 1
                        if decision.error:
                            stats["errors"] += 1
                        if decision.error and decision.text:
                            submit_llm(decision.article)
                        elif decision.passed:
                            passed_count += 1
                            stats["passed"] += 1
                            submit_llm(decision.article)
                        else:
                            stats["filtered_out"] += 1

                    logger.info(
                        "🧭 Embedding batch %s/%s: passed %s/%s, LLM pending=%s",
                        batch_number,
                        len(batches),
                        passed_count,
                        len(result.decisions),
                        len(llm_futures),
                    )

                    if controller and controller.should_stop():
                        break

            for future in embedding_futures:
                future.cancel()

        for future in as_completed(llm_futures):
            pmid = llm_futures[future]
            try:
                result = future.result()
                if result:
                    screened.append(result)
            except Exception as error:
                logger.error(f"❌ Error screening PMID {pmid}: {error}")

        stats["elapsed_seconds"] = time.perf_counter() - started
        stats["llm_screened_results"] = len(screened)
        self.last_stats = stats
        logger.info(
            "🧭 Embedding prefilter complete: %s → %s passed, %s LLM results, %.2fs",
            stats["before_embedding"],
            stats["passed"],
            len(screened),
            stats["elapsed_seconds"],
        )
        return screened

    def _embed_batch(self, articles: list[dict], query_vector: list[float]) -> EmbeddingBatchResult:
        started = time.perf_counter()
        decisions: list[EmbeddingDecision] = []
        valid_articles: list[dict] = []
        texts: list[str] = []

        for article in articles:
            pmid = str(article.get("pmid", article.get("PMID", "")))
            text = ArticleTextBuilder.build(article)
            if not text:
                decisions.append(EmbeddingDecision(article, pmid, "", None, False, "metadata text is empty"))
            else:
                valid_articles.append(article)
                texts.append(text)

        if not texts:
            return EmbeddingBatchResult(decisions, time.perf_counter() - started)

        try:
            vectors = self.embedding_provider.embed_documents(texts)
            if len(vectors) != len(texts):
                raise RuntimeError(f"Expected {len(texts)} vectors, got {len(vectors)}")
            for article, text, vector in zip(valid_articles, texts, vectors):
                pmid = str(article.get("pmid", article.get("PMID", "")))
                similarity = cosine_similarity(query_vector, vector)
                passed = not math.isnan(similarity) and similarity >= self.threshold
                decisions.append(EmbeddingDecision(article, pmid, text, similarity, passed))
        except Exception as error:
            message = str(error)[:500]
            for article, text in zip(valid_articles, texts):
                pmid = str(article.get("pmid", article.get("PMID", "")))
                decisions.append(EmbeddingDecision(article, pmid, text, None, False, message))
            return EmbeddingBatchResult(decisions, time.perf_counter() - started, message)

        return EmbeddingBatchResult(decisions, time.perf_counter() - started)

    def _record_decisions(self, round_number: int, batch_number: int, decisions: list[EmbeddingDecision]) -> None:
        if not self.audit_path:
            return
        path = Path(self.audit_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        exists = path.exists()
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["round", "batch", "pmid", "similarity", "passed", "error"],
            )
            if not exists:
                writer.writeheader()
            for decision in decisions:
                writer.writerow(
                    {
                        "round": round_number,
                        "batch": batch_number,
                        "pmid": decision.pmid,
                        "similarity": "" if decision.similarity is None else f"{decision.similarity:.10f}",
                        "passed": "1" if decision.passed else "0",
                        "error": decision.error,
                    }
                )
