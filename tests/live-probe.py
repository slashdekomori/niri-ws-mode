#!/usr/bin/env python3
"""Live smoke test. Needs a running niri session and Alacritty.

Opens four throwaway Alacritty windows on the focused workspace, floats them
with the real code path, checks the sizes and placement, tiles them again,
floats them once more, and closes them. It only touches the windows it opens,
but it does flash them on the focused workspace.

    python3 tests/live-probe.py
"""

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import time

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "bin", "niri-ws-mode")
loader = importlib.machinery.SourceFileLoader("niri_ws_mode", SCRIPT)
spec = importlib.util.spec_from_loader("niri_ws_mode", loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)

PREFIX = "wsmode-probe"
failures = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        failures.append(what)


def probes():
    found = [w for w in m.niri_json("windows") if w["title"].startswith(PREFIX)]
    return sorted(found, key=m.tiled_order)


def rect(w):
    x, y = w["layout"]["tile_pos_in_workspace_view"]
    return (x, y, *w["layout"]["tile_size"])


def float_all(ws):
    movers = [(w["id"], m.to_floating(w)) for w in probes()]
    m.arrange(ws, movers)
    m.settle(ws, movers)
    return movers


def main():
    for i in range(4):
        subprocess.run(["niri", "msg", "action", "spawn", "--", "alacritty", "--title", f"{PREFIX}{i}"])
        time.sleep(0.7)
    time.sleep(1)
    try:
        wins = probes()
        check(len(wins) == 4, "4 probe windows opened")
        ws = wins[0]["workspace_id"]
        tiled = [tuple(w["layout"]["tile_size"]) for w in wins]

        float_all(ws)
        floated = probes()
        sizes = [tuple(w["layout"]["tile_size"]) for w in floated]
        expect = [tuple(max(1, int(v * m.FLOAT_SCALE)) for v in t) for t in tiled]
        check(all(w["is_floating"] for w in floated), "all windows are floating")
        check(sorted(sizes) == sorted(expect), f"sizes are FLOAT_SCALE ({m.FLOAT_SCALE}) of tiled")
        rects = [rect(w) for w in floated]
        pairs = [(a, b) for i, a in enumerate(rects) for b in rects[i + 1 :]]
        check(
            sum(1 for a, b in pairs if m.overlap(a, b)) < len(pairs),
            "placement does not stack every window on top of the others",
        )

        for w in probes():
            m.to_tiling(w)
        time.sleep(0.5)
        back = [tuple(w["layout"]["tile_size"]) for w in probes()]
        check(sorted(back) == sorted(tiled), "tiled sizes restored after tiling")
        check(not m.load_state()["tiled"].keys() & {str(w["id"]) for w in probes()}, "saved sizes cleaned up")

        float_all(ws)
        again = sorted(tuple(w["layout"]["tile_size"]) for w in probes())
        check(again == sorted(expect), "second float gives the same sizes (no shrinking)")
    finally:
        for w in probes():
            m.action("close-window", win=w["id"])
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
