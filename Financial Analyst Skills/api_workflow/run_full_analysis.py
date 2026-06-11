from __future__ import annotations

import argparse
from datetime import datetime

from .runner import run_stock_analysis, save_analysis_bundle


def print_progress(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 14-analyst stock workflow.")
    parser.add_argument("user_input", help="股票分析请求，例如：全面分析贵州茅台 600519.SH")
    parser.add_argument("--profile", default="cheap", choices=["cheap", "balanced"])
    parser.add_argument("--collection-mode", default="standard", choices=["fast", "standard", "deep"])
    parser.add_argument("--output", default="", help="可选：保存 JSON 结果的路径")
    args = parser.parse_args()

    result = run_stock_analysis(
        args.user_input,
        profile=args.profile,
        collection_mode=args.collection_mode,
        progress_callback=print_progress,
    )
    if args.output:
        saved_files = save_analysis_bundle(result, args.output)
        if saved_files.get("text_report"):
            print(f"saved text report: {saved_files['text_report']}")
        if saved_files.get("long_report"):
            print(f"saved long report: {saved_files['long_report']}")
        print(f"saved: {saved_files['json']}")
    else:
        import json

        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
