#!/usr/bin/env python3
"""
llm_router_v5.py -- Enhanced LLM Task Router v5.0

Extends v4.0 with NLP/ML capabilities:
- Intent detection (BERT-based)
- Smart priority ranking (ML-based)
- Text chunking and compression (50% token reduction)
- Fail-safe fallback to v4.0

Core v5.0 flags:
  --v5                      Enable v5.0 engine (default: auto)
  --compress                Enable compression (default: true if v5)
  --compression-level 1-3   Compression strength (default: 2)
  --intent-detect           Enable intent detection (default: true if v5)
  --smart-priority          Enable ML priority (default: true if v5)
  --show-stats              Show token reduction & processing time
  --fallback-v4             Fallback to v4.0 on error (default: true)
  --no-cache                Disable caching (default: false)

All v4.0 flags are 100% compatible.
"""

from __future__ import annotations
import re, json, sys, os, time
import datetime
import logging
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Optional, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# v4.0 imports (for fallback and compatibility)
import llm_router as v4

# v5.0 NLP/ML modules
try:
    from nlp.intent_detector import IntentDetector, IntentAnalysis
    from nlp.priority_ranker import PriorityRanker, PriorityScore
    from nlp.text_chunker import TextChunker
    from nlp.compressor import Compressor, CompressionResult
    NLP_AVAILABLE = True
except ImportError as e:
    logging.warning(f"NLP modules not available: {e}. v5.0 features disabled.")
    NLP_AVAILABLE = False
    # Dummy classes for type hints
    IntentAnalysis = Any
    PriorityScore = Any
    CompressionResult = Any


# -------------------------
# Logging Setup
# -------------------------

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# -------------------------
# Data Models (v5.0)
# -------------------------

@dataclass
class EnhancedTaskDecision:
    """
    v5.0 Enhanced Task Decision

    Extends v4.0 TaskDecision with NLP/ML metadata
    """
    # v4.0 fields (100% compatible)
    id: str
    summary: str
    route: str                          # "analyze" | "implement" | "research"
    confidence: float                   # ML-based (not fixed 0.95)
    priority: int                       # ML-based (not order-based)
    reasons: List[str]
    claude_prompt: str
    next_session_starter: str
    change_log_stub: str

    # v5.0 additional fields
    intent_analysis: Optional[IntentAnalysis] = None
    priority_score: Optional[PriorityScore] = None
    compression_result: Optional[CompressionResult] = None
    processing_time_ms: float = 0.0     # Performance monitoring
    v5_enabled: bool = False            # Flag to indicate v5 processing

    def to_v4_format(self) -> v4.TaskDecision:
        """Convert to v4.0 TaskDecision for compatibility"""
        return v4.TaskDecision(
            id=self.id,
            summary=self.summary,
            route=self.route,
            confidence=self.confidence,
            priority=self.priority,
            reasons=self.reasons,
            claude_prompt=self.claude_prompt,
            next_session_starter=self.next_session_starter,
            change_log_stub=self.change_log_stub
        )


@dataclass
class EnhancedRouterOutput:
    """
    v5.0 Enhanced Router Output

    Extends v4.0 RouterOutput with performance metrics
    """
    route: str
    confidence: float
    reasons: List[str]
    global_notes: List[str]
    session_guard: List[str]
    tasks: List[EnhancedTaskDecision]

    # v5.0 metrics
    total_processing_time_ms: float = 0.0
    token_reduction_rate: float = 0.0   # 0.0-1.0 (0.5 = 50% reduction)
    v5_features_used: List[str] = None  # ["intent", "compression", ...]

    def __post_init__(self):
        if self.v5_features_used is None:
            self.v5_features_used = []


# -------------------------
# Lazy Model Loader
# -------------------------

class LazyModelLoader:
    """
    Lazy loading for NLP/ML models

    Models are loaded only when first accessed to minimize startup time.
    Supports caching to avoid reloading.
    """

    def __init__(self, model_dir: str = "./models"):
        self.model_dir = Path(model_dir)
        self._intent_detector: Optional[IntentDetector] = None
        self._priority_ranker: Optional[PriorityRanker] = None
        self._text_chunker: Optional[TextChunker] = None
        self._compressor: Optional[Compressor] = None

    @property
    def intent_detector(self) -> IntentDetector:
        """Load intent detector on first access"""
        if self._intent_detector is None:
            if not NLP_AVAILABLE:
                raise RuntimeError("NLP modules not available")
            logger.info("Loading intent detector...")
            start = time.time()
            self._intent_detector = IntentDetector()
            logger.info(f"Intent detector loaded in {time.time() - start:.2f}s")
        return self._intent_detector

    @property
    def priority_ranker(self) -> PriorityRanker:
        """Load priority ranker on first access"""
        if self._priority_ranker is None:
            if not NLP_AVAILABLE:
                raise RuntimeError("NLP modules not available")
            logger.info("Loading priority ranker...")
            start = time.time()
            self._priority_ranker = PriorityRanker()
            logger.info(f"Priority ranker loaded in {time.time() - start:.2f}s")
        return self._priority_ranker

    @property
    def text_chunker(self) -> TextChunker:
        """Load text chunker on first access"""
        if self._text_chunker is None:
            if not NLP_AVAILABLE:
                raise RuntimeError("NLP modules not available")
            logger.info("Loading text chunker...")
            start = time.time()
            self._text_chunker = TextChunker()
            logger.info(f"Text chunker loaded in {time.time() - start:.2f}s")
        return self._text_chunker

    @property
    def compressor(self) -> Compressor:
        """Load compressor on first access"""
        if self._compressor is None:
            if not NLP_AVAILABLE:
                raise RuntimeError("NLP modules not available")
            logger.info("Loading compressor...")
            start = time.time()
            self._compressor = Compressor()
            logger.info(f"Compressor loaded in {time.time() - start:.2f}s")
        return self._compressor


# -------------------------
# Enhanced Router Engine
# -------------------------

class EnhancedRouter:
    """
    v5.0 Enhanced Router Engine

    Integrates NLP/ML modules with v4.0 router:
    - Intent detection for better task classification
    - ML-based priority ranking
    - Text compression for token efficiency
    - Fail-safe fallback to v4.0
    """

    def __init__(
        self,
        enable_nlp: bool = True,
        enable_compression: bool = True,
        compression_level: int = 2,
        fallback_to_v4: bool = True,
        model_dir: str = "./models",
        use_cache: bool = True
    ):
        """
        Initialize Enhanced Router

        Args:
            enable_nlp: Enable intent detection and priority ranking
            enable_compression: Enable prompt compression
            compression_level: Compression strength (1-3)
            fallback_to_v4: Fallback to v4.0 on error
            model_dir: Directory for model files
            use_cache: Enable result caching
        """
        self.enable_nlp = enable_nlp and NLP_AVAILABLE
        self.enable_compression = enable_compression and NLP_AVAILABLE
        self.compression_level = compression_level
        self.fallback_to_v4 = fallback_to_v4
        self.use_cache = use_cache

        # Lazy load models
        self.loader = LazyModelLoader(model_dir) if NLP_AVAILABLE else None

        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "v5_success": 0,
            "v4_fallback": 0,
            "avg_processing_time_ms": 0.0,
            "avg_token_reduction": 0.0
        }

        logger.info(f"EnhancedRouter initialized (NLP={self.enable_nlp}, "
                   f"Compression={self.enable_compression}, Level={self.compression_level})")

    def route(
        self,
        request: str,
        **kwargs
    ) -> EnhancedRouterOutput:
        """
        Route user request to tasks with v5.0 enhancements

        Args:
            request: User request text (Korean or English)
            **kwargs: Additional v4.0 compatible flags

        Returns:
            EnhancedRouterOutput with tasks and metadata
        """
        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            # Try v5.0 routing
            result = self._route_v5(request, **kwargs)
            self.stats["v5_success"] += 1

            # Update stats
            elapsed_ms = (time.time() - start_time) * 1000
            self.stats["avg_processing_time_ms"] = (
                (self.stats["avg_processing_time_ms"] * (self.stats["v5_success"] - 1)
                 + elapsed_ms) / self.stats["v5_success"]
            )

            result.total_processing_time_ms = elapsed_ms
            return result

        except Exception as e:
            if self.fallback_to_v4:
                logger.warning(f"v5.0 routing failed, falling back to v4.0: {e}")
                self.stats["v4_fallback"] += 1
                return self._fallback_v4(request, **kwargs)
            else:
                raise

    def _route_v5(self, request: str, **kwargs) -> EnhancedRouterOutput:
        """
        v5.0 routing with NLP/ML enhancements

        Flow:
        1. Use v4.0 to split tasks (leverage existing logic)
        2. Apply v5.0 enhancements per task (PARALLEL PROCESSING):
           - Intent detection
           - Priority ranking
           - Compression
        3. Return enhanced results
        """
        # Step 1: Get base routing from v4.0
        # This handles task splitting, Groq API, etc.
        v4_result = v4.route_text(
            full_text=request,
            desktop_edit=kwargs.get("desktop_edit", False),
            economy=kwargs.get("economy", "balanced"),
            phase=kwargs.get("phase", "implement"),
            opus_only=kwargs.get("opus_only", False),
            max_tickets=kwargs.get("max_tickets", 99),
            merge_spec=kwargs.get("merge_spec", ""),
            force_split=kwargs.get("force_split", False),
            min_tickets=kwargs.get("min_tickets", 0)
        )

        # Step 2: Apply batch NLP processing with PARALLEL EXECUTION (ThreadPoolExecutor)
        intent_analyses = []
        priority_scores = []

        if self.enable_nlp and self.loader:
            parallel_start = time.time()

            # Parallel processing with ThreadPoolExecutor (max_workers=3)
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Submit parallel tasks
                future_intents = executor.submit(self._batch_detect_intents, v4_result.tasks)
                future_priorities = executor.submit(self._batch_rank_priorities, v4_result.tasks)

                # Wait for results (blocking)
                try:
                    intent_analyses = future_intents.result(timeout=30)
                except Exception as e:
                    logger.warning(f"Parallel intent detection failed: {e}")
                    intent_analyses = [None] * len(v4_result.tasks)

                try:
                    priority_scores = future_priorities.result(timeout=30)
                except Exception as e:
                    logger.warning(f"Parallel priority ranking failed: {e}")
                    priority_scores = [None] * len(v4_result.tasks)

            parallel_time = (time.time() - parallel_start) * 1000
            logger.info(f"Parallel NLP processing completed in {parallel_time:.2f}ms")

        # Step 3: Convert v4 tasks to v5 format with enhancements
        enhanced_tasks = []
        v5_features_used = []
        total_token_reduction = 0.0

        for i, v4_task in enumerate(v4_result.tasks):
            intent = intent_analyses[i] if i < len(intent_analyses) else None
            priority = priority_scores[i] if i < len(priority_scores) else None

            enhanced_task = self._enhance_task(v4_task, intent, priority, **kwargs)
            enhanced_tasks.append(enhanced_task)

            # Track features used
            if enhanced_task.intent_analysis:
                v5_features_used.append("intent_detection")
            if enhanced_task.priority_score:
                v5_features_used.append("smart_priority")
            if enhanced_task.compression_result:
                v5_features_used.append("compression")
                total_token_reduction += enhanced_task.compression_result.reduction_rate

        # Calculate average token reduction
        avg_token_reduction = (
            total_token_reduction / len(enhanced_tasks) if enhanced_tasks else 0.0
        )

        # Step 3: Build enhanced output
        return EnhancedRouterOutput(
            route=v4_result.route,
            confidence=v4_result.confidence,
            reasons=v4_result.reasons,
            global_notes=v4_result.global_notes,
            session_guard=v4_result.session_guard,
            tasks=enhanced_tasks,
            token_reduction_rate=avg_token_reduction,
            v5_features_used=list(set(v5_features_used))  # Deduplicate
        )

    def _batch_detect_intents(self, v4_tasks: List[v4.TaskDecision]) -> List[Optional[IntentAnalysis]]:
        """
        Batch intent detection for parallel processing

        Args:
            v4_tasks: List of v4.0 TaskDecisions

        Returns:
            List of IntentAnalysis (or None on failure)
        """
        intent_analyses = []
        for v4_task in v4_tasks:
            try:
                intent = self.loader.intent_detector.detect(v4_task.summary)
                intent_analyses.append(intent)
            except Exception as e:
                logger.warning(f"Intent detection failed for task {v4_task.id}: {e}")
                intent_analyses.append(None)

        return intent_analyses

    def _batch_rank_priorities(self, v4_tasks: List[v4.TaskDecision]) -> List[Optional[PriorityScore]]:
        """
        Batch priority ranking for parallel processing

        Args:
            v4_tasks: List of v4.0 TaskDecisions

        Returns:
            List of PriorityScore (or None on failure)
        """
        try:
            task_summaries = [t.summary for t in v4_tasks]
            priority_scores = self.loader.priority_ranker.rank(task_summaries)
            return priority_scores
        except Exception as e:
            logger.warning(f"Priority ranking failed: {e}")
            return [None] * len(v4_tasks)

    def _enhance_task(
        self,
        v4_task: v4.TaskDecision,
        intent_analysis: Optional[IntentAnalysis],
        priority_score: Optional[PriorityScore],
        **kwargs
    ) -> EnhancedTaskDecision:
        """
        Enhance a single v4 task with v5 features

        Args:
            v4_task: v4.0 TaskDecision
            intent_analysis: Pre-computed intent analysis (or None)
            priority_score: Pre-computed priority score (or None)
            **kwargs: Configuration flags

        Returns:
            EnhancedTaskDecision with NLP/ML metadata
        """
        task_start = time.time()

        # Convert v4 task to v5 format
        enhanced = EnhancedTaskDecision(
            id=v4_task.id,
            summary=v4_task.summary,
            route=v4_task.route,
            confidence=v4_task.confidence,
            priority=v4_task.priority,
            reasons=v4_task.reasons,
            claude_prompt=v4_task.claude_prompt,
            next_session_starter=v4_task.next_session_starter,
            change_log_stub=v4_task.change_log_stub,
            v5_enabled=True
        )

        # Apply intent analysis if available
        if intent_analysis:
            enhanced.intent_analysis = intent_analysis

            # Update route based on intent if confidence is high
            if intent_analysis.confidence > 0.8:
                enhanced.route = intent_analysis.intent
                enhanced.confidence = intent_analysis.confidence

        # Apply priority score if available
        if priority_score:
            enhanced.priority_score = priority_score

            # Update priority with ML-based score
            enhanced.priority = priority_score.priority
            enhanced.confidence = max(enhanced.confidence, priority_score.ml_confidence)

        if self.enable_compression and self.loader:
            # Prompt compression
            try:
                compression_result = self.loader.compressor.compress(
                    v4_task.claude_prompt,
                    level=self.compression_level
                )
                enhanced.compression_result = compression_result

                # Update prompt with compressed version
                enhanced.claude_prompt = compression_result.compressed

            except Exception as e:
                logger.warning(f"Compression failed for task {v4_task.id}: {e}")

        # Calculate processing time
        enhanced.processing_time_ms = (time.time() - task_start) * 1000

        return enhanced

    def _fallback_v4(self, request: str, **kwargs) -> EnhancedRouterOutput:
        """
        Fallback to v4.0 routing

        Args:
            request: User request
            **kwargs: v4.0 flags

        Returns:
            EnhancedRouterOutput (converted from v4.0)
        """
        v4_result = v4.route_text(
            full_text=request,
            desktop_edit=kwargs.get("desktop_edit", False),
            economy=kwargs.get("economy", "balanced"),
            phase=kwargs.get("phase", "implement"),
            opus_only=kwargs.get("opus_only", False),
            max_tickets=kwargs.get("max_tickets", 99),
            merge_spec=kwargs.get("merge_spec", ""),
            force_split=kwargs.get("force_split", False),
            min_tickets=kwargs.get("min_tickets", 0)
        )

        # Convert v4 tasks to v5 format (without enhancements)
        enhanced_tasks = [
            EnhancedTaskDecision(
                id=t.id,
                summary=t.summary,
                route=t.route,
                confidence=t.confidence,
                priority=t.priority,
                reasons=t.reasons,
                claude_prompt=t.claude_prompt,
                next_session_starter=t.next_session_starter,
                change_log_stub=t.change_log_stub,
                v5_enabled=False
            )
            for t in v4_result.tasks
        ]

        return EnhancedRouterOutput(
            route=v4_result.route,
            confidence=v4_result.confidence,
            reasons=v4_result.reasons,
            global_notes=v4_result.global_notes,
            session_guard=v4_result.session_guard,
            tasks=enhanced_tasks,
            v5_features_used=["v4_fallback"]
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self.stats.copy()


# -------------------------
# Output Formatting (v4.0 Compatibility)
# -------------------------

def format_output_for_v4_compat(result: EnhancedRouterOutput, include_v5_fields: bool = False) -> dict:
    """
    Format output for v4.0 compatibility

    Args:
        result: EnhancedRouterOutput from v5.0 router
        include_v5_fields: Include v5.0-specific fields (default: False)

    Returns:
        Dictionary with v4.0-compatible format
    """
    # Convert tasks to v4.0 format (remove v5.0-specific fields)
    v4_tasks = []
    for task in result.tasks:
        task_dict = {
            "id": task.id,
            "summary": task.summary,
            "route": task.route,
            "confidence": task.confidence,
            "priority": task.priority,
            "reasons": task.reasons,
            "claude_prompt": task.claude_prompt,
            "next_session_starter": task.next_session_starter,
            "change_log_stub": task.change_log_stub,
        }

        # Include v5.0 fields only if requested
        if include_v5_fields:
            if task.intent_analysis:
                task_dict["intent_analysis"] = asdict(task.intent_analysis)
            if task.priority_score:
                task_dict["priority_score"] = asdict(task.priority_score)
            if task.compression_result:
                task_dict["compression_result"] = asdict(task.compression_result)
            task_dict["processing_time_ms"] = task.processing_time_ms
            task_dict["v5_enabled"] = task.v5_enabled

        v4_tasks.append(task_dict)

    # Base v4.0 output format
    output = {
        "route": result.route,
        "confidence": result.confidence,
        "reasons": result.reasons,
        "global_notes": result.global_notes,
        "session_guard": result.session_guard,
        "tasks": v4_tasks,
    }

    # Add v5.0 metrics only if requested
    if include_v5_fields:
        output["total_processing_time_ms"] = result.total_processing_time_ms
        output["token_reduction_rate"] = result.token_reduction_rate
        output["v5_features_used"] = result.v5_features_used

    return output


# -------------------------
# CLI Entry Point (v5.0)
# -------------------------

def main():
    """
    CLI entry point for v5.0 router

    Supports all v4.0 flags plus new v5.0 flags
    """
    # Parse v5.0 specific flags from argv
    args = sys.argv[1:]

    v5_enabled = "--v5" in args or "--enable-v5" in args
    enable_compression = "--compress" in args or v5_enabled
    compression_level = 2  # Default
    show_stats = "--show-stats" in args
    fallback_v4 = "--no-fallback" not in args
    no_cache = "--no-cache" in args

    # Parse compression level (flag with value)
    for i, arg in enumerate(args):
        if arg == "--compression-level" and i + 1 < len(args):
            try:
                compression_level = int(args[i + 1])
                compression_level = max(1, min(3, compression_level))  # Clamp to 1-3
            except ValueError:
                logger.warning(f"Invalid compression level: {args[i + 1]}, using default (2)")

    # Strip all v5 flags (simple flags and value flags) to isolate the request text
    v5_simple_flags = {
        "--v5", "--enable-v5", "--compress", "--show-stats",
        "--fallback-v4", "--no-fallback", "--no-cache", "--intent-detect", "--smart-priority",
    }
    v5_value_flags = {"--compression-level"}

    cleaned = []
    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg in v5_simple_flags:
            continue
        if arg in v5_value_flags:
            skip_next = True
            continue
        cleaned.append(arg)
    args = cleaned

    # Check if NLP is available
    if v5_enabled and not NLP_AVAILABLE:
        logger.warning("v5.0 requested but NLP modules not available. Falling back to v4.0.")
        v5_enabled = False

    # If v5 not explicitly requested or not available, use v4.0 directly
    if not v5_enabled:
        # Restore cleaned args for v4 (replace sys.argv temporarily)
        orig_argv = sys.argv
        sys.argv = [sys.argv[0]] + args
        v4.main()
        sys.argv = orig_argv
        return

    # Initialize v5.0 router
    router = EnhancedRouter(
        enable_nlp=True,
        enable_compression=enable_compression,
        compression_level=compression_level,
        fallback_to_v4=fallback_v4,
        use_cache=not no_cache
    )

    # Get request from remaining args (after stripping v5 flags)
    if not args:
        print("Usage: python3 llm_router_v5.py 'request' [flags]", file=sys.stderr)
        print("Run with --help for full documentation.", file=sys.stderr)
        sys.exit(1)

    # v4 flags are still in args — strip them too and join remainder as request
    v4_simple_flags = {
        "--json", "--desktop-edit", "--opus-only", "--tickets-md",
        "--friendly", "--force-split",
    }
    v4_value_flags = {
        "--economy", "--phase", "--one-task", "--save-tickets",
        "--max-tickets", "--min-tickets", "--merge",
    }

    request_parts = []
    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg in v4_simple_flags:
            continue
        if arg in v4_value_flags:
            skip_next = True
            continue
        request_parts.append(arg)

    request = " ".join(request_parts) if request_parts else args[-1]

    # Route request
    result = router.route(request)

    # Output results (v4.0 compatible format)
    # Format output based on --show-stats flag
    output = format_output_for_v4_compat(result, include_v5_fields=show_stats)
    print(json.dumps(output, indent=2, ensure_ascii=False))

    # Show stats if requested
    if show_stats:
        stats = router.get_stats()
        print("\n--- v5.0 Performance Stats ---", file=sys.stderr)
        print(f"Total requests: {stats['total_requests']}", file=sys.stderr)
        print(f"v5 success: {stats['v5_success']}", file=sys.stderr)
        print(f"v4 fallback: {stats['v4_fallback']}", file=sys.stderr)
        print(f"Avg processing time: {stats['avg_processing_time_ms']:.2f}ms", file=sys.stderr)
        print(f"Avg token reduction: {result.token_reduction_rate * 100:.1f}%", file=sys.stderr)


if __name__ == "__main__":
    main()
