import sys


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "agent":
        from .agent.cli import main as agent_main
        return agent_main(args[1:])
    from .bilisub import main as legacy_main
    return legacy_main(args, prog="bilidigest")


if __name__ == "__main__":
    raise SystemExit(main())
