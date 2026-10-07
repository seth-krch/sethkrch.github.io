"""What the browser page calls. Every function takes and returns plain strings or
JSON so it is easy to call from JavaScript, and it works the same under normal
Python (that is how it is tested)."""
import contextlib
import io
import json
import re

import explain
from sim.config import PRESETS
from sim.events import EventLog
from sim.model import WorldModel
from sim.runner import HEADER, format_census
from sim.settings import STAGES, build_config, describe_fields
from sim import analysis as A

MAX_TICKS = 6000
_s = {}


def options():
    """Everything the page needs to draw its controls."""
    return json.dumps({"presets": list(PRESETS), "stages": sorted(STAGES), "fields": describe_fields(),
                       "max_ticks": MAX_TICKS})


def _capture(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args)
    return buf.getvalue().rstrip()


def start(params_json):
    """Begin a run. params: preset, stage, seed, ticks, report_every, map_every, overrides (text)."""
    p = json.loads(params_json)
    sets = [t for t in re.split(r"[\s,]+", p.get("overrides", "")) if t]
    try:
        cfg = build_config(p.get("preset", "crowded"), int(p.get("stage", 4)), int(p.get("seed", 1)), sets)
        ticks = max(1, min(int(p.get("ticks", 800)), MAX_TICKS))
        report_every = max(1, int(p.get("report_every", 100)))
        map_every = max(0, int(p.get("map_every", 0)))
    except (ValueError, TypeError) as e:
        return json.dumps({"error": str(e)})
    log = EventLog(keep=True)
    model = WorldModel(cfg, log)
    _s.clear()
    _s.update(model=model, ticks=ticks, report_every=report_every, map_every=map_every, ended=False)
    return json.dumps({"header": HEADER, "ticks": ticks, "population": len(model.by_id),
                       "cells": int((model.cap > 0).sum())})


def advance(n):
    """Run up to n more ticks; return the new report lines and whether the run is over."""
    m = _s["model"]
    lines = []
    for _ in range(int(n)):
        if m.tick >= _s["ticks"] or not m.by_id:
            break
        m.step()
        if m.tick % _s["report_every"] == 0:
            if not m.history or m.history[-1]["tick"] != m.tick:
                m._census()
            lines.append(format_census(m.history[-1]))
        if _s["map_every"] and m.tick % _s["map_every"] == 0:
            lines.append(f"--- map at tick {m.tick} ---\n{m.render()}")
        if not m.by_id:
            lines.append(f"*** extinct at tick {m.tick} ***")
    done = m.tick >= _s["ticks"] or not m.by_id
    return json.dumps({"tick": m.tick, "population": len(m.by_id), "lines": lines, "done": done})


def final_map():
    m = _s["model"]
    return f"--- map at tick {m.tick} (digits are aggression 0-9, shading is food) ---\n{m.render()}"


def summary():
    return _capture(explain.cmd_summary, _s["model"].log.events)


def explain_cmd(text):
    """Run a command from the explain console, e.g. 'rivals 10' or 'rivalry 596 669'."""
    if "model" not in _s:
        return "Run a world first."
    ev = _s["model"].log.events
    parts = text.strip().split()
    if not parts or parts[0] in ("help", "?"):
        return ("commands:\n  summary\n  rivals [N]        most-repeated pairings\n"
                "  rivalry A B       every meeting between two creatures\n  contest EID       one contest, step by step\n"
                "  life ID           one creature's history\n  ancestry ID       ancestors and descendant count")
    cmd, args = parts[0], parts[1:]
    try:
        if cmd == "summary":
            return _capture(explain.cmd_summary, ev)
        if cmd == "rivals":
            return _capture(explain.cmd_rivals, ev, int(args[0]) if args else 15) or "no repeated pairings yet"
        if cmd == "rivalry":
            return _capture(explain.cmd_rivalry, ev, int(args[0]), int(args[1]))
        if cmd == "life":
            return _capture(explain.cmd_life, ev, int(args[0]))
        if cmd == "ancestry":
            return _capture(explain.cmd_ancestry, ev, int(args[0]))
        if cmd == "contest":
            e = next((e for e in ev if e["kind"] == "contest" and e["eid"] == int(args[0])), None)
            return explain.explain_contest(e) if e else "no contest with that event id"
    except (IndexError, ValueError):
        return f"usage problem with '{text}'. Type help."
    except SystemExit as e:  # explain.py exits on unknown ids
        return str(e)
    return f"unknown command '{cmd}'. Type help."


def log_jsonl():
    return "\n".join(json.dumps(e, separators=(",", ":")) for e in _s["model"].log.events)
