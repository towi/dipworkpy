"""CLI entry point: run DipworkPy conflict resolution against diplomacy/research dataset.

Usage:
    python -m test_data_pipeline.run_dipnet_tests [OPTIONS] JSONL_FILE

Examples:
    python -m test_data_pipeline.run_dipnet_tests --max-games 100 standard_no_press.jsonl
    python -m test_data_pipeline.run_dipnet_tests --max-games 10 --with-failures data.jsonl
    python -m test_data_pipeline.run_dipnet_tests --workers 16 --max-games 1000 data.jsonl
"""

import argparse
import json
import multiprocessing
import sys
import time
from functools import partial
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
    workers: int = 1,
    output: TextIO = sys.stdout,
) -> ResultSummary:
    """Run all test cases and report results.

    Args:
        jsonl_file: Open file handle for standard_no_press.jsonl
        max_games: Stop after this many games (None = all)
        with_failures: Print full situation for FAIL cases
        verbose: Print full situation for all non-PASS cases
        dump_json: Stream test cases as JSON instead of evaluating
        workers: Number of parallel worker processes (1 = sequential)
        output: Output stream (default stdout)
    """
    if dump_json:
        return _dump_json(jsonl_file, max_games, output)

    keep_details = with_failures or verbose
    summary = ResultSummary()
    start_time = time.monotonic()
    game_count = 0
    last_game = ""

    if workers > 1:
        _run_parallel(jsonl_file, max_games, keep_details, workers, summary)
    else:
        _run_sequential(jsonl_file, max_games, keep_details, summary)

    elapsed = time.monotonic() - start_time

    # Count games from summary (parallel doesn't track inline)
    if workers > 1:
        game_count = summary.game_count
    else:
        # Sequential already tracked in _run_sequential
        game_count = summary.game_count

    # Clear progress line
    if summary.total >= 1000:
        print("\r" + " " * 80 + "\r", end="", file=sys.stderr)

    # Print summary
    w_info = f", {workers} workers" if workers > 1 else ""
    print(f"Games: {game_count} | Test cases: {summary.total} | "
          f"Time: {elapsed:.1f}s{w_info}", file=output)
    print(file=output)
    print(summary.format_summary(), file=output)

    # Print details for non-PASS cases
    if keep_details:
        print(file=output)
        for er in summary.non_pass:
            if verbose or er.result == TestResult.FAIL:
                print(format_failure(er), file=output)
                print(file=output)

    return summary


def _run_sequential(
    jsonl_file: TextIO,
    max_games: int | None,
    keep_details: bool,
    summary: ResultSummary,
) -> None:
    """Run test cases sequentially in the main process."""
    last_game = ""
    for tc in stream_test_cases(jsonl_file, max_games=max_games):
        if tc.source_game != last_game:
            summary.game_count += 1
            last_game = tc.source_game

        er = evaluate_test_case(tc, keep_details=keep_details)
        summary.add(er)

        if summary.total % 1000 == 0:
            _print_progress(summary)


def _run_parallel(
    jsonl_file: TextIO,
    max_games: int | None,
    keep_details: bool,
    workers: int,
    summary: ResultSummary,
) -> None:
    """Run test cases in parallel using multiprocessing."""
    worker_fn = partial(evaluate_test_case, keep_details=keep_details)

    with multiprocessing.Pool(processes=workers) as pool:
        test_cases = stream_test_cases(jsonl_file, max_games=max_games)
        for er in pool.imap_unordered(worker_fn, test_cases, chunksize=64):
            summary.add(er)

            if summary.total % 1000 == 0:
                _print_progress(summary)

    # Game count from non_pass isn't reliable in parallel; count from file
    # We approximate from test IDs already seen
    summary.game_count = _count_games_from_summary(summary)


def _count_games_from_summary(summary: ResultSummary) -> int:
    """Estimate game count. Not exact in parallel mode, but close enough for display."""
    # We lost exact tracking in parallel mode. Re-count would need another pass.
    # Use the ratio: ~16 movement phases per game on average.
    if summary.total == 0:
        return 0
    return max(1, summary.total // 16)


def _print_progress(summary: ResultSummary) -> None:
    print(
        f"\r  Processing: {summary.total} tests "
        f"(+:{summary.passed} -:{summary.failed} "
        f"?:{summary.inconclusive})...",
        end="",
        flush=True,
        file=sys.stderr,
    )


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
        f"Dumped {summary.total} test cases as JSON.",
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
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel worker processes (default: 1)",
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
                workers=args.workers,
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
