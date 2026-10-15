"""Executable example: python run_service.py"""
import argparse

from tool_loop import ReleaseRequest, run_tool_loop


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a release diagnostics tool loop")
    parser.add_argument("service")
    parser.add_argument("build")
    parser.add_argument("checks", nargs="+", help="check results, for example passed lint")
    args = parser.parse_args()
    report = run_tool_loop(ReleaseRequest(args.service, args.build, tuple(args.checks)))
    print(report)


if __name__ == "__main__":
    main()

