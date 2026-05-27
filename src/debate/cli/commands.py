"""
CLI command implementations for the agent-debate console script.

Each _cmd_* function handles one subcommand.  They are kept here (separate
from the argument-parser wiring in entry.py) so that entry.py stays focused
on routing and these functions stay focused on doing work.
"""

from __future__ import annotations

import sys


def _cmd_run(args) -> None:
    """Run a full debate (or mock debate) and print the result."""
    from rich.console import Console
    from rich.rule import Rule

    from debate.sdk import AgentDebateSDK

    console = Console()
    sdk = AgentDebateSDK(use_mock=args.mock)

    topic = args.topic or None
    rounds = args.rounds or None

    console.print(Rule("[bold]Agent Debate[/bold]"))
    if args.mock:
        console.print("[dim]Running in MOCK mode (no real API calls)[/dim]")
    if topic:
        console.print(f"[dim]Topic override:[/dim] {topic}")

    transcript, verdict = sdk.run_debate(topic=topic, rounds=rounds)

    console.print(f"\n[bold]Transcript[/bold] ({len(transcript)} messages)")
    for msg in transcript:
        colour = {"judge": "yellow", "pro": "cyan", "con": "magenta"}.get(
            msg.role.value, "white"
        )
        console.print(
            f"  [{colour}][{msg.role.value.upper()} R{msg.round} {msg.message_type.value}]"
            f"[/{colour}] {msg.content[:120]}"
        )

    console.print(Rule("[bold]Verdict[/bold]"))
    winner_colour = "cyan" if verdict.winner.value == "pro" else "magenta"
    console.print(
        f"[bold {winner_colour}]🏆 {verdict.winner.value.upper()} WINS[/bold {winner_colour}]"
        f" — PRO {verdict.total_pro_score:.1f} vs CON {verdict.total_con_score:.1f}"
    )
    console.print(f"[italic]Key turning point:[/italic] {verdict.key_turning_point}")


def _cmd_ping(args) -> None:
    """Run N quick mock debate pings and report results."""
    from rich.console import Console
    from rich.table import Table

    from debate.sdk import AgentDebateSDK

    console = Console()
    sdk = AgentDebateSDK(use_mock=True)
    topic = args.topic or "AI will benefit humanity"

    console.print(f"[bold]Ping mode:[/bold] {args.pings} pings — topic: {topic}")

    table = Table("Ping", "Winner", "Messages", "Pro Score", "Con Score")
    for i in range(1, args.pings + 1):
        transcript, verdict = sdk.run_debate(topic=topic, rounds=1)
        table.add_row(
            str(i),
            verdict.winner.value.upper(),
            str(len(transcript)),
            f"{verdict.total_pro_score:.1f}",
            f"{verdict.total_con_score:.1f}",
        )

    console.print(table)
    console.print(f"[green]✓ {args.pings} pings completed.[/green]")


def _cmd_skills_list(_args) -> None:
    """List all registered skills."""
    from rich.console import Console
    from rich.table import Table

    from debate.sdk import AgentDebateSDK

    console = Console()
    sdk = AgentDebateSDK(use_mock=True)
    skills = sdk.list_skills()

    table = Table("Skill Name", "Intended Agents", "Trigger")
    for s in skills:
        table.add_row(
            s.name,
            ", ".join(s.intended_agents),
            s.trigger[:80],
        )

    console.print(table)
    console.print(f"[dim]{len(skills)} skills registered.[/dim]")


def _cmd_skills_validate(_args) -> None:
    """Validate that all skill filesystem dirs exist with required files."""
    from rich.console import Console

    from debate.sdk import AgentDebateSDK

    console = Console()
    sdk = AgentDebateSDK(use_mock=True)
    results = sdk.validate_skills()

    all_ok = True
    for name, ok in results.items():
        icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
        console.print(f"  {icon} {name}")
        if not ok:
            all_ok = False

    if all_ok:
        console.print(f"\n[green]All {len(results)} skills validated.[/green]")
    else:
        console.print("\n[red]Some skills are missing filesystem docs.[/red]")
        sys.exit(1)
