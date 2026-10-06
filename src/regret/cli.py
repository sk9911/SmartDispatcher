"""`regret <cmd>` dispatches to `regret.<cmd>.main`."""

import importlib
import sys

COMMANDS = ("fetch", "compute", "report", "ensemble", "geostrophic", "neuralgcm")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: regret <command> [args...]\n\ncommands:")
        for c in COMMANDS:
            print(f"  {c}")
        return 0 if argv else 2
    cmd, rest = argv[0], argv[1:]
    if cmd not in COMMANDS:
        print(f"regret: unknown command '{cmd}' (expected one of: {', '.join(COMMANDS)})", file=sys.stderr)
        return 2
    name = f"regret.{cmd}"
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as e:
        if e.name != name:
            raise
        print(f"regret: module {name} not found for command '{cmd}'", file=sys.stderr)
        return 2
    return module.main(rest)


if __name__ == "__main__":
    sys.exit(main())
