# Phase 1 Results

What we built, what we measured, and what we learned. Numbers are mean ± sd
across seeds; every table can be regenerated with `experiments.py` (commands
at the end). Constants such as costs and rates were chosen by us and results
depend on them, so treat "robust across seeds" as weaker than "true in general".

## Summary

- The world works and is inspectable. Population persists, evolves, and every
  contest leaves a record that can be explained in words.
- **Environment drives evolution, and it does so consistently.** Crowded
  colonies on rich food patches evolve an arms race (big, aggressive, almost
  nobody yields; about a quarter of deaths are fights). Scattered food evolves
  small, mild creatures that rarely fight. All seeds agree.
- **Memory works as a mechanism but is not worth its cost in this economy.** It
  is a real data structure that changes behavior and builds relationships, but
  creatures that use it do not out-reproduce creatures that ignore it, so its
  capacity just drifts.
- **The crowded world collapses to a hawk monoculture.** There is no stable mix
  of strategies, which fails our diversity test.
- Three simulation bugs/artifacts were found by the tools we built and would
  have produced false conclusions. They are described below.

## The six tests

| # | Test | Verdict |
|---|------|---------|
| 1 | Viability | **Pass** |
| 2 | Rhyme and reason | **Pass for size/aggression, fail for memory** |
| 3 | Relationships | **Pass, with a caveat** |
| 4 | Diversity | **Fail** (hawk monoculture) |
| 5 | Traceability | **Pass** |
| 6 | Surprise | For you to judge; candidates listed below |

### 1. Viability: pass
6 of 6 seeds survive 8,000 ticks (about 60 generations in the crowded world)
with no extinction and no explosion. Lowest population after warm-up: 62 ± 5
(crowded), 145 ± 15 (spread).

### 2. Rhyme and reason: split
Same code, different food layout, 6 seeds each, 8,000 ticks:

| | crowded (default) | spread (`--preset spread`) |
|---|---|---|
| mean size | 2.11 ± 0.16 | 0.57 ± 0.00 |
| mean aggression | 0.84 ± 0.04 | 0.46 ± 0.01 |
| contests that become fights | 70% | 5% |
| deaths caused by fighting | 26.5% ± 2.6% | 2.8% ± 0.2% |
| population | 73 ± 7 | 160 ± 16 |

Seeds do not overlap between the two columns on any row. Selection is doing the
work: in the crowded world size is rewarded because contests decide who eats,
and the arms race shrinks the population because large bodies cost more to feed.
In the spread world contests rarely matter, so size is only a cost and falls to
its floor.

**Memory is where this test fails.** The crowded world does keep more memory
slots than the spread world (3.5 vs 1.3), but the ablation says that is not
because memory is useful. With `memory_has_effect=false` (creatures pay for
memory but ignore it) the gap persists:

| memory slots (5 seeds, 6,000 ticks) | used | ignored |
|---|---|---|
| crowded, cost 0.003 | 3.75 ± 0.92 | 3.43 ± 1.12 |
| crowded, cost 0.01 | 1.94 ± 0.72 | 1.85 ± 0.72 |
| spread, cost 0.003 | 1.28 ± 0.25 | 1.62 ± 0.79 |
| spread, cost 0.01 | 0.56 ± 0.07 | 0.49 ± 0.07 |

Births per tick are also identical with and without memory (e.g. 1.382 vs
1.385). A stronger-personality variant (aggression weight 40, decision noise
0.2) gave the same answer: memory capacity 4.20 ± 1.72 used vs 5.70 ± 2.49
ignored. Memory has no fitness advantage in any regime we tried.

Why: memory is only valuable if it lets you pick better. In a dense colony the
opponent is whoever is next to the food, so avoiding one rival means fighting
the next. In the spread world there are too few repeat meetings. Memory needs
a choice to inform (whom to challenge, whom to share with, whom to follow).

### 3. Relationships: pass, with a caveat
Pairs that meet at least 5 times and are lopsided (one side wins at least 85%)
occur far above what coin flips would give: 43 ± 14 observed vs 3.2 expected
(crowded) and 254 ± 70 vs 53 expected (spread). The caveat is that visible
size differences also create lopsided pairs, so not all of these are
"relationships" in the memory sense.

Memory does visibly change relationships. In the crowded world, creatures that
use memory form about half as many repeat rivalries (40 ± 12 vs 84 ± 10 pairs,
lower in all 5 seeds) because remembered losers stop re-challenging.

### 4. Diversity: fail
Starting aggression varies widely (sd 0.25). By the end it has narrowed to sd
0.13 with mean 0.84 in the crowded world, and the yield rate is 0.9%, so
essentially everyone fights. The bimodality coefficient (about 0.56, right at
the 0.555 threshold) shows no clear second mode. The spread world also settles
on a single (peaceful) strategy. The simulation currently has nothing that
keeps different strategies alive at the same time.

### 5. Traceability: pass
`explain.py` reconstructs a contest, a rivalry, a creature's life or its
ancestry from the log alone, including what each side believed, how it scored
its options, and how its memory changed. Example from a real run: creature 669
backed down once, remembered 596 as someone who stands firm (belief 0.93), and
gave way at once in the next two meetings (it stood firm again in the fourth,
when its own odds had changed). The logs also include ground-truth
aggression that no creature could see, so beliefs can be checked against reality.

### 6. Surprise
Things that surprised me, for you to weigh:
- The crowded arms race: size doubled, aggression climbed, yielding vanished,
  about a quarter of deaths became fights, and the population shrank while it
  happened. None of this was designed.
- Memory not paying for itself, across every regime tried.
- How easily plausible-looking numbers were wrong (next section).

## Bugs and artifacts found along the way

1. **Boxed-in yielders never left.** A creature that yielded but had no free
   neighbor stayed put, so the attacker challenged it again every tick (23
   meetings in 22 ticks). This inflated contest and rivalry counts and made
   memory look useful. Found by reading a rivalry with `explain.py`. Fixed (loser
   swaps places) with a regression test that fails on the old code.
2. **Reproduction was blocked tens of thousands of times in crowds** (54,364
   blocked vs 2,736 successful) because children had to be placed adjacent to the
   parent. That made crowds space-limited rather than energy-limited and hid
   selection on energy costs. Fixed by letting newborns settle at the nearest
   free cell within 4 cells.
3. **My first "sparse" control was wrong.** Abundant food everywhere does not
   give a sparse population, it gives an explosion to the population cap. A fair
   sparse world needs a density limiter, and even then it relaxes selection
   rather than testing memory.

Lesson: measure before believing. The ablation and the log-reading tools are
what exposed all three.

## Rough performance

About 7 ms per tick at around 100 creatures (a 1,500-tick default run takes
about 11 s on one core), so 8,000 ticks take roughly a minute or two. That is
fine for Phase 1 and for a 24/7 run at tens of ticks per second with this
population. It was not profiled or optimized and thousands of creatures would
need work.

## What this suggests for next steps (your decision)

1. **Give memory something it can pay for.** The most natural candidate is
   cooperation: sharing food or helping kin only works if you can tell who
   returned the favor, which is exactly what individual memory is for.
   Alternatives: let creatures choose between several opponents, or add a hidden
   fighting-strength trait so a past fight actually predicts the next one.
2. **Keep strategies diverse.** Candidates are environmental change (food
   patches that move or fail), a cost that grows as fighters become common, or
   several patch types. The crowded world needs something that stops "big and
   aggressive" from being the only answer.
3. **Species and predators** only after the above, per the original plan.

## Reproducing the numbers

```bash
python experiments.py compare --ticks 8000 --seeds 6 --cond "crowded:" --cond "spread:"
python experiments.py compare --ticks 6000 --seeds 5 \
  --cond "used:memory_cost=0.003" --cond "ignored:memory_cost=0.003,memory_has_effect=false"
```
Seeds start at 100 for `experiments.py`. Results are deterministic for a given
seed and configuration.
