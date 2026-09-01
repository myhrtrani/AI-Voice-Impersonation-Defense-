#!/usr/bin/env python
"""
Command-Line Log & Crash Viewer for Voice Impersonation Defense.

Usage:
    python view_logs.py                   # Shows overview & last 20 lines of all logs
    python view_logs.py --errors          # Shows only error.log (crashes & tracebacks)
    python view_logs.py --analysis        # Shows only analysis.log (audio risk metrics)
    python view_logs.py --app             # Shows only app.log (general server logs)
    python view_logs.py --tail            # Continuously follows/tails live logs
    python view_logs.py -n 50             # Shows last 50 lines
"""

import os
import sys
import time
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")

APP_LOG = os.path.join(LOGS_DIR, "app.log")
ERROR_LOG = os.path.join(LOGS_DIR, "error.log")
ANALYSIS_LOG = os.path.join(LOGS_DIR, "analysis.log")


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def display_file(file_path: str, title: str, num_lines: int = 25):
    print_header(title)
    if not os.path.exists(file_path):
        print(f"  [No log file found at: {file_path}]")
        return

    size_kb = os.path.getsize(file_path) / 1024
    print(f"  File: {file_path} (Size: {size_kb:.1f} KB)\n" + "-" * 80)

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            if not lines:
                print("  (Log file is currently empty)")
                return
            for line in lines[-num_lines:]:
                print(line.rstrip())
    except Exception as e:
        print(f"  Error reading log file: {e}")


def tail_file(file_path: str):
    print(f"Streaming live log: {file_path} (Press Ctrl+C to exit)...")
    if not os.path.exists(file_path):
        open(file_path, "w", encoding="utf-8").close()

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        # Go to the end of file
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if line:
                print(line.rstrip())
            else:
                time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="Voice Impersonation Defense Log & Crash Viewer")
    parser.add_argument("--errors", action="store_true", help="View crashes and stack traces (error.log)")
    parser.add_argument("--analysis", action="store_true", help="View audio DSP & ML metrics (analysis.log)")
    parser.add_argument("--app", action="store_true", help="View general application logs (app.log)")
    parser.add_argument("-n", "--lines", type=int, default=25, help="Number of lines to display (default: 25)")
    parser.add_argument("--tail", action="store_true", help="Follow live log updates")

    args = parser.parse_args()

    if args.tail:
        target = ERROR_LOG if args.errors else (ANALYSIS_LOG if args.analysis else APP_LOG)
        try:
            tail_file(target)
        except KeyboardInterrupt:
            print("\nStopped log tail.")
        return

    if args.errors:
        display_file(ERROR_LOG, "CRASH & ERROR LOG (error.log)", args.lines)
    elif args.analysis:
        display_file(ANALYSIS_LOG, "AUDIO RISK & ML ANALYSIS LOG (analysis.log)", args.lines)
    elif args.app:
        display_file(APP_LOG, "APPLICATION LOG (app.log)", args.lines)
    else:
        # Default: show overview of all
        print_header(f"VOICE IMPERSONATION DEFENSE - LOG DIAGNOSTICS ({LOGS_DIR})")
        display_file(ERROR_LOG, "LATEST CRASHES & ERRORS (error.log)", min(args.lines, 15))
        display_file(ANALYSIS_LOG, "LATEST AUDIO RISK ANALYSIS (analysis.log)", min(args.lines, 10))
        display_file(APP_LOG, "LATEST APPLICATION EVENTS (app.log)", min(args.lines, 10))


if __name__ == "__main__":
    main()

