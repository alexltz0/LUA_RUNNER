"""
Event Bus — high-performance pub/sub system for game events.
Supports priorities, one-shot listeners, and wildcard patterns.
"""

from __future__ import annotations

import time
import fnmatch
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict


@dataclass(order=True)
class EventListener:
    priority: int
    callback: Any = field(compare=False)
    once: bool = field(default=False, compare=False)
    listener_id: str = field(default="", compare=False)


@dataclass
class EventRecord:
    name: str
    data: Dict[str, Any]
    timestamp: float
    propagation_stopped: bool = False


class EventBus:
    """
    Low-latency event bus with:
    - Priority-based dispatch
    - Wildcard pattern matching (e.g. "entity.*")
    - One-shot listeners
    - Event history for debugging
    - Propagation control
    """

    def __init__(self, history_size: int = 100):
        self._listeners: Dict[str, List[EventListener]] = defaultdict(list)
        self._history: List[EventRecord] = []
        self._history_size = history_size
        self._listener_counter = 0
        self._stats: Dict[str, int] = defaultdict(int)

    def on(
        self,
        event: str,
        callback: Callable,
        priority: int = 0,
        once: bool = False,
    ) -> str:
        """Register a listener. Returns listener_id for removal."""
        self._listener_counter += 1
        lid = f"listener_{self._listener_counter}"
        listener = EventListener(
            priority=priority,
            callback=callback,
            once=once,
            listener_id=lid,
        )
        self._listeners[event].append(listener)
        self._listeners[event].sort()
        return lid

    def once(self, event: str, callback: Callable, priority: int = 0) -> str:
        """Register a one-shot listener."""
        return self.on(event, callback, priority=priority, once=True)

    def off(self, event: str, listener_id: str) -> bool:
        """Remove a specific listener."""
        listeners = self._listeners.get(event, [])
        for i, l in enumerate(listeners):
            if l.listener_id == listener_id:
                listeners.pop(i)
                return True
        return False

    def off_all(self, event: Optional[str] = None) -> None:
        """Remove all listeners for an event, or all listeners."""
        if event:
            self._listeners.pop(event, None)
        else:
            self._listeners.clear()

    def emit(self, event: str, data: Optional[Dict[str, Any]] = None) -> EventRecord:
        """
        Emit an event. Dispatches to exact matches and wildcard patterns.
        Returns the EventRecord for inspection.
        """
        data = data or {}
        record = EventRecord(name=event, data=data, timestamp=time.perf_counter())
        self._stats[event] += 1

        # Collect matching listeners (exact + wildcard)
        matching: List[EventListener] = []
        for pattern, listeners in self._listeners.items():
            if pattern == event or fnmatch.fnmatch(event, pattern):
                matching.extend(listeners)

        matching.sort()

        to_remove: List[tuple] = []
        for listener in matching:
            if record.propagation_stopped:
                break
            try:
                listener.callback(record)
            except Exception as e:
                # Log but don't crash the event loop
                print(f"[EventBus] Error in listener for '{event}': {e}")
            if listener.once:
                for pattern, listeners in self._listeners.items():
                    if listener in listeners:
                        to_remove.append((pattern, listener))

        for pattern, listener in to_remove:
            self._listeners[pattern].remove(listener)

        # History
        self._history.append(record)
        if len(self._history) > self._history_size:
            self._history.pop(0)

        return record

    def stop_propagation(self, record: EventRecord) -> None:
        """Stop event propagation for a given record."""
        record.propagation_stopped = True

    @property
    def history(self) -> List[EventRecord]:
        return list(self._history)

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    def listener_count(self, event: Optional[str] = None) -> int:
        if event:
            return len(self._listeners.get(event, []))
        return sum(len(v) for v in self._listeners.values())
