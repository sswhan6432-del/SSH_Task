"""Priority queue for task routing with thread-safe heapq.

Max 100 items. Priority 1 = highest.
"""

import heapq
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

MAX_QUEUE_SIZE = 100


@dataclass(order=True)
class QueueItem:
    priority: int
    timestamp: float = field(compare=False, default_factory=time.time)
    task_id: str = field(compare=False, default="")
    payload: dict = field(compare=False, default_factory=dict)
    status: str = field(compare=False, default="pending")

    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "status": self.status,
            "payload_keys": list(self.payload.keys()),
        }


class QueueManager:
    """Thread-safe priority queue for routing tasks."""

    def __init__(self):
        self._heap: list[QueueItem] = []
        self._lock = threading.Lock()
        self._counter = 0
        self._processed = 0
        self._total_enqueued = 0

    def enqueue(self, payload: dict, priority: int = 5, task_id: str = "") -> Optional[QueueItem]:
        """Add item to queue. Returns None if queue full."""
        with self._lock:
            if len(self._heap) >= MAX_QUEUE_SIZE:
                return None
            self._counter += 1
            self._total_enqueued += 1
            if not task_id:
                task_id = f"task-{self._counter}"
            item = QueueItem(priority=priority, task_id=task_id, payload=payload)
            heapq.heappush(self._heap, item)
            return item

    def dequeue(self) -> Optional[QueueItem]:
        """Pop highest priority item (lowest number)."""
        with self._lock:
            if not self._heap:
                return None
            item = heapq.heappop(self._heap)
            item.status = "processing"
            self._processed += 1
            return item

    def peek(self) -> Optional[QueueItem]:
        """Look at next item without removing."""
        with self._lock:
            if not self._heap:
                return None
            return self._heap[0]

    def size(self) -> int:
        with self._lock:
            return len(self._heap)

    def status(self) -> dict:
        with self._lock:
            return {
                "queue_size": len(self._heap),
                "max_size": MAX_QUEUE_SIZE,
                "total_enqueued": self._total_enqueued,
                "total_processed": self._processed,
                "items": [item.to_dict() for item in sorted(self._heap)],
            }

    def clear(self):
        with self._lock:
            self._heap.clear()


# Singleton
queue_manager = QueueManager()
