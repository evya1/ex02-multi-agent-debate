"""
agent-debate CLI entry point.

Provides subcommands:
  agent-debate run           — run a debate interactively (uses config/debate.yaml)
  agent-debate run --mock    — offline mock run (no API key)
  agent-debate run --topic "..." --rounds N [--mock]
  agent-debate skills list   — list all registered skills
  agent-debate skills validate — verify skill filesystem dirs

Ping mode (for automated testing / CI):
  agent-debate --mock --topic "AI benefits" --pings N
  Runs N quick mock debate pings (each 1 round) and prints a summary.

This module is registered as a console_script in pyproject.toml so that
`uv run agent-debate` invokes it after `uv sync`.
"""

from __future__ import annotations

import argparse
import sys


def _cmd_run(args: argparse.Namespace) -> None:
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
        colour = {"judge": "yellow", "pro": "cyan", "con": "magenta"}.get(msg.role.value, "white")
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


def _cmd_ping(args: argparse.Namespace) -> None:
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


def _cmd_skills_list(_args: argparse.Namespace) -> None:
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


def _cmd_skills_validate(_args: argparse.Namespace) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent-debate",
        description="AI Agent Debate System",
    )
    parser.add_argument("--mock", action="store_true", help="Use offline mock providers")
    parser.add_argument("--topic", type=str, default="", help="Override debate topic")
    parser.add_argument("--rounds", type=int, default=0, help="Override round count")
    parser.add_argument(
        "--pings",
        type=int,
        default=0,
        help="Run N quick mock pings instead of a full debate",
    )

    subparsers = parser.add_subparsers(dest="command")

    # 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Run a debate")
    run_parser.add_argument("--mock", action="store_true", help="Mock mode")
    run_parser.add_argument("--topic", type=str, default="")
    run_parser.add_argument("--rounds", type=int, default=0)

    # 'skills' subcommand group
    skills_parser = subparsers.add_parser("skills", help="Skill management")
    skills_sub = skills_parser.add_subparsers(dest="skills_command")
    skills_sub.add_parser("list", help="List all registered skills")
    skills_sub.add_parser("validate", help="Validate skill filesystem dirs")

    args = parser.parse_args()

    # Route to handler
    if args.command == "run":
        _cmd_run(args)
    elif args.command == "skills":
        if args.skills_command == "list":
            _cmd_skills_list(args)
        elif args.skills_command == "validate":
            _cmd_skills_validate(args)
        else:
            skills_parser.print_help()
    elif args.pings > 0:
        _cmd_ping(args)
    elif args.command is None:
        # No subcommand: run in interactive menu mode (if topic given, run directly)
        if args.topic or args.mock:
            _cmd_run(args)
        else:
            from debate.cli.menu import DebateCLI
            from debate.models.config import AppConfig

            try:
                config = AppConfig.from_yaml_files()
            except Exception:
                parser.print_help()
                sys.exit(1)
            DebateCLI(config).run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
