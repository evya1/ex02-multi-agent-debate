"""
Console display helpers for the debate CLI.

Owns all Rich rendering: the banner, transcript lines, verdict panel, and
transcript log viewer.  Kept separate from DebateCLI's navigation logic so
display concerns don't clutter the menu flow.
"""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from debate.models.message import DebateMessage, Role
from debate.models.verdict import Verdict

console = Console()

_ROLE_COLOUR: dict[Role, str] = {
    Role.JUDGE: "yellow",
    Role.PRO: "cyan",
    Role.CON: "magenta",
}


def print_banner() -> None:
    console.print(
        Panel.fit(
            "[bold blue]🤖 AI Agent Debate System[/bold blue]\n"
            "[dim]Exercise 02 — Orchestration of AI[/dim]",
            border_style="blue",
            padding=(1, 4),
        )
    )


def print_transcript(transcript: list[DebateMessage]) -> None:
    console.print(Rule("[bold]Debate Transcript[/bold]"))
    for msg in transcript:
        colour = _ROLE_COLOUR.get(msg.role, "white")
        role_tag = msg.role.value.upper()
        label = (
            f"[{colour}][{role_tag} | Round {msg.round} | {msg.message_type.value}][/{colour}]"
        )
        console.print(f"\n{label}")
        console.print(msg.content)
        if msg.evidence:
            for i, ev in enumerate(msg.evidence, 1):
                console.print(f'  [dim][{i}] {ev.source}: "{ev.quote[:120]}"[/dim]')


def print_verdict(verdict: Verdict) -> None:
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


def view_last_transcript(log_path: str) -> None:
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
