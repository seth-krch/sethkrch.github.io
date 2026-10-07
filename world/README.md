# Persistent World — Phase 1

A text-only agent-based simulation: creatures eat, spend energy, reproduce with
mutation, contest food spots, and remember each other. Design and rationale are
in [PHASE1_DESIGN.md](PHASE1_DESIGN.md); findings are in [PHASE1_RESULTS.md](PHASE1_RESULTS.md).

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Run a world

```bash
python run.py --ticks 3000 --report-every 100                # full model (stage 4)
python run.py --stage 1 --ticks 300 --map-every 100          # energy economy only, with an ASCII map
python run.py --ticks 4000 --log runs/a.jsonl                # also write the full event log
python run.py --set n_patches=2 --set food_cap=40 --set regrow=1.0   # override any Config field
```

Stages (each adds one system on top of the previous): 1 world + energy,
2 genes + reproduction, 3 contests, 4 memory.

The ASCII map shows creatures as a digit (their aggression decile, 0–9) and food
as shading (` .:*#`, empty to full).

## In the browser

`index.html` runs the same Python in the browser (Pyodide, in a web worker), so it
works from a phone. Served by GitHub Pages it lives at `sethkrch.com/world/`. To try
it locally from the repository root: `python3 -m http.server 8000`, then open
`http://127.0.0.1:8000/world/`.

It fetches the Python files from this folder, so the page always runs exactly the
code in the repository. Real Mesa also needs pandas and scipy, which are heavy for a
phone, so the page swaps in `web/mesa_shim.py` (a small stand-in for the two Mesa
classes the simulation uses). `tests/test_web.py` proves runs under the shim and
under real Mesa give identical event logs, and that the simulation imports nothing the
browser cannot load. After changing any Python file, bump `BUILD` in `index.html` so
browsers re-fetch it.

## Ask "why did that happen?"

Every run can write an append-only JSON-lines event log (births, deaths,
contests with the scores and beliefs behind each decision, memory updates).

```bash
python explain.py runs/a.jsonl summary
python explain.py runs/a.jsonl rivals 10          # most-repeated pairings
python explain.py runs/a.jsonl rivalry 596 669    # every meeting between two creatures, explained
python explain.py runs/a.jsonl contest 7952       # one contest, step by step
python explain.py runs/a.jsonl life 596           # one creature's whole history
python explain.py runs/a.jsonl ancestry 596
```

## Experiments

Compare conditions across seeds (runs in parallel):

```bash
python experiments.py compare --ticks 5000 --seeds 4 \
    --cond "crowded:n_patches=2,patch_radius=3,food_cap=40,regrow=1.0" \
    --cond "sparse:n_patches=0,food_cap=10,regrow=0.5,initial_population=60"
```

`memory_has_effect=false` is the ablation switch: creatures still pay for memory
but ignore it, which isolates what memory is actually worth.

## Tests

```bash
python -m pytest -q
```

## Layout

| Path | Purpose |
|---|---|
| `sim/config.py` | every tunable parameter |
| `sim/genes.py`, `sim/memory.py`, `sim/decision.py` | framework-independent logic (no Mesa) |
| `sim/model.py` | Mesa `Model`/`Agent` glue: grid, food, creatures, contests |
| `sim/events.py` | append-only event log |
| `sim/analysis.py` | questions answered from the log (relationships, selection, memory value) |
| `sim/settings.py` | presets, stages and `FIELD=VALUE` overrides, shared by the command line and the page |
| `run.py`, `explain.py`, `experiments.py` | command-line tools |
| `index.html`, `worker.js`, `web/` | the browser page: UI, Pyodide worker, Mesa stand-in, and the bridge the page calls |
