"""
Tick Scheduler — Fixed-timestep game loop with configurable tick rate.
Drives the event-driven Lua execution model.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ScheduledTask:
    name: str
    callback: Callable
    interval_ticks: int
    remaining: int
    repeat: bool = True
    active: bool = True


class TickScheduler:
    """
    Fixed-timestep scheduler for game loop simulation.

    Features:
    - Configurable tick rate (default 60 TPS)
    - Delta time tracking
    - Scheduled tasks with tick intervals
    - Performance metrics (avg tick time, frame budget usage)
    """

    def __init__(self, tick_rate: int = 60):
        self._tick_rate = tick_rate
        self._tick_interval = 1.0 / tick_rate
        self._tick_count = 0
        self._running = False
        self._tasks: Dict[str, ScheduledTask] = {}
        self._on_tick: Optional[Callable] = None
        self._tick_times: List[float] = []
        self._max_tick_samples = 120

    @property
    def tick_rate(self) -> int:
        return self._tick_rate

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def tick_interval(self) -> float:
        return self._tick_interval

    @property
    def avg_tick_time_ms(self) -> float:
        if not self._tick_times:
            return 0.0
        return (sum(self._tick_times) / len(self._tick_times)) * 1000

    @property
    def frame_budget_usage(self) -> float:
        """Percentage of frame budget used (100% = at limit)."""
        if not self._tick_times:
            return 0.0
        avg = sum(self._tick_times) / len(self._tick_times)
        return (avg / self._tick_interval) * 100

    def on_tick(self, callback: Callable) -> None:
        """Set the main tick callback. Called every tick with (tick_count, delta_time)."""
        self._on_tick = callback

    def schedule(
        self,
        name: str,
        callback: Callable,
        interval_ticks: int = 1,
        repeat: bool = True,
    ) -> None:
        """Schedule a task to run every N ticks."""
        self._tasks[name] = ScheduledTask(
            name=name,
            callback=callback,
            interval_ticks=interval_ticks,
            remaining=interval_ticks,
            repeat=repeat,
        )

    def unschedule(self, name: str) -> bool:
        """Remove a scheduled task."""
        return self._tasks.pop(name, None) is not None

    def run(self, max_ticks: Optional[int] = None) -> None:
        """
        Run the scheduler loop.
        If max_ticks is set, stops after that many ticks (useful for testing/demos).
        """
        self._running = True
        self._tick_count = 0

        while self._running:
            tick_start = time.perf_counter()

            # Main tick callback
            dt = self._tick_interval
            if self._on_tick:
                self._on_tick(self._tick_count, dt)

            # Scheduled tasks
            to_remove = []
            for name, task in self._tasks.items():
                if not task.active:
                    continue
                task.remaining -= 1
                if task.remaining <= 0:
                    try:
                        task.callback(self._tick_count, dt)
                    except Exception as e:
                        print(f"[Scheduler] Error in task '{name}': {e}")
                    if task.repeat:
                        task.remaining = task.interval_ticks
                    else:
                        to_remove.append(name)

            for name in to_remove:
                del self._tasks[name]

            self._tick_count += 1

            # Max ticks limit
            if max_ticks is not None and self._tick_count >= max_ticks:
                self._running = False
                break

            # Timing
            tick_elapsed = time.perf_counter() - tick_start
            self._tick_times.append(tick_elapsed)
            if len(self._tick_times) > self._max_tick_samples:
                self._tick_times.pop(0)

            # Sleep for remaining frame budget
            sleep_time = self._tick_interval - tick_elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False

    def get_metrics(self) -> Dict:
        return {
            "tick_count": self._tick_count,
            "tick_rate": self._tick_rate,
            "avg_tick_time_ms": round(self.avg_tick_time_ms, 3),
            "frame_budget_usage_pct": round(self.frame_budget_usage, 1),
            "active_tasks": len([t for t in self._tasks.values() if t.active]),
        }
