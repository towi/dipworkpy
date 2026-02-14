"""CLI entry point: run DipworkPy conflict resolution against diplomacy/research dataset.

Usage:
    python -m test_data_pipeline.run_dipnet_tests [OPTIONS] JSONL_FILE

Examples:
    python -m test_data_pipeline.run_dipnet_tests --max-games 100 standard_no_press.jsonl
    python -m test_data_pipeline.run_dipnet_tests --max-games 10 --with-failures data.jsonl
    python -m test_data_pipeline.run_dipnet_tests --dump-json --max-games 5 data.jsonl
"""

import argparse
import json
import sys
import time
from typing import TextIO

from .dipnet_parser import stream_test_cases
from .evaluator import (
    EvalResult,
    ResultSummary,
    TestResult,
    evaluate_test_case,
    format_failure,
)


def run_tests(
    jsonl_file: TextIO,
    max_games: int | None = None,
    with_failures: bool = False,
    verbose: bool = False,
    dump_json: bool = False,
    output: TextIO = sys.stdout,
) -> ResultSummary:
    """Run all test cases and report results.

    Args:
        jsonl_file: Open file handle for standard_no_press.jsonl
        max_games: Stop after this many games (None = all)
        with_failures: Print full situation for FAIL cases
        verbose: Print full situation for all non-PASS cases
        dump_json: Stream test cases as JSON instead of evaluating
        output: Output stream (default stdout)
    """
    if dump_json:
        return _dump_json(jsonl_file, max_games, output)

    summary = ResultSummary()
    start_time = time.monotonic()
    game_count = 0
    last_game = ""

    for tc in stream_test_cases(jsonl_file, max_games=max_games):
        if tc.source_game != last_game:
            game_count += 1
            last_game = tc.source_game

        er = evaluate_test_case(tc)
        summary.add(er)

        # Progress indicator every 1000 tests
        if summary.total % 1000 == 0:
            elapsed = time.monotonic() - start_time
            rate = summary.total / elapsed if elapsed > 0 else 0
            print(
                f"\r  Processing: {summary.total:,} tests "
                f"({game_count:,} games, {rate:.0f} tests/sec)...",
                end="",
                flush=True,
                file=sys.stderr,
            )

    elapsed = time.monotonic() - start_time

    # Clear progress line
    if summary.total >= 1000:
        print("\r" + " " * 70 + "\r", end="", file=sys.stderr)

    # Print summary
    print(f"Games: {game_count:,} | Test cases: {summary.total:,} | "
          f"Time: {elapsed:.1f}s", file=output)
    print(file=output)
    print(summary.format_summary(), file=output)

    # Print details for non-PASS cases
    if with_failures or verbose:
        print(file=output)
        for er in summary.non_pass:
            if verbose or er.result == TestResult.FAIL:
                print(format_failure(er), file=output)
                print(file=output)

    return summary


def _dump_json(
    jsonl_file: TextIO,
    max_games: int | None,
    output: TextIO,
) -> ResultSummary:
    """Stream test cases as JSON objects to output."""
    summary = ResultSummary()
    for tc in stream_test_cases(jsonl_file, max_games=max_games):
        summary.total += 1
        obj = {
            "id": tc.id,
            "source_game": tc.source_game,
            "source_phase": tc.source_phase,
            "has_convoy": tc.has_convoy,
            "has_void": tc.has_void,
            "orders": [
                {
                    "nation": o.nation,
                    "utype": o.utype,
                    "current": o.current,
                    "order": o.order.value if o.order else None,
                    "dest": o.dest,
                }
                for o in tc.orders
            ],
            "expected": [
                {
                    "nation": e.nation,
                    "utype": e.utype,
                    "current": e.current,
                    "order": e.order.value if e.order else None,
                    "dest": e.dest,
                    "succeeds": e.succeeds,
                    "dislodged": e.dislodged,
                }
                for e in tc.expected
            ],
        }
        print(json.dumps(obj), file=output)
    print(
        f"Dumped {summary.total:,} test cases as JSON.",
        file=sys.stderr,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run DipworkPy conflict resolution against diplomacy/research dataset."
    )
    parser.add_argument(
        "jsonl_file",
        help="Path to standard_no_press.jsonl",
    )
    parser.add_argument(
        "--max-games",
        type=int,
        default=None,
        help="Stop after N games (default: all)",
    )
    parser.add_argument(
        "--with-failures",
        action="store_true",
        help="Print full situation for FAIL cases in DipworkPy notation",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full situation for all non-PASS cases (FAIL + ERROR + INCONCLUSIVE)",
    )
    parser.add_argument(
        "--dump-json",
        action="store_true",
        help="Stream test cases as JSON to stdout (no evaluation)",
    )

    args = parser.parse_args()

    try:
        with open(args.jsonl_file) as f:
            summary = run_tests(
                f,
                max_games=args.max_games,
                with_failures=args.with_failures,
                verbose=args.verbose,
                dump_json=args.dump_json,
            )
    except FileNotFoundError:
        print(f"Error: File not found: {args.jsonl_file}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)

    # Exit with non-zero if there were failures or errors
    if summary.failed > 0 or summary.errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
