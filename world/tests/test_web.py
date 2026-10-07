"""The browser page runs the same simulation under Pyodide with a tiny Mesa stand-in.
These tests keep that path honest."""
import ast
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "web"))
import bridge  # noqa: E402

SCRIPT = """
import sys, json, hashlib
sys.path.insert(0, {root!r}); sys.path.insert(0, {root!r} + '/web')
if {shim!r}:
    import mesa_shim
    sys.modules['mesa'] = mesa_shim
from sim.config import Config
from sim.events import EventLog
from sim.model import WorldModel
m = WorldModel(Config(seed=9), EventLog()); m.run(400)
print(hashlib.sha256(json.dumps(m.log.events, sort_keys=True).encode()).hexdigest(), len(m.log.events))
"""


def run_hash(shim):
    out = subprocess.run([sys.executable, "-W", "ignore", "-c", SCRIPT.format(root=ROOT, shim=shim)],
                         capture_output=True, text=True, check=True).stdout.split()
    return out[0], int(out[1])


def test_shim_and_real_mesa_produce_identical_event_logs():
    real, n = run_hash(False)
    shim, m = run_hash(True)
    assert n > 1000 and (real, n) == (shim, m)


def test_simulation_only_imports_what_the_browser_has():
    """Pyodide has numpy and the standard library; Mesa is only allowed in model.py (and is shimmed)."""
    stdlib = set(sys.stdlib_module_names)
    for name in os.listdir(os.path.join(ROOT, "sim")):
        if not name.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(ROOT, "sim", name)).read())
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                ok = mod in stdlib or mod in ("numpy", "sim") or (mod == "mesa" and name == "model.py")
                assert ok, f"sim/{name} imports {mod}, which the browser page cannot load"


def test_bridge_run_explain_and_log_round_trip():
    info = json.loads(bridge.start(json.dumps({"ticks": 250, "report_every": 100, "seed": 3})))
    assert info["ticks"] == 250 and info["population"] > 0
    lines, done = [], False
    while not done:
        r = json.loads(bridge.advance(40))
        lines += r["lines"]
        done = r["done"]
    assert r["tick"] == 250 and len(lines) == 2
    assert "rivals" in bridge.explain_cmd("help")
    assert "meetings" in bridge.explain_cmd("rivals 1") or "no repeated" in bridge.explain_cmd("rivals 1")
    assert "never contested" in bridge.explain_cmd("rivalry 1 2") or "met" in bridge.explain_cmd("rivalry 1 2")
    assert "last census" in bridge.summary()
    assert "digits are aggression" in bridge.final_map()
    events = [json.loads(line) for line in bridge.log_jsonl().splitlines()]
    assert events[0]["kind"] == "world" and all(e["eid"] == i for i, e in enumerate(events))


def test_bridge_rejects_bad_input_without_crashing():
    assert "unknown setting" in json.loads(bridge.start(json.dumps({"overrides": "nope=1"})))["error"]
    assert "bad value" in json.loads(bridge.start(json.dumps({"overrides": "food_cap=lots"})))["error"]
    assert "preset" in json.loads(bridge.start(json.dumps({"preset": "moon"})))["error"]
    bridge.start(json.dumps({"ticks": 50}))
    assert "usage problem" in bridge.explain_cmd("life")
    assert "unknown command" in bridge.explain_cmd("dance")


def test_bridge_clamps_ticks_and_applies_overrides():
    info = json.loads(bridge.start(json.dumps({"ticks": 10 ** 9, "overrides": "initial_population=7 food_cap=5"})))
    assert info["ticks"] == bridge.MAX_TICKS and info["population"] == 7


def test_ablation_switch_reaches_the_simulation():
    from sim.settings import build_config
    assert build_config(sets=["memory_has_effect=false"]).memory_has_effect is False
    assert build_config(sets=["init_memory_range=1,3"]).init_memory_range == (1, 3)
