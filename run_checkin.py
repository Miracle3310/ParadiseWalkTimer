from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wechat_timer.app import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run WeChat mini-program check-in automation.")
    parser.add_argument(
        "--mode",
        choices=("scheduled", "retry", "dry-run"),
        default="scheduled",
        help="scheduled runs the daily task, retry runs only when pending, dry-run avoids clicking check-in.",
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("config.yaml")),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even when today's state says the task has already completed.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(mode=args.mode, config_path=Path(args.config), force=args.force)


if __name__ == "__main__":
    sys.exit(main())

