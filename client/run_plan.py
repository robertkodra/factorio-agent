"""Submit a saved plan once and report changes while Factorio executes it."""
import argparse
import json
import time
from pathlib import Path

from .agent import Agent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--id", help="New job ID for an intentional new execution")
    parser.add_argument("--deadline", type=float, default=300)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if args.id:
        plan["id"] = args.id
    with Agent() as agent:
        started = time.perf_counter()
        status = agent.request("submit", **plan)
        print(json.dumps(dict(accepted=status, submit_ms=(time.perf_counter()-started)*1000)), flush=True)
        previous = None
        while time.perf_counter()-started < args.deadline:
            status = agent.request("status", id=plan["id"])
            marker = (status["status"], status.get("index"))
            if marker != previous:
                print(json.dumps(status), flush=True)
                previous = marker
            if status["status"] != "running":
                return 0 if status["status"] == "complete" else 1
            time.sleep(.5)
    print("Wait deadline reached. Job continues in Factorio; inspect status or cancel explicitly.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
