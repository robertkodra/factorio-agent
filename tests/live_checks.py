"""Integration checks against the completed first-belts test world. Mutates it."""
import json
import time
from pathlib import Path

from client.agent import Agent, AgentError, ROOT


def check_rejected(agent, text, **request):
    try:
        agent.request(**request)
    except AgentError as error:
        assert text in str(error), str(error)
        return str(error)
    raise AssertionError("Expected rejection: " + text)


def run():
    report = {}
    suffix = str(time.time_ns())
    with Agent() as agent:
        report["before"] = agent.request("observe")
        agent.request("pause", value=False)
        job = dict(id="cancel-" + suffix, actions=[dict(type="walk", x=-45, y=-47, timeout=1200)])
        report["submitted"] = agent.request("submit", **job)
        report["duplicate"] = agent.request("submit", **job)
        reordered = json.loads(json.dumps(job, sort_keys=True))
        report["reordered_duplicate"] = agent.request("submit", **reordered)
        report["conflict"] = check_rejected(agent, "id_conflict", op="submit", id=job["id"], actions=[dict(type="wait_ticks", ticks=2)])
        report["busy"] = check_rejected(agent, "busy", op="submit", id="busy-"+suffix, actions=[dict(type="wait_ticks", ticks=1)])
        time.sleep(.5)
        report["cancelled"] = agent.request("cancel", id=job["id"])
        assert report["cancelled"]["status"] == "cancelled"
        stopped = agent.request("observe")
        time.sleep(.3)
        after = agent.request("observe")
        assert stopped["position"] == after["position"], (stopped, after)
        assert not after["walking"]["walking"] and not after["mining"]
        report["stopped_position"] = after["position"]
        report["unknown_id"] = check_rejected(agent, "unknown_job_id", op="status", id="missing-"+suffix)
        report["invalid_batch"] = check_rejected(agent, "invalid_action", op="submit", id="bad-"+suffix, actions=[dict(type="walk",x=0,y=0),dict(type="teleport",x=0,y=0)])
        assert agent.request("observe")["position"] == after["position"]
        # Retrieve the actual starter furnace, then reject a distant build while
        # verifying that its inventory item is preserved, and place it back.
        report["retrieve_furnace"] = agent.run(dict(id="retrieve-"+suffix, actions=[dict(type="walk",x=-70,y=-47),dict(type="mine",x=-72,y=-45,entity="stone-furnace",item="stone-furnace",count=1)]))
        assert report["retrieve_furnace"]["status"] == "complete", report["retrieve_furnace"]
        before = agent.request("observe")["inventory"]
        report["far_build"] = agent.run(dict(id="far-"+suffix, actions=[dict(type="place",x=100,y=100,entity="stone-furnace")]))
        assert report["far_build"]["status"] == "failed", report["far_build"]
        assert "placement_rejected" in report["far_build"]["error"]
        assert agent.request("observe")["inventory"] == before
        report["restore_furnace"] = agent.run(dict(id="restore-"+suffix, actions=[dict(type="place",x=-72,y=-45,entity="stone-furnace")]))
        assert report["restore_furnace"]["status"] == "complete"
        report["after"] = agent.request("observe")
        report["pass"] = True
    (ROOT / "runtime").mkdir(mode=0o700, exist_ok=True)
    (ROOT / "runtime/live-checks.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
