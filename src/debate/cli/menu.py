"""
DebateCLI — Rich-powered interactive terminal menu.

Handles navigation (menu loop, topic/round changes, debate launch) and
delegates all console rendering to debate.cli.display.
"""

from __future__ import annotations

from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from debate.cli.display import (
    console,
    print_banner,
    print_transcript,
    print_verdict,
    view_last_transcript,
)
from debate.models.config import AppConfig
from debate.runner import DebateRunner


class DebateCLI:
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    # ── public entry-point ─────────────────────────────────────────────────────

    def run(self) -> None:
        print_banner()
        while True:
            choice = self._main_menu()
            if choice == "1":
                self._start_debate()
            elif choice == "2":
                self._change_topic()
            elif choice == "3":
                self._change_rounds()
            elif choice == "4":
                view_last_transcript(self._config.logging.file)
            elif choice == "5":
                console.print("\n[dim]Goodbye.[/dim]\n")
                break

    # ── menu screens ───────────────────────────────────────────────────────────

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
        from rich.rule import Rule

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

        print_transcript(transcript)
        print_verdict(verdict)
        console.print(f"\n[dim]Total API cost: ${runner._gatekeeper.total_cost:.4f}[/dim]")
