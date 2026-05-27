"""
DebateCLI — Rich-powered interactive terminal menu.

Why Rich?  It provides colour, panels, tables, and live progress without
requiring a curses setup or complex UI framework.

The menu gives operators a zero-code way to:
  - Start a debate with the current config
  - Change the topic or round count
  - Print a previous transcript from the JSONL log
"""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.rule import Rule
from rich.table import Table

from debate.models.config import AppConfig
from debate.models.message import DebateMessage, Role
from debate.models.verdict import Verdict
from debate.runner import DebateRunner

console = Console()

_ROLE_COLOUR = {
    Role.JUDGE: "yellow",
    Role.PRO: "cyan",
    Role.CON: "magenta",
}


class DebateCLI:
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    # ── public entry-point ─────────────────────────────────────────────────────

    def run(self) -> None:
        self._print_banner()
        while True:
            choice = self._main_menu()
            if choice == "1":
                self._start_debate()
            elif choice == "2":
                self._change_topic()
            elif choice == "3":
                self._change_rounds()
            elif choice == "4":
                self._view_last_transcript()
            elif choice == "5":
                console.print("\n[dim]Goodbye.[/dim]\n")
                break

    # ── menu screens ───────────────────────────────────────────────────────────

    def _print_banner(self) -> None:
        console.print(Panel.fit(
            "[bold blue]🤖 AI Agent Debate System[/bold blue]\n"
            "[dim]Exercise 02 — Orchestration of AI[/dim]",
            border_style="blue",
            padding=(1, 4),
        ))

    def _main_menu(self) -> str:
        console.print()
        table = Table(show_header=False, box=None, padding=(0, 2))
        topic_preview = self._config.debate.topic[:60]
        rounds_label = f"Change rounds  [dim](currently {self._config.debate.rounds})[/dim]"
        table.add_row("[bold cyan]1[/bold cyan]", f"Start debate  [dim]— {topic_preview}[/dim]")
        table.add_row("[bold cyan]2[/bold cyan]", "Change topic")
        table.add_row("[bold cyan]3[/bold cyan]", rounds_label)
        table.add_row("[bold cyan]4[/bold cyan]", "View last transcript")
        table.add_row("[bold cyan]5[/bold cyan]", "Exit")
        console.print(table)
        return Prompt.ask("\nOption", choices=["1", "2", "3", "4", "5"])

    def _change_topic(self) -> None:
        new_topic = Prompt.ask("New topic")
        if new_topic.strip():
            self._config.debate.topic = new_topic.strip()
            console.print("[green]✓ Topic updated.[/green]")

    def _change_rounds(self) -> None:
        n = IntPrompt.ask("Number of rounds per side (5 = budget, 10 = full)", default=5)
        self._config.debate.rounds = max(1, n)
        console.print(f"[green]✓ Rounds set to {self._config.debate.rounds}.[/green]")

    # ── debate execution ───────────────────────────────────────────────────────

    def _start_debate(self) -> None:
        console.print(Rule("[bold]Starting Debate[/bold]"))
        console.print(f"[dim]Topic:[/dim] {self._config.debate.topic}")
        console.print(f"[dim]Rounds:[/dim] {self._config.debate.rounds} per side\n")

        runner = DebateRunner(self._config)
        try:
            transcript, verdict = runner.run()
        except KeyboardInterrupt:
            console.print("\n[yellow]Debate interrupted.[/yellow]")
            return
        except Exception as exc:
            console.print(f"\n[red]Error during debate: {exc}[/red]")
            raise

        self._print_transcript(transcript)
        self._print_verdict(verdict)
        console.print(f"\n[dim]Total API cost: ${runner._gatekeeper.total_cost:.4f}[/dim]")

    # ── display helpers ────────────────────────────────────────────────────────

    def _print_transcript(self, transcript: list[DebateMessage]) -> None:
        console.print(Rule("[bold]Debate Transcript[/bold]"))
        for msg in transcript:
            colour = _ROLE_COLOUR.get(msg.role, "white")
            role_tag = msg.role.value.upper()
            label = (
                f"[{colour}][{role_tag} | Round {msg.round}"
                f" | {msg.message_type.value}][/{colour}]"
            )
            console.print(f"\n{label}")
            console.print(msg.content)
            if msg.evidence:
                for i, ev in enumerate(msg.evidence, 1):
                    console.print(f"  [dim][{i}] {ev.source}: \"{ev.quote[:120]}\"[/dim]")

    def _print_verdict(self, verdict: Verdict) -> None:
        console.print(Rule("[bold]Verdict[/bold]"))
        winner_colour = "cyan" if verdict.winner.value == "pro" else "magenta"
        console.print(
            Panel(
                f"[bold {winner_colour}]🏆 {verdict.winner.value.upper()} WINS"
                f"[/bold {winner_colour}]\n\n"
                f"PRO score: {verdict.total_pro_score:.1f}   "
                f"CON score: {verdict.total_con_score:.1f}\n\n"
                f"[italic]Key turning point:[/italic] {verdict.key_turning_point}\n\n"
                f"{verdict.reasoning}",
                border_style=winner_colour,
            )
        )

    # ── transcript viewer ──────────────────────────────────────────────────────

    def _view_last_transcript(self) -> None:
        log_path = self._config.logging.file
        if not Path(log_path).exists():
            console.print("[yellow]No transcript found yet.[/yellow]")
            return

        console.print(Rule("[bold]Last Debate Log[/bold]"))
        with open(log_path) as f:
            lines = f.readlines()

        if not lines:
            console.print("[yellow]Log file is empty.[/yellow]")
            return

        for line in lines[-200:]:  # show last 200 entries
            try:
                entry = json.loads(line)
                role = entry.get("role", entry.get("event", "?"))
                content = entry.get("content") or entry.get("reasoning") or str(entry.get("event"))
                console.print(f"[dim]{role}[/dim]: {str(content)[:200]}")
            except json.JSONDecodeError:
                pass
