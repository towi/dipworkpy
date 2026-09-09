"""CLI entry point: run DipworkPy conflict resolution against diplomacy/research dataset.

Usage:
    python -m test_data_pipeline.run_dipnet_tests [OPTIONS] JSONL_FILE

Examples:
    python -m test_data_pipeline.run_dipnet_tests --max-games 100 standard_no_press.jsonl
    python -m test_data_pipeline.run_dipnet_tests --max-games 10 --with-failures data.jsonl
    python -m test_data_pipeline.run_dipnet_tests --workers 16 --max-games 1000 data.jsonl
    python -m test_data_pipeline.run_dipnet_tests --max-games 100 --cluster-failures data.jsonl
"""

import argparse
import json
import multiprocessing
import sys
import time
from collections import Counter, defaultdict
from functools import partial
from typing import List, TextIO

from .dipnet_parser import DwpcrTestCase, stream_test_cases
from .evaluator import (
    EvalResult,
    ResultSummary,
    TestResult,
    evaluate_test_case,
    format_failure,
)


def _order_signature(case: DwpcrTestCase) -> str:
    """Order-type counts for the test case, as a stable signature string.

    Example: "con:1,mve:3,msup:1" for a case with 1 convoy, 3 moves, 1 move-support.
    """
    c: Counter[str] = Counter((o.order.value if o.order else "none") for o in case.orders)
    return ",".join(f"{k}:{v}" for k, v in sorted(c.items()))


def _void_order_signature(case: DwpcrTestCase) -> str:
    """Signature for the orders the dataset marked as 'void'.

    Much finer-grained than the full-case signature for void clusters:
    most cluster value comes from knowing *which* orders triggered void,
    not the broader phase context.
    """
    if not case.void_order_indices:
        return "(no-void-marked)"
    c: Counter[str] = Counter()
    for i in case.void_order_indices:
        if 0 <= i < len(case.orders):
            o = case.orders[i]
            c[o.order.value if o.order else "none"] += 1
    return ",".join(f"{k}:{v}" for k, v in sorted(c.items()))


def _cluster_report(
    eval_results: List[EvalResult],
    bucket_label: str,
    top_n: int = 20,
    examples_per_cluster: int = 3,
    sig_fn=_order_signature,
    sig_label: str = "order-type",
) -> List[str]:
    """Build a top-N cluster report for a list of EvalResult.

    Returns a list of report lines. Caller wraps in headers/markdown.
    """
    signatures: Counter[str] = Counter()
    examples: dict[str, List[str]] = defaultdict(list)

    skipped = 0
    for er in eval_results:
        if er.test_case is None:
            skipped += 1
            continue
        sig = sig_fn(er.test_case)
        signatures[sig] += 1
        if len(examples[sig]) < examples_per_cluster:
            examples[sig].append(er.test_case.source_game)

    lines: List[str] = []
    total = sum(signatures.values())
    lines.append(
        f"Total {bucket_label} cases analyzed: {total}"
        + (f" (plus {skipped} without retained details)" if skipped else "")
    )
    lines.append("")
    if total == 0:
        lines.append(f"_No {bucket_label} cases to cluster._")
        return lines

    lines.append(f"### Top {top_n} {bucket_label} clusters by {sig_label} signature")
    lines.append("")
    lines.append("| Count | Pct | Signature | Examples (game IDs) |")
    lines.append("|------:|----:|-----------|---------------------|")
    for sig, count in signatures.most_common(top_n):
        pct = 100.0 * count / total
        exs = ", ".join(examples[sig])
        lines.append(f"| {count} | {pct:.1f}% | `{sig}` | {exs} |")
    return lines


def run_tests(
    jsonl_file: TextIO,
    max_games: int | None = None,
    with_failures: bool = False,
    verbose: bool = False,
    dump_json: bool = False,
    workers: int = 1,
    cluster_failures: bool = False,
    cluster_output_path: str | None = None,
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
        cluster_failures: Group non-PASS cases by order-type signature
            and emit a top-20 cluster report.
        cluster_output_path: If set with cluster_failures, write the
            markdown report to this path.
        output: Output stream (default stdout)
    """
    if dump_json:
        return _dump_json(jsonl_file, max_games, output)

    # cluster_failures needs test_case retained to compute signatures
    keep_details = with_failures or verbose or cluster_failures
    summary = ResultSummary()
    start_time = time.monotonic()
    game_count = 0

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
    print(f"Games: {game_count} | Test cases: {summary.total} | Time: {elapsed:.1f}s{w_info}", file=output)
    print(file=output)
    print(summary.format_summary(), file=output)

    # Print details for non-PASS cases
    if with_failures or verbose:
        print(file=output)
        for er in summary.non_pass:
            if verbose or er.result == TestResult.FAIL:
                print(format_failure(er), file=output)
                print(file=output)

    # Cluster report: group non-PASS by order signature
    if cluster_failures:
        report_lines = _build_cluster_markdown(summary)
        for line in report_lines:
            print(line, file=output)
        if cluster_output_path:
            try:
                with open(cluster_output_path, "w") as f:
                    f.write("\n".join(report_lines))
                    f.write("\n")
                print(
                    f"\nCluster report written to: {cluster_output_path}",
                    file=sys.stderr,
                )
            except OSError as e:
                print(
                    f"\nWarning: could not write {cluster_output_path}: {e}",
                    file=sys.stderr,
                )

    return summary


def _build_cluster_markdown(summary: ResultSummary) -> List[str]:
    """Build the markdown report describing failure clusters."""
    fail = [er for er in summary.non_pass if er.result == TestResult.FAIL]
    void = [er for er in summary.non_pass if er.result == TestResult.INCONCLUSIVE and er.reason == "void"]
    convoy = [er for er in summary.non_pass if er.result == TestResult.INCONCLUSIVE and er.reason == "convoy"]
    error = [er for er in summary.non_pass if er.result == TestResult.ERROR]

    lines: List[str] = []
    lines.append("# DipNet Failure Clusters")
    lines.append("")
    lines.append("Generated by `run_dipnet_tests.py --cluster-failures`.")
    lines.append("")
    lines.append("## Result distribution")
    lines.append("")
    lines.append(f"- Total test cases: **{summary.total}**")
    lines.append(f"- PASS: {summary.passed}")
    lines.append(f"- FAIL: {summary.failed}")
    lines.append(f"- ERROR: {summary.errors}")
    lines.append(
        f"- INCONCLUSIVE: {summary.inconclusive} "
        f"(convoy {summary.inconclusive_convoy}, void {summary.inconclusive_void})"
    )
    lines.append("")

    lines.append("## FAIL clusters")
    lines.append("")
    lines.extend(_cluster_report(fail, "FAIL"))
    lines.append("")

    lines.append("## ERROR clusters")
    lines.append("")
    lines.extend(_cluster_report(error, "ERROR"))
    lines.append("")

    # Legacy sections: convoys are now adjudicated through geography and no
    # longer parked as INCONCLUSIVE, so these buckets are empty. Kept for
    # output-format stability.
    lines.append("## INCONCLUSIVE (convoy) clusters — legacy, now empty")
    lines.append("")
    lines.extend(_cluster_report(convoy, "convoy-inconclusive"))
    lines.append("")

    lines.append("## INCONCLUSIVE (void) clusters — by full-case signature")
    lines.append("")
    lines.extend(_cluster_report(void, "void-inconclusive"))
    lines.append("")

    lines.append("## INCONCLUSIVE (void) clusters — by void-order-only signature")
    lines.append("")
    lines.append(
        "Each cluster groups cases by the order types the dataset marked "
        "specifically as `void`. Much more actionable than the full-case "
        "signature above."
    )
    lines.append("")
    lines.extend(
        _cluster_report(
            void,
            "void-inconclusive",
            sig_fn=_void_order_signature,
            sig_label="void-order",
        )
    )
    lines.append("")
    return lines


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
        f"\r  Processing: {summary.total} tests (+:{summary.passed} -:{summary.failed} ?:{summary.inconclusive})...",
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
        help="Print full situation for all non-PASS cases (FAIL + ERROR)",
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
    parser.add_argument(
        "--cluster-failures",
        action="store_true",
        help="Group non-PASS cases by order-type signature and dump top-20 clusters",
    )
    parser.add_argument(
        "--cluster-out",
        default="doc/DIPNET_CLUSTERS.md",
        help="Path to write the cluster report markdown (default: doc/DIPNET_CLUSTERS.md). "
        "Set to empty string to skip file write.",
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
                cluster_failures=args.cluster_failures,
                cluster_output_path=(args.cluster_out or None) if args.cluster_failures else None,
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
