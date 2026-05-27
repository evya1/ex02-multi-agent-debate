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

Command implementations live in debate.cli.commands; this module only wires
the argument parser and routes to the correct function.
"""

from __future__ import annotations

import argparse
import sys

from debate.cli.commands import _cmd_ping, _cmd_run, _cmd_skills_list, _cmd_skills_validate


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
