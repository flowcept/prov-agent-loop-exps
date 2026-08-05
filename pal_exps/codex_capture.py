from __future__ import annotations

import argparse
import time
from pathlib import Path


def start_adapter(
    settings_path: str,
    duration_sec: float | None = None,
    replay_wait_sec: float = 2.0,
    campaign_id: str | None = None,
) -> dict:
    import os

    os.environ["FLOWCEPT_SETTINGS_PATH"] = settings_path
    from flowcept import Flowcept

    started = time.perf_counter()
    interrupted = False
    buffer_records = 0
    with Flowcept(interceptors="codex", save_workflow=False, campaign_id=campaign_id) as flowcept:
        if duration_sec is None:
            print("Codex adapter running. Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(2)
                    buffer_records = len(flowcept.get_buffer())
                    print(f"records in buffer: {buffer_records}")
            except KeyboardInterrupt:
                interrupted = True
        else:
            deadline = started + max(duration_sec, replay_wait_sec)
            try:
                while time.perf_counter() < deadline:
                    time.sleep(min(1.0, max(0.0, deadline - time.perf_counter())))
                    buffer_records = len(flowcept.get_buffer())
            except KeyboardInterrupt:
                interrupted = True
                buffer_records = len(flowcept.get_buffer())
    elapsed = time.perf_counter() - started
    print(f"Codex adapter stopped after {elapsed:.3f}s.")
    return {"adapter_buffer_records": buffer_records, "adapter_elapsed_sec": elapsed, "interrupted": interrupted}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Flowcept Codex adapter for online capture or JSONL replay.")
    parser.add_argument("--settings-path", required=True)
    parser.add_argument("--duration-sec", type=float, default=None)
    parser.add_argument("--replay-wait-sec", type=float, default=2.0)
    args = parser.parse_args(argv)
    start_adapter(args.settings_path, args.duration_sec, args.replay_wait_sec)


if __name__ == "__main__":
    main()
