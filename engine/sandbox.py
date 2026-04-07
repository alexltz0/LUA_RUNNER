"""
Sandbox — Restricted Lua execution environment.
Prevents access to OS, IO, debug, and other dangerous libraries.
Provides a curated API surface for game scripting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
import time

from lupa import LuaRuntime, LuaError


# Lua libraries that are SAFE to expose
SAFE_LIBS = {
    "math",
    "string",
    "table",
}

# Lua globals that are SAFE
SAFE_GLOBALS = {
    "print",
    "type",
    "tostring",
    "tonumber",
    "pairs",
    "ipairs",
    "next",
    "select",
    "unpack",
    "error",
    "pcall",
    "xpcall",
    "assert",
    "rawget",
    "rawset",
    "rawequal",
    "rawlen",
    "setmetatable",
    "getmetatable",
}

# Lua globals to REMOVE for security
BLOCKED_GLOBALS = {
    "os",
    "io",
    "debug",
    "loadfile",
    "dofile",
    "require",
    "package",
    "collectgarbage",
    "newproxy",
    "load",
    "loadstring",
}

SANDBOX_SETUP = """
-- Remove dangerous globals
os = nil
io = nil
debug = nil
loadfile = nil
dofile = nil
require = nil
package = nil
collectgarbage = nil
newproxy = nil
load = nil
loadstring = nil

-- Utility: shallow copy of a table
function table.shallow_copy(t)
    local copy = {}
    for k, v in pairs(t) do
        copy[k] = v
    end
    return copy
end

-- Utility: clamp
function math.clamp(val, min_val, max_val)
    return math.max(min_val, math.min(max_val, val))
end

-- Utility: lerp
function math.lerp(a, b, t)
    return a + (b - a) * t
end
"""


class ExecutionResult:
    """Result of a sandboxed Lua execution."""

    def __init__(
        self,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        execution_time_ms: float = 0.0,
    ):
        self.success = success
        self.result = result
        self.error = error
        self.execution_time_ms = execution_time_ms

    def __repr__(self):
        if self.success:
            return f"<ExecutionResult ok={self.result} time={self.execution_time_ms:.2f}ms>"
        return f"<ExecutionResult error='{self.error}' time={self.execution_time_ms:.2f}ms>"


class SandboxedLua:
    """
    Sandboxed Lua runtime with:
    - Blocked dangerous globals (os, io, debug, etc.)
    - Execution time tracking
    - Memory limit awareness
    - Curated math/string/table extensions
    - Python ↔ Lua bridge for engine API injection
    """

    def __init__(self, max_execution_ms: float = 100.0):
        self._max_execution_ms = max_execution_ms
        self._lua = LuaRuntime(unpack_returned_tuples=True)
        self._globals_injected: Dict[str, Any] = {}
        self._setup_sandbox()

    def _setup_sandbox(self) -> None:
        """Apply sandbox restrictions."""
        self._lua.execute(SANDBOX_SETUP)

    def inject_global(self, name: str, value: Any) -> None:
        """Inject a Python value/function into the Lua global namespace."""
        g = self._lua.globals()
        g[name] = value
        self._globals_injected[name] = value

    def inject_api(self, namespace: str, api: Dict[str, Any]) -> None:
        """Inject a table of functions under a namespace (e.g., 'engine.log')."""
        g = self._lua.globals()
        table = self._lua.table_from(api)
        g[namespace] = table

    def execute(self, code: str) -> ExecutionResult:
        """Execute Lua code in the sandbox."""
        start = time.perf_counter()
        try:
            result = self._lua.execute(code)
            elapsed = (time.perf_counter() - start) * 1000
            return ExecutionResult(
                success=True,
                result=result,
                execution_time_ms=elapsed,
            )
        except LuaError as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=elapsed,
            )

    def execute_file(self, filepath: str) -> ExecutionResult:
        """Execute a Lua file in the sandbox."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
            return self.execute(code)
        except FileNotFoundError:
            return ExecutionResult(success=False, error=f"File not found: {filepath}")
        except IOError as e:
            return ExecutionResult(success=False, error=f"IO error: {e}")

    def call_function(self, func_name: str, *args) -> ExecutionResult:
        """Call a Lua function by name."""
        start = time.perf_counter()
        try:
            g = self._lua.globals()
            func = g[func_name]
            if func is None:
                return ExecutionResult(
                    success=False,
                    error=f"Function '{func_name}' not found",
                )
            result = func(*args)
            elapsed = (time.perf_counter() - start) * 1000
            return ExecutionResult(
                success=True,
                result=result,
                execution_time_ms=elapsed,
            )
        except LuaError as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ExecutionResult(success=False, error=str(e), execution_time_ms=elapsed)

    def get_global(self, name: str) -> Any:
        """Get a Lua global value."""
        return self._lua.globals()[name]

    def set_global(self, name: str, value: Any) -> None:
        """Set a Lua global value."""
        self._lua.globals()[name] = value

    def reset(self) -> None:
        """Reset the sandbox (new Lua state)."""
        self._lua = LuaRuntime(unpack_returned_tuples=True)
        self._setup_sandbox()
        for name, value in self._globals_injected.items():
            self._lua.globals()[name] = value

    @property
    def lua(self) -> LuaRuntime:
        return self._lua
