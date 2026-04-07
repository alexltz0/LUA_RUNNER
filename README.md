# LUA_RUNNER

**Custom scripting engine optimized for low-latency game events.**

A Python-based game scripting engine that embeds Lua (via LuaJIT) for high-performance, event-driven game logic. Features a sandboxed execution environment, a pub/sub event bus, fixed-timestep scheduling, and a complete entity management API.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│                 LuaRunner Core              │
├──────────┬──────────┬───────────────────────┤
│ EventBus │ Sandbox  │   TickScheduler       │
│ pub/sub  │ LuaJIT   │   60 TPS fixed-step   │
│ wildcard │ no OS/IO │   task scheduling      │
│ priority │ API gate │   perf metrics         │
├──────────┴──────────┴───────────────────────┤
│              Engine API Layer               │
│  log · events · entities · time · combat    │
├─────────────────────────────────────────────┤
│            Lua Game Scripts                 │
│  init.lua · enemies.lua · combat.lua · ...  │
└─────────────────────────────────────────────┘
```

## Features

- **Sandboxed Lua Execution** — Dangerous globals (`os`, `io`, `debug`, `require`) stripped. Scripts can't escape the sandbox.
- **Event-Driven Architecture** — Pub/sub with priorities, wildcards (`entity.*`), one-shot listeners, and propagation control.
- **Fixed-Timestep Scheduler** — Configurable tick rate (default 60 TPS), scheduled tasks, frame budget tracking.
- **Entity System** — Spawn, destroy, and modify entities with property access from Lua.
- **Hot Reload** — Reload all scripts without restarting the engine.
- **Performance Metrics** — Tick time, frame budget usage, event throughput tracking.
- **Interactive REPL** — Live Lua console with engine API access.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the demo (600 ticks at 60 TPS = 10 seconds)
python main.py run --scripts scripts --ticks 600

# Interactive REPL
python main.py interactive

# Run benchmark
python main.py bench

# Execute a single script
python main.py exec scripts/init.lua
```

## Lua API Reference

### Logging
```lua
log("message")           -- Info log
log_warn("warning")      -- Warning log  
log_error("error")       -- Error log
```

### Events
```lua
on_event("event.name", function(name)
    -- handle event
end)

emit_event("event.name", { key = "value" })
```

### Entities
```lua
spawn_entity("id", "type")              -- Create entity
get_entity("id")                         -- Get entity table
destroy_entity("id")                     -- Remove entity
set_entity_prop("id", "health", 100)     -- Set property
get_entity_prop("id", "health")          -- Get property
```

### Engine State
```lua
get_tick()    -- Current tick number
get_time()    -- Wall clock time
get_delta()   -- Delta time per tick
```

### Lifecycle Hooks
```lua
function on_init()      -- Called when engine starts
function on_tick(t, dt) -- Called every tick
function on_shutdown()  -- Called when engine stops
```

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Project Structure

```
lua_runner/
├── engine/
│   ├── __init__.py       # Package exports
│   ├── core.py           # LuaRunner orchestrator
│   ├── events.py         # EventBus pub/sub system
│   ├── sandbox.py        # Sandboxed Lua execution
│   └── scheduler.py      # Fixed-timestep tick scheduler
├── scripts/
│   ├── init.lua          # Game initialization
│   ├── enemies.lua       # Enemy spawning & AI
│   ├── combat.lua        # Damage & healing system
│   └── game_loop.lua     # Main tick loop
├── tests/
│   └── test_engine.py    # Unit tests
├── website/              # Portfolio website (React + Tailwind)
├── main.py               # CLI entry point
├── requirements.txt      # Python dependencies
└── README.md
```

## Tech Stack

- **Python 3.10+** — Host runtime
- **lupa (LuaJIT)** — Embedded Lua with JIT compilation
- **rich** — Terminal UI
- **click** — CLI framework
- **React + Vite + Tailwind** — Portfolio website

## License

MIT
