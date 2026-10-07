#!/usr/bin/env python3
"""Run the Phase 1 world from the terminal.

  python run.py --ticks 3000 --report-every 100
  python run.py --ticks 2000 --set food_cap=6 --set initial_population=200 --log runs/a.jsonl
  python run.py --stage 1       # energy economy only (no genes/contests/memory)
"""
import argparse
from sim.config import PRESETS
from sim.settings import STAGES, build_config
from sim.runner import simulate


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticks", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--preset", choices=PRESETS, default="crowded",
                    help="crowded (default), spread (scattered small patches), sparse (capped population)")
    ap.add_argument("--stage", type=int, choices=STAGES, default=4)
    ap.add_argument("--report-every", type=int, default=100)
    ap.add_argument("--map-every", type=int, default=0)
    ap.add_argument("--log", default=None, help="write the full event log (JSON lines) here")
    ap.add_argument("--set", action="append", default=[], metavar="FIELD=VALUE")
    a = ap.parse_args()
    try:
        cfg = build_config(a.preset, a.stage, a.seed, a.set)
    except ValueError as e:
        raise SystemExit(str(e))
    m = simulate(cfg, a.ticks, log_path=a.log, report_every=a.report_every, map_every=a.map_every)
    print(f"done: {m.tick} ticks, population {len(m.by_id)}, {m.log.next_id} events, {m.wall_seconds:.1f}s")


if __name__ == "__main__":
    main()
