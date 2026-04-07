"""
LUA_RUNNER - Custom scripting engine optimized for low-latency game events.
"""

__version__ = "1.0.0"

from engine.core import LuaRunner
from engine.events import EventBus
from engine.sandbox import SandboxedLua
from engine.scheduler import TickScheduler
