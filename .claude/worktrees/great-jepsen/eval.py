"""
Evaluation script: run the agent on a dataset of (url, task) and report metrics.
Usage:
  python eval.py --dataset eval_dataset.json
  python eval.py --dataset eval_dataset.json --output eval_report.md

Dataset format (JSON):
  [
    {"url": "https://...", "task": "Summarize the page", "expected_keywords": ["python", "backend"]},
    ...
  ]
  Optional: "expected_keywords" (list) — partial success if any appear in answer.
  Optional: "expected_summary_length_min": 100 — fail if answer shorter.
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


def score_run(expected: dict, answer: str | None, metrics: dict) -> dict:
    """Compute per-run score: success (bool), partial (bool), note (str)."""
    if not answer:
        return {"success": False, "partial": False, "note": "no answer"}
    keywords = expected.get("expected_keywords") or []
    min_len = expected.get("expected_summary_length_min") or 0
    if min_len and len(answer) < min_len:
        return {"success": False, "partial": False, "note": f"answer too short ({len(answer)} < {min_len})"}
    if not keywords:
        return {"success": True, "partial": False, "note": "no criteria"}
    found = [k for k in keywords if k.lower() in answer.lower()]
    if len(found) == len(keywords):
        return {"success": True, "partial": False, "note": f"all keywords found: {found}"}
    if found:
        return {"success": False, "partial": True, "note": f"partial: {found} of {keywords}"}
    return {"success": False, "partial": False, "note": f"no keywords found; expected any of {keywords}"}


async def run_eval(dataset_path: str, output_path: str | None, max_steps: int = 8):
    if not os.environ.get("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY not set; cannot run agent.")
        return
    dataset = load_dataset(dataset_path)
    results = []
    for i, row in enumerate(dataset):
        url = row.get("url", "")
        task = row.get("task", "")
        if not url or not task:
            results.append({"url": url, "task": task, "error": "missing url or task", "score": {}})
            continue
        print(f"[{i+1}/{len(dataset)}] {url[:50]}... | {task[:40]}...")
        async with BrowserController(headless=True) as browser:
            out = await run_agent(browser, task=task, url=url, max_steps=max_steps)
        answer = out.get("answer")
        metrics = out.get("metrics", {})
        score = score_run(row, answer or "", metrics)
        results.append({
            "url": url,
            "task": task,
            "ok": out.get("ok"),
            "answer_preview": (answer or "")[:200],
            "metrics": metrics,
            "score": score,
        })
        print(f"  -> ok={out.get('ok')} steps={metrics.get('steps_used')} success={score.get('success')}")

    # Summary
    n_ok = sum(1 for r in results if r.get("ok"))
    n_success = sum(1 for r in results if r.get("score", {}).get("success"))
    n_partial = sum(1 for r in results if r.get("score", {}).get("partial"))
    avg_steps = 0
    if results:
        steps_list = [r.get("metrics", {}).get("steps_used", 0) for r in results]
        avg_steps = sum(steps_list) / len(steps_list)
    summary = {
        "total": len(dataset),
        "agent_ok": n_ok,
        "task_success": n_success,
        "partial": n_partial,
        "avg_steps": round(avg_steps, 1),
        "results": results,
    }

    if output_path:
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Wrote {output_path}")

    # Markdown report
    if output_path and output_path.endswith(".json"):
        md_path = output_path.replace(".json", ".md")
    else:
        md_path = (output_path or "eval_report") + ("" if (output_path or "").endswith(".md") else ".md")
    if not md_path.endswith(".md"):
        md_path = "eval_report.md"
    with open(md_path, "w") as f:
        f.write("# Eval Report\n\n")
        f.write(f"- Total: {summary['total']} | Agent OK: {n_ok} | Task success: {n_success} | Partial: {n_partial} | Avg steps: {avg_steps}\n\n")
        f.write("| URL | Task | OK | Steps | Success | Note |\n")
        f.write("|-----|------|-----|-------|--------|------|\n")
        for r in results:
            u = (r.get("url") or "")[:40]
            t = (r.get("task") or "")[:30]
            ok = r.get("ok", False)
            steps = r.get("metrics", {}).get("steps_used", "")
            sc = r.get("score", {})
            success = sc.get("success", False)
            note = (sc.get("note") or "")[:40]
            f.write(f"| {u} | {t} | {ok} | {steps} | {success} | {note} |\n")
    print(f"Wrote {md_path}")
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="eval_dataset.json", help="JSON dataset path")
    p.add_argument("--output", default=None, help="Output JSON report path")
    p.add_argument("--max-steps", type=int, default=8)
    args = p.parse_args()
    asyncio.run(run_eval(args.dataset, args.output, args.max_steps))


if __name__ == "__main__":
    main()
