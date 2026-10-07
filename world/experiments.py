#!/usr/bin/env python3
"""Run a condition across many seeds and report robust summaries.

  python experiments.py compare --ticks 6000 --seeds 6 \
      --cond crowded:food_cap=6,initial_population=200 --cond sparse:food_cap=10,regrow=0.5

A condition is NAME:field=value,field=value (starting from the default config).
"""
import argparse
import dataclasses
import statistics as st
from multiprocessing import Pool

from sim.config import Config
from sim.runner import simulate
from sim import analysis as A


def coerce(cfg, k, v):
    fields = {f.name for f in dataclasses.fields(Config)}
    if k not in fields:
        raise SystemExit(f"unknown config field: {k}")
    cur = getattr(cfg, k)
    if isinstance(cur, bool):
        return v.lower() in ("1", "true", "yes")
    return type(cur)(v)


def make_cfg(overrides, seed):
    cfg = Config(seed=seed)
    return cfg.with_(**{k: coerce(cfg, k, v) if isinstance(v, str) else v for k, v in overrides.items()})


def tail_mean(history, field, frac=0.25):
    rows = history[int(len(history) * (1 - frac)):] or history
    return sum(r[field] for r in rows) / len(rows) if rows else float("nan")


def one_run(args):
    overrides, seed, ticks = args
    cfg = make_cfg(overrides, seed)
    m = simulate(cfg, ticks, keep_events=True, report_every=0, out=lambda *_: None)
    ev = m.log.events
    h = m.history
    mem = A.does_memory_change_outcomes(ev)
    dom = A.dominance_vs_chance(ev)
    aggs = [c.genes.aggression for c in m.by_id.values()]
    rel = A.relationship_summary(ev)
    return {
        "seed": seed, "extinct": not m.by_id, "pop": tail_mean(h, "pop") if h else 0,
        "memory": tail_mean(h, "memory") if h else 0, "aggression": tail_mean(h, "aggression") if h else 0,
        "aggression_sd": tail_mean(h, "aggression_sd") if h else 0,
        "size": tail_mean(h, "size") if h else 0, "perception": tail_mean(h, "perception") if h else 0,
        "mem_series": [r["memory"] for r in h],
        "contests_per_tick": len(A.contests(ev)) / max(1, m.tick),
        "fight_frac": sum(1 for e in A.contests(ev) if e["outcome"].startswith("fight")) / max(1, len(A.contests(ev))),
        "knew_frac": A.repeat_encounter_stats(ev)["attacker_knew_defender_fraction"],
        "belief_corr": A.belief_accuracy(ev),
        "dominance_pairs": rel["dominance_pairs"], "pairs_with_history": rel["pairs_with_history"],
        "fit_memory": A.fitness_correlation(ev, "memory", min_age=50),
        "fit_aggression": A.fitness_correlation(ev, "aggression", min_age=50),
        "fit_size": A.fitness_correlation(ev, "size", min_age=50),
        "backdown_frac": sum(1 for e in A.contests(ev) if e["outcome"] == "backdown") / max(1, len(A.contests(ev))),
        "births_per_tick": m.log.counts.get("birth", 0) / max(1, m.tick),
        "mean_energy": tail_mean(h, "mean_energy") if h else 0,
        "dom_observed": dom["observed_dominance"], "dom_expected": dom["expected_by_chance"],
        "bimodality": A.bimodality(aggs), "agg_hist": A.aggression_histogram(m.by_id.values()),
        "fight_death_frac": A.death_causes(ev).get("fight", 0) / max(1, sum(A.death_causes(ev).values())),
        "starve_death_frac": A.death_causes(ev).get("starvation", 0) / max(1, sum(A.death_causes(ev).values())),
        "min_pop": min((r["pop"] for r in h[len(h) // 5:]), default=0),
        "max_generation": max((e["generation"] for e in ev if e["kind"] == "birth"), default=0),
        "yield_knew": mem.get("knew", {}).get("yield"), "yield_stranger": mem.get("stranger", {}).get("yield"),
    }


def run_condition(overrides, seeds, ticks, procs=4):
    jobs = [(overrides, s, ticks) for s in seeds]
    with Pool(min(procs, len(jobs))) as pool:
        return pool.map(one_run, jobs)


def fmt(vals, nd=2):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "   n/a"
    return f"{st.mean(vals):6.{nd}f}±{(st.pstdev(vals) if len(vals) > 1 else 0):.{nd}f}"


def summarize(name, runs):
    print(f"\n== {name}  ({len(runs)} seeds, extinct: {sum(r['extinct'] for r in runs)})")
    for label, key, nd in [("population", "pop", 0), ("memory slots", "memory", 2), ("aggression", "aggression", 2),
                           ("aggression sd", "aggression_sd", 2), ("size", "size", 2), ("perception", "perception", 2),
                           ("contests/tick", "contests_per_tick", 2), ("fight fraction", "fight_frac", 3),
                           ("attacker knew defender", "knew_frac", 3), ("belief~truth corr", "belief_corr", 2),
                           ("yield|knew", "yield_knew", 3), ("yield|stranger", "yield_stranger", 3),
                           ("dominance pairs", "dominance_pairs", 1),
                           ("fitness corr: memory", "fit_memory", 3), ("fitness corr: aggression", "fit_aggression", 3),
                           ("fitness corr: size", "fit_size", 3),
                           ("backdown fraction", "backdown_frac", 3), ("births/tick", "births_per_tick", 3),
                           ("mean energy", "mean_energy", 2),
                           ("dominance pairs observed", "dom_observed", 1), ("  ...expected by chance", "dom_expected", 1),
                           ("aggression bimodality", "bimodality", 2),
                           ("deaths by fighting", "fight_death_frac", 3), ("deaths by starvation", "starve_death_frac", 3),
                           ("min population", "min_pop", 0), ("generations", "max_generation", 0)]:
        print(f"  {label:<24}{fmt([r[key] for r in runs], nd)}   per-seed: "
              + " ".join(f"{r[key]:.2f}" if isinstance(r[key], float) else str(r[key]) for r in runs))


def parse_cond(text):
    from sim.config import PRESETS
    name, _, rest = text.partition(":")
    ov = {}
    if name in PRESETS:
        ov.update({k: v for k, v in PRESETS[name].items()})
    for item in filter(None, rest.split(",")):
        k, v = item.split("=", 1)
        ov[k] = v
    return name, ov


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["compare"])
    ap.add_argument("--ticks", type=int, default=6000)
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--first-seed", type=int, default=100)
    ap.add_argument("--cond", action="append", default=[], metavar="NAME:field=v,...")
    a = ap.parse_args()
    for text in a.cond or ["default:"]:
        name, ov = parse_cond(text)
        summarize(name, run_condition(ov, range(a.first_seed, a.first_seed + a.seeds), a.ticks))


if __name__ == "__main__":
    main()
