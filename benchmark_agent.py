"""
Benchmark script for crawl reliability metrics.

Usage:
  python benchmark_agent.py --dataset eval_dataset.json --output benchmark_report.json
"""
import argparse
import asyncio
import json
import os
from pathlib import Path

from agent_loop import run_agent
from browser_tools import BrowserController


def load_dataset(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


async def run_benchmark(dataset_path: str, output_path: str | None, max_steps: int = 12):
    if not os.environ.get("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY not set; cannot run benchmark.")
        return

    dataset = load_dataset(dataset_path)
    rows: list[dict] = []
    for i, row in enumerate(dataset):
        url = row.get("url", "")
        task = row.get("task", "")
        if not url or not task:
            continue
        print(f"[{i+1}/{len(dataset)}] {url[:50]}... | {task[:40]}...")
        async with BrowserController(headless=True) as browser:
            out = await run_agent(browser, task=task, url=url, max_steps=max_steps)
        metrics = out.get("metrics", {})
        diag = metrics.get("diagnostics", {}) or {}
        rows.append(
            {
                "url": url,
                "task": task,
                "ok": bool(out.get("ok")),
                "steps_used": int(metrics.get("steps_used", 0) or 0),
                "tools_failed": int(metrics.get("tools_failed", 0) or 0),
                "auto_submit_attempts": int(diag.get("auto_submit_attempts", 0) or 0),
                "auto_submit_success": int(diag.get("auto_submit_success", 0) or 0),
                "auto_submit_retries": int(diag.get("auto_submit_retries", 0) or 0),
                "repeated_action_breaks": int(diag.get("repeated_action_breaks", 0) or 0),
                "forced_state_refreshes": int(diag.get("forced_state_refreshes", 0) or 0),
                "same_state_streak": int(diag.get("same_state_streak", 0) or 0),
            }
        )

    total = len(rows)
    if total == 0:
        print("No runnable rows in dataset.")
        return

    success_count = sum(1 for r in rows if r["ok"])
    total_steps = sum(r["steps_used"] for r in rows)
    total_failures = sum(r["tools_failed"] for r in rows)
    total_auto_submit_attempts = sum(r["auto_submit_attempts"] for r in rows)
    total_auto_submit_success = sum(r["auto_submit_success"] for r in rows)
    total_auto_submit_retries = sum(r["auto_submit_retries"] for r in rows)
    total_repeated_breaks = sum(r["repeated_action_breaks"] for r in rows)
    total_refreshes = sum(r["forced_state_refreshes"] for r in rows)
    stuck_runs = sum(1 for r in rows if r["same_state_streak"] >= 2)

    summary = {
        "total_runs": total,
        "success_rate": round(success_count / total, 3),
        "avg_steps": round(total_steps / total, 2),
        "avg_tool_failures": round(total_failures / total, 2),
        "auto_submit_attempts": total_auto_submit_attempts,
        "auto_submit_success_rate": round(
            (total_auto_submit_success / total_auto_submit_attempts) if total_auto_submit_attempts else 0.0,
            3,
        ),
        "auto_submit_retries": total_auto_submit_retries,
        "repeated_action_break_rate": round(total_repeated_breaks / total, 3),
        "forced_refresh_rate": round(total_refreshes / total, 3),
        "stuck_loop_rate": round(stuck_runs / total, 3),
        "rows": rows,
    }

    if output_path:
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Wrote {output_path}")

    md_path = "benchmark_report.md"
    if output_path:
        p = Path(output_path)
        md_path = str(p.with_suffix(".md"))
    with open(md_path, "w") as f:
        f.write("# Browser Agent Benchmark Report\n\n")
        f.write(f"- Total runs: {summary['total_runs']}\n")
        f.write(f"- Success rate: {summary['success_rate']}\n")
        f.write(f"- Avg steps: {summary['avg_steps']}\n")
        f.write(f"- Avg tool failures: {summary['avg_tool_failures']}\n")
        f.write(f"- Auto-submit attempts: {summary['auto_submit_attempts']}\n")
        f.write(f"- Auto-submit success rate: {summary['auto_submit_success_rate']}\n")
        f.write(f"- Auto-submit retries: {summary['auto_submit_retries']}\n")
        f.write(f"- Repeated-action break rate: {summary['repeated_action_break_rate']}\n")
        f.write(f"- Forced refresh rate: {summary['forced_refresh_rate']}\n")
        f.write(f"- Stuck loop rate: {summary['stuck_loop_rate']}\n\n")
        f.write("| URL | OK | Steps | Fails | AutoSubmit | RepeatedBreaks | Streak |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|\n")
        for row in rows:
            f.write(
                f"| {row['url'][:60]} | {row['ok']} | {row['steps_used']} | {row['tools_failed']} | "
                f"{row['auto_submit_success']}/{row['auto_submit_attempts']} | "
                f"{row['repeated_action_breaks']} | {row['same_state_streak']} |\n"
            )
    print(f"Wrote {md_path}")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="eval_dataset.json", help="JSON dataset path")
    parser.add_argument("--output", default="benchmark_report.json", help="Output JSON report path")
    parser.add_argument("--max-steps", type=int, default=12)
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.dataset, args.output, args.max_steps))


if __name__ == "__main__":
    main()

