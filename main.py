"""
Entry point for the AI Agent Debate System.

Two modes:
  python main.py          → interactive Rich menu
  python main.py --run    → run debate immediately with config defaults (SDK mode)

The --run flag is the programmatic / CI-friendly path; the menu is for
interactive use where operators want to adjust topic/rounds before starting.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv


def _load_config():
    from debate.models.config import AppConfig
    return AppConfig.from_yaml_files(
        debate_path=Path("config/debate.yaml"),
        models_path=Path("config/models.yaml"),
    )


def run_interactive() -> None:
    from debate.cli.menu import DebateCLI
    config = _load_config()
    DebateCLI(config).run()


def run_direct() -> None:
    """SDK mode: run the debate and print a summary to stdout."""
    from rich.console import Console
    from debate.runner import DebateRunner

    console = Console()
    config = _load_config()

    console.print(f"[bold]Topic:[/bold] {config.debate.topic}")
    console.print(f"[bold]Rounds:[/bold] {config.debate.rounds} per side\n")

    runner = DebateRunner(config)
    transcript, verdict = runner.run()

    for msg in transcript:
        role_label = f"[{msg.role.value.upper()}]"
        console.print(f"\n{role_label} Round {msg.round} ({msg.message_type.value})")
        console.print(msg.content)

    console.print("\n" + "=" * 60)
    console.print(f"[bold]WINNER: {verdict.winner.value.upper()}[/bold]")
    console.print(verdict.summary())
    console.print(f"\n[dim]Total cost: ${runner._gatekeeper.total_cost:.4f}[/dim]")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="AI Agent Debate System")
    parser.add_argument("--run", action="store_true", help="Run debate directly (no menu)")
    args = parser.parse_args()

    if args.run:
        run_direct()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
