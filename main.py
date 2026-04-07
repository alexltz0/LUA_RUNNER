#!/usr/bin/env python3
"""
LUA_RUNNER CLI — Interactive demo and script runner.
"""

import sys
import time
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

from engine import LuaRunner

console = Console()


def print_banner():
    banner = """
╔═══════════════════════════════════════════════╗
║   LUA_RUNNER v1.0                             ║
║   Custom Scripting Engine for Game Events      ║
║   Low-Latency · Event-Driven · Sandboxed       ║
╚═══════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_metrics(runner: LuaRunner):
    metrics = runner.get_metrics()
    table = Table(title="Engine Metrics", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")

    table.add_row("Tick Count", str(metrics["tick_count"]))
    table.add_row("Tick Rate", f"{metrics['tick_rate']} TPS")
    table.add_row("Avg Tick Time", f"{metrics['avg_tick_time_ms']:.3f} ms")
    table.add_row("Frame Budget", f"{metrics['frame_budget_usage_pct']:.1f}%")
    table.add_row("Loaded Scripts", str(metrics["loaded_scripts"]))
    table.add_row("Active Entities", str(metrics["entities"]))
    table.add_row("Event Listeners", str(metrics["event_listeners"]))
    table.add_row("Events Emitted", str(metrics["events_emitted"]))

    console.print(table)


def print_logs(runner: LuaRunner):
    logs = runner.get_logs(clear=True)
    if logs:
        console.print("\n[bold yellow]─── Engine Log ───[/bold yellow]")
        for log_line in logs:
            if "[ERROR]" in log_line:
                console.print(f"  {log_line}", style="red")
            elif "[WARN]" in log_line:
                console.print(f"  {log_line}", style="yellow")
            elif "[ENGINE]" in log_line:
                console.print(f"  {log_line}", style="blue")
            else:
                console.print(f"  {log_line}", style="dim")


@click.group()
def cli():
    """LUA_RUNNER — Custom scripting engine for low-latency game events."""
    pass


@cli.command()
@click.option("--scripts", "-s", default="scripts", help="Script directory")
@click.option("--ticks", "-t", default=600, help="Number of ticks to run")
@click.option("--rate", "-r", default=60, help="Tick rate (TPS)")
def run(scripts: str, ticks: int, rate: int):
    """Run the engine with game scripts."""
    print_banner()

    script_dir = Path(scripts).resolve()
    if not script_dir.exists():
        console.print(f"[red]Script directory not found: {script_dir}[/red]")
        sys.exit(1)

    console.print(f"[cyan]Loading scripts from:[/cyan] {script_dir}")
    console.print(f"[cyan]Tick rate:[/cyan] {rate} TPS")
    console.print(f"[cyan]Max ticks:[/cyan] {ticks}\n")

    runner = LuaRunner(tick_rate=rate, script_dir=str(script_dir))

    # Load all scripts
    results = runner.load_directory()
    for r in results:
        if r.success:
            console.print(f"  [green]✓[/green] Script loaded ({r.execution_time_ms:.2f}ms)")
        else:
            console.print(f"  [red]✗[/red] {r.error}")

    console.print(f"\n[bold green]Starting engine...[/bold green]\n")

    start_time = time.perf_counter()
    runner.start(max_ticks=ticks)
    elapsed = time.perf_counter() - start_time

    # Results
    print_logs(runner)
    console.print()
    print_metrics(runner)
    console.print(f"\n[dim]Total wall time: {elapsed:.2f}s[/dim]")


@cli.command()
@click.argument("script_path")
@click.option("--rate", "-r", default=60, help="Tick rate (TPS)")
def exec(script_path: str, rate: int):
    """Execute a single Lua script."""
    print_banner()

    runner = LuaRunner(tick_rate=rate)
    result = runner.sandbox.execute_file(script_path)

    if result.success:
        console.print(f"[green]✓ Executed successfully[/green] ({result.execution_time_ms:.2f}ms)")
        if result.result is not None:
            console.print(f"[cyan]Result:[/cyan] {result.result}")
    else:
        console.print(f"[red]✗ Error:[/red] {result.error}")


@cli.command()
def bench():
    """Run a performance benchmark."""
    print_banner()
    console.print("[bold]Running benchmark...[/bold]\n")

    runner = LuaRunner(tick_rate=120)

    # Benchmark: raw Lua execution
    n_iterations = 10000
    code = "local x = 0; for i=1,1000 do x = x + math.sin(i) * math.cos(i) end; return x"

    start = time.perf_counter()
    for _ in range(n_iterations):
        runner.sandbox.execute(code)
    elapsed = (time.perf_counter() - start) * 1000

    console.print(f"[cyan]Lua execution benchmark:[/cyan]")
    console.print(f"  Iterations: {n_iterations}")
    console.print(f"  Total time: {elapsed:.2f} ms")
    console.print(f"  Per iteration: {elapsed / n_iterations:.4f} ms")
    console.print(f"  Throughput: {n_iterations / (elapsed / 1000):.0f} ops/sec\n")

    # Benchmark: event dispatch
    n_events = 50000
    counter = {"n": 0}

    def handler(record):
        counter["n"] += 1

    runner.events.on("bench.event", handler)

    start = time.perf_counter()
    for i in range(n_events):
        runner.events.emit("bench.event", {"i": i})
    elapsed = (time.perf_counter() - start) * 1000

    console.print(f"[cyan]Event dispatch benchmark:[/cyan]")
    console.print(f"  Events: {n_events}")
    console.print(f"  Total time: {elapsed:.2f} ms")
    console.print(f"  Per event: {elapsed / n_events:.4f} ms")
    console.print(f"  Throughput: {n_events / (elapsed / 1000):.0f} events/sec")


@cli.command()
def interactive():
    """Interactive Lua REPL with engine API."""
    print_banner()
    console.print("[bold green]Interactive mode. Type Lua code, 'quit' to exit.[/bold green]\n")

    runner = LuaRunner(tick_rate=60)
    runner.load_directory("scripts")

    while True:
        try:
            code = console.input("[bold cyan]lua>[/bold cyan] ")
            if code.strip().lower() in ("quit", "exit"):
                break
            if code.strip() == "":
                continue
            if code.strip() == ":metrics":
                print_metrics(runner)
                continue
            if code.strip() == ":logs":
                print_logs(runner)
                continue
            if code.strip() == ":entities":
                for eid, ent in runner.entities.items():
                    console.print(f"  [cyan]{eid}[/cyan]: {ent}")
                continue

            result = runner.sandbox.execute(code)
            if result.success:
                if result.result is not None:
                    console.print(f"[green]→[/green] {result.result}")
                console.print(f"[dim]({result.execution_time_ms:.3f}ms)[/dim]")
            else:
                console.print(f"[red]Error:[/red] {result.error}")

            print_logs(runner)

        except (KeyboardInterrupt, EOFError):
            break

    console.print("\n[dim]Goodbye![/dim]")


if __name__ == "__main__":
    cli()
