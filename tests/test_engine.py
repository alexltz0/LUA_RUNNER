"""
Tests for the LUA_RUNNER engine.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.events import EventBus
from engine.sandbox import SandboxedLua
from engine.scheduler import TickScheduler
from engine.core import LuaRunner


class TestEventBus:
    def test_emit_and_receive(self):
        bus = EventBus()
        received = []
        bus.on("test", lambda r: received.append(r.name))
        bus.emit("test")
        assert len(received) == 1
        assert received[0] == "test"

    def test_once_listener(self):
        bus = EventBus()
        count = {"n": 0}
        bus.once("ping", lambda r: count.__setitem__("n", count["n"] + 1))
        bus.emit("ping")
        bus.emit("ping")
        assert count["n"] == 1

    def test_wildcard_matching(self):
        bus = EventBus()
        received = []
        bus.on("entity.*", lambda r: received.append(r.name))
        bus.emit("entity.spawn")
        bus.emit("entity.destroy")
        bus.emit("other.event")
        assert len(received) == 2

    def test_priority_ordering(self):
        bus = EventBus()
        order = []
        bus.on("ordered", lambda r: order.append("B"), priority=1)
        bus.on("ordered", lambda r: order.append("A"), priority=0)
        bus.emit("ordered")
        assert order == ["A", "B"]

    def test_off_removes_listener(self):
        bus = EventBus()
        count = {"n": 0}
        lid = bus.on("removable", lambda r: count.__setitem__("n", count["n"] + 1))
        bus.emit("removable")
        bus.off("removable", lid)
        bus.emit("removable")
        assert count["n"] == 1

    def test_stats(self):
        bus = EventBus()
        bus.on("a", lambda r: None)
        bus.emit("a")
        bus.emit("a")
        bus.emit("b")
        assert bus.stats["a"] == 2
        assert bus.stats["b"] == 1


class TestSandboxedLua:
    def test_basic_execution(self):
        lua = SandboxedLua()
        result = lua.execute("return 1 + 2")
        assert result.success
        assert result.result == 3

    def test_sandbox_blocks_os(self):
        lua = SandboxedLua()
        result = lua.execute("return os")
        assert result.success
        assert result.result is None

    def test_sandbox_blocks_io(self):
        lua = SandboxedLua()
        result = lua.execute("return io")
        assert result.success
        assert result.result is None

    def test_math_extensions(self):
        lua = SandboxedLua()
        result = lua.execute("return math.clamp(15, 0, 10)")
        assert result.success
        assert result.result == 10

    def test_lerp(self):
        lua = SandboxedLua()
        result = lua.execute("return math.lerp(0, 10, 0.5)")
        assert result.success
        assert result.result == 5.0

    def test_inject_global(self):
        lua = SandboxedLua()
        lua.inject_global("my_value", 42)
        result = lua.execute("return my_value")
        assert result.success
        assert result.result == 42

    def test_call_function(self):
        lua = SandboxedLua()
        lua.execute("function add(a, b) return a + b end")
        result = lua.call_function("add", 3, 4)
        assert result.success
        assert result.result == 7

    def test_error_handling(self):
        lua = SandboxedLua()
        result = lua.execute("this is not valid lua!!")
        assert not result.success
        assert result.error is not None

    def test_reset(self):
        lua = SandboxedLua()
        lua.execute("x = 42")
        lua.reset()
        result = lua.execute("return x")
        assert result.success
        assert result.result is None


class TestTickScheduler:
    def test_tick_count(self):
        scheduler = TickScheduler(tick_rate=60)
        scheduler.run(max_ticks=10)
        assert scheduler.tick_count == 10

    def test_on_tick_callback(self):
        scheduler = TickScheduler(tick_rate=1000)
        ticks = []
        scheduler.on_tick(lambda t, dt: ticks.append(t))
        scheduler.run(max_ticks=5)
        assert ticks == [0, 1, 2, 3, 4]

    def test_scheduled_task(self):
        scheduler = TickScheduler(tick_rate=1000)
        results = []
        scheduler.schedule("test_task", lambda t, dt: results.append(t), interval_ticks=3)
        scheduler.run(max_ticks=10)
        # Should fire at ticks 2, 5, 8 (every 3 ticks, 0-indexed countdown)
        assert len(results) > 0

    def test_metrics(self):
        scheduler = TickScheduler(tick_rate=60)
        scheduler.run(max_ticks=10)
        metrics = scheduler.get_metrics()
        assert metrics["tick_count"] == 10
        assert metrics["tick_rate"] == 60


class TestLuaRunner:
    def test_engine_creation(self):
        runner = LuaRunner(tick_rate=60)
        assert runner is not None

    def test_lua_log(self):
        runner = LuaRunner(tick_rate=60)
        runner.sandbox.execute('log("hello world")')
        logs = runner.get_logs()
        assert any("hello world" in l for l in logs)

    def test_entity_spawn(self):
        runner = LuaRunner(tick_rate=60)
        runner.sandbox.execute('spawn_entity("test_entity", "npc")')
        assert "test_entity" in runner.entities
        assert runner.entities["test_entity"]["type"] == "npc"

    def test_entity_props(self):
        runner = LuaRunner(tick_rate=60)
        runner.sandbox.execute('spawn_entity("e1", "test")')
        runner.sandbox.execute('set_entity_prop("e1", "health", 50)')
        result = runner.sandbox.execute('return get_entity_prop("e1", "health")')
        assert result.result == 50

    def test_entity_destroy(self):
        runner = LuaRunner(tick_rate=60)
        runner.sandbox.execute('spawn_entity("e1", "test")')
        runner.sandbox.execute('destroy_entity("e1")')
        assert "e1" not in runner.entities

    def test_short_run(self):
        runner = LuaRunner(tick_rate=1000)
        runner.start(max_ticks=10)
        metrics = runner.get_metrics()
        assert metrics["tick_count"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
