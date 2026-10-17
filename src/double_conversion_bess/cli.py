"""Command-line entry point."""

import argparse

from .profiles import read_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Double-conversion BESS project tools")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-profile", help="Check an SI-unit load CSV")
    validate.add_argument("path")
    validate.add_argument("--base-power-mw", type=float, help="Power base for Load_pu")
    run = commands.add_parser("simulate", help="Run the provisional model and export HTML/CSV")
    run.add_argument("path")
    run.add_argument("--base-power-mw", type=float, required=True)
    run.add_argument("--battery-scale", type=float, default=0.025)
    run.add_argument("--config", help="JSON file overriding Config fields")
    run.add_argument("--output", default="outputs/latest")
    args = parser.parse_args()
    try:
        base = None if args.base_power_mw is None else args.base_power_mw * 1e6
        time, power = read_profile(args.path, base_power_w=base)
        if args.command == "simulate":
            import json
            from pathlib import Path
            from .config import Config
            from .simulation import simulate
            from .report import write_report
            options = dict(rated_power_w=base, battery_scale=args.battery_scale)
            if args.config:
                options.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
            if options["rated_power_w"] != base:
                raise ValueError("Config rated_power_w must match --base-power-mw")
            result = simulate(time, power, Config(**options))
            print(result.termination)
            print(f"HTML report: {write_report(result, args.output)}")
            return
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(f"Valid profile: {len(time)} samples, {time[0]:g}–{time[-1]:g} s, "
          f"peak {power.max() / 1e6:g} MW")


if __name__ == "__main__":
    main()
