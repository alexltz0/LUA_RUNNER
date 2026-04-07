"""
LuaRunner Core — Orchestrates sandbox, events, and scheduler
into a unified scripting engine for game events.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from engine.events import EventBus
from engine.sandbox import SandboxedLua, ExecutionResult
from engine.scheduler import TickScheduler


class LuaRunner:
    """
    Main engine class. Combines:
    - SandboxedLua for safe script execution
    - EventBus for pub/sub game events
    - TickScheduler for fixed-timestep updates

    Lifecycle: init → load scripts → start → tick loop → stop
    """

    def __init__(self, tick_rate: int = 60, script_dir: Optional[str] = None):
        self.events = EventBus()
        self.sandbox = SandboxedLua()
        self.scheduler = TickScheduler(tick_rate=tick_rate)
        self._script_dir = script_dir
        self._loaded_scripts: Dict[str, str] = {}
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._log_buffer: List[str] = []
        self._started = False

        self._inject_engine_api()
        self.scheduler.on_tick(self._on_tick)

    def _inject_engine_api(self) -> None:
        """Inject the engine API into the Lua sandbox."""
        lua = self.sandbox

        # -- Logging --
        lua.inject_global("log", self._lua_log)
        lua.inject_global("log_warn", self._lua_log_warn)
        lua.inject_global("log_error", self._lua_log_error)

        # -- Events (register from Lua) --
        lua.inject_global("on_event", self._lua_on_event)
        lua.inject_global("emit_event", self._lua_emit_event)

        # -- Entity API --
        lua.inject_global("spawn_entity", self._lua_spawn_entity)
        lua.inject_global("get_entity", self._lua_get_entity)
        lua.inject_global("destroy_entity", self._lua_destroy_entity)
        lua.inject_global("set_entity_prop", self._lua_set_entity_prop)
        lua.inject_global("get_entity_prop", self._lua_get_entity_prop)

        # -- Time / Engine State --
        lua.inject_global("get_tick", lambda: self.scheduler.tick_count)
        lua.inject_global("get_time", lambda: time.time())
        lua.inject_global("get_delta", lambda: self.scheduler.tick_interval)

    # ── Lua-callable API ─────────────────────────────────────────

    def _lua_log(self, *args):
        msg = " ".join(str(a) for a in args)
        self._log_buffer.append(f"[INFO] {msg}")

    def _lua_log_warn(self, *args):
        msg = " ".join(str(a) for a in args)
        self._log_buffer.append(f"[WARN] {msg}")

    def _lua_log_error(self, *args):
        msg = " ".join(str(a) for a in args)
        self._log_buffer.append(f"[ERROR] {msg}")

    def _lua_on_event(self, event_name: str, lua_callback):
        """Register a Lua function as an event listener."""
        def wrapper(record):
            try:
                lua_callback(record.name)
            except Exception as e:
                self._lua_log_error(f"Event handler error: {e}")
        self.events.on(event_name, wrapper)

    def _lua_emit_event(self, event_name: str, data=None):
        """Emit an event from Lua."""
        if data is not None:
            # Convert Lua table to Python dict
            try:
                py_data = dict(data)
            except (TypeError, ValueError):
                py_data = {"value": data}
        else:
            py_data = {}
        self.events.emit(event_name, py_data)

    def _lua_spawn_entity(self, entity_id: str, entity_type: str = "generic"):
        self._entities[entity_id] = {
            "id": entity_id,
            "type": entity_type,
            "health": 100,
            "x": 0,
            "y": 0,
            "active": True,
        }
        self.events.emit("entity.spawn", {"id": entity_id, "type": entity_type})
        return entity_id

    def _lua_get_entity(self, entity_id: str):
        ent = self._entities.get(entity_id)
        if ent:
            return self.sandbox.lua.table_from(ent)
        return None

    def _lua_destroy_entity(self, entity_id: str):
        if entity_id in self._entities:
            self.events.emit("entity.destroy", {"id": entity_id})
            del self._entities[entity_id]
            return True
        return False

    def _lua_set_entity_prop(self, entity_id: str, prop: str, value):
        if entity_id in self._entities:
            self._entities[entity_id][prop] = value
            return True
        return False

    def _lua_get_entity_prop(self, entity_id: str, prop: str):
        ent = self._entities.get(entity_id)
        if ent:
            return ent.get(prop)
        return None

    # ── Script Loading ───────────────────────────────────────────

    def load_script(self, filepath: str) -> ExecutionResult:
        """Load and execute a Lua script file."""
        path = Path(filepath)
        if not path.exists():
            return ExecutionResult(success=False, error=f"Script not found: {filepath}")
        code = path.read_text(encoding="utf-8")
        self._loaded_scripts[str(path)] = code
        result = self.sandbox.execute(code)
        if result.success:
            self._log_buffer.append(f"[ENGINE] Loaded: {path.name}")
        else:
            self._log_buffer.append(f"[ENGINE] Failed to load {path.name}: {result.error}")
        return result

    def load_directory(self, dirpath: Optional[str] = None) -> List[ExecutionResult]:
        """Load all .lua files from a directory."""
        dirpath = dirpath or self._script_dir
        if not dirpath:
            return []

        results = []
        scripts_path = Path(dirpath)
        if not scripts_path.exists():
            return []

        # Load init.lua first if it exists
        init_file = scripts_path / "init.lua"
        if init_file.exists():
            results.append(self.load_script(str(init_file)))

        # Load remaining .lua files
        for lua_file in sorted(scripts_path.glob("**/*.lua")):
            if lua_file.name == "init.lua":
                continue
            results.append(self.load_script(str(lua_file)))

        return results

    def hot_reload(self) -> List[ExecutionResult]:
        """Reload all previously loaded scripts."""
        self.sandbox.reset()
        self._inject_engine_api()
        results = []
        for filepath, code in self._loaded_scripts.items():
            result = self.sandbox.execute(code)
            results.append(result)
        self.events.emit("engine.reload", {})
        return results

    # ── Tick Loop ────────────────────────────────────────────────

    def _on_tick(self, tick: int, dt: float) -> None:
        """Called every tick by the scheduler."""
        self.events.emit("tick", {"tick": tick, "dt": dt})

        # Call Lua on_tick if defined
        try:
            g = self.sandbox.lua.globals()
            on_tick_fn = g["on_tick"]
            if on_tick_fn is not None:
                on_tick_fn(tick, dt)
        except Exception:
            pass

    # ── Lifecycle ────────────────────────────────────────────────

    def start(self, max_ticks: Optional[int] = None) -> None:
        """Start the engine loop."""
        self._started = True
        self.events.emit("engine.start", {})

        # Call Lua on_init if defined
        self.sandbox.call_function("on_init")

        self._log_buffer.append(
            f"[ENGINE] Started at {self.scheduler.tick_rate} TPS"
        )
        self.scheduler.run(max_ticks=max_ticks)
        self._started = False
        self.events.emit("engine.stop", {})

    def stop(self) -> None:
        """Stop the engine loop."""
        self.sandbox.call_function("on_shutdown")
        self.scheduler.stop()
        self._log_buffer.append("[ENGINE] Stopped")

    # ── Introspection ────────────────────────────────────────────

    def get_logs(self, clear: bool = False) -> List[str]:
        logs = list(self._log_buffer)
        if clear:
            self._log_buffer.clear()
        return logs

    def get_metrics(self) -> Dict:
        return {
            **self.scheduler.get_metrics(),
            "loaded_scripts": len(self._loaded_scripts),
            "entities": len(self._entities),
            "event_listeners": self.events.listener_count(),
            "events_emitted": sum(self.events.stats.values()),
        }

    @property
    def entities(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._entities)
