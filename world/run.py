#!/usr/bin/env python3
"""Run the Phase 1 world from the terminal.

  python run.py --ticks 3000 --report-every 100
  python run.py --ticks 2000 --set food_cap=6 --set initial_population=200 --log runs/a.jsonl
  python run.py --stage 1       # energy economy only (no genes/contests/memory)
"""
import argparse
import dataclasses
from sim.config import Config
from sim.runner import simulate

STAGES = {
    1: dict(enable_reproduction=False, enable_contests=False, enable_memory=False),
    2: dict(enable_reproduction=True, enable_contests=False, enable_memory=False),
    3: dict(enable_reproduction=True, enable_contests=True, enable_memory=False),
    4: dict(enable_reproduction=True, enable_contests=True, enable_memory=True),
}


def parse_set(cfg, items):
    fields = {f.name: f for f in dataclasses.fields(Config)}
    kw = {}
    for item in items:
        k, v = item.split("=", 1)
        if k not in fields:
            raise SystemExit(f"unknown config field: {k}")
        cur = getattr(cfg, k)
        kw[k] = (v.lower() in ("1", "true", "yes")) if isinstance(cur, bool) else type(cur)(v)
    return cfg.with_(**kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticks", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--stage", type=int, choices=STAGES, default=4)
    ap.add_argument("--report-every", type=int, default=100)
    ap.add_argument("--map-every", type=int, default=0)
    ap.add_argument("--log", default=None, help="write the full event log (JSON lines) here")
    ap.add_argument("--set", action="append", default=[], metavar="FIELD=VALUE")
    a = ap.parse_args()
    cfg = parse_set(Config(seed=a.seed, **STAGES[a.stage]), a.set)
    m = simulate(cfg, a.ticks, log_path=a.log, report_every=a.report_every, map_every=a.map_every)
    print(f"done: {m.tick} ticks, population {len(m.by_id)}, {m.log.next_id} events, {m.wall_seconds:.1f}s")


if __name__ == "__main__":
    main()
