# Persistent World — Phase 1 Design

Status: implemented. See the implementation notes at the end and PHASE1_RESULTS.md for what was found.

## Vision (destination, not Phase 1)

A persistent artificial world of autonomous creatures that runs 24/7 whether or
not anyone is watching. Humans and animals, predators and prey, tribes, wars,
famines, extinctions, speciation. Major arcs (a war, a famine) should start and
end on roughly a one-month scale; a creature should live weeks to months in
real viewing time. Website and 3D come much later (Phases 4–5).

## Principles

1. **Emergence, not theater.** Interesting events are never scheduled or
   spawned. A detector may *notice* them afterwards.
2. **Claims match mechanisms.** Memory is a data structure. Relationships come
   from interaction history. Evolution is selection plus inheritance.
3. **Inspectable.** Any event must be explainable from stored state/history.
4. **Few systems, deep interactions.** Resist adding systems until the current
   ones are shown to produce something interesting.
5. **No LLM in the tick loop.** Math, utility scoring, and evolution do the
   work. LLMs are a possible later layer for rare high-level cognition.
6. **Time is measured in ticks.** Mapping ticks to real time is a Phase 3
   decision. Phase 1 runs headless as fast as possible.

## Phase 1 question

Do a few simple, inspectable systems produce behavior worth watching? We are
*not* building the tribal world yet.

## Phase 1 world

**World.** Small 2D grid. Food regrows at a fixed rate. Text output only.

**Creatures.** One species. Each has a permanent ID and:

- `energy` — the single source of hunger, survival and death.
- Genes: `size` (visible to others), `aggression` (hidden), `perception_range`,
  `memory_capacity`. Mutation is a small random shift at birth.
- Asexual reproduction when energy is high enough; child inherits parent genes
  plus mutation; parent ID is recorded (genealogy from day one).
- Death by starvation, old age, or fight.
- One shared energy budget: movement, perception range, and memory capacity
  all draw energy every tick. Tradeoffs come from the budget, not scripts.

**Decisions.** Each tick, score each available action (eat, move, contest,
flee, rest, reproduce) from internal state, perception and memory. Pick the
highest score plus noise. Genes are the weights. No neural nets. The decision
module stays swappable.

**Contests.** When A sees B eating, A weighs its aggression against B's
visible size and any memory of B. B gets a small possession bonus. Outcomes:
B yields; both fight (both pay a cost, the stronger usually wins, upsets are
possible); or A backs down. Both sides update memory from the outcome.

**Memory.** Per-creature record keyed by creature ID: estimated hidden
aggression, confidence, last seen tick/location. Information gain scales with
proximity and interaction depth (a distant glimpse teaches little; a
zero-distance fight teaches a lot). Capacity is a heritable gene and costs
energy every tick. When full, the least useful entry is dropped.

**Evidence trail.** Append-only structured event log: births, deaths (with
cause), contests (scores, memory state, outcome), memory updates. Everything
reproducible from a seed.

## Out of scope for Phase 1

Multiple species, predators, sexual reproduction, groups/tribes,
communication, terrain/biomes, persistence beyond the event log, any UI.

## Pass/fail tests (defined before seeing results)

1. **Viability** — population persists across many seeds without always
   crashing or exploding.
2. **Rhyme and reason** — memory capacity evolves differently in crowded/scarce
   vs sparse/abundant worlds, *consistently across seeds*. If it always drifts
   to zero or max, the cost/payoff is wrong.
3. **Relationships** — pairs show repeated, consistent interactions (bully and
   avoider).
4. **Diversity** — aggression settles into a mix of strategies rather than one
   boring answer.
5. **Traceability** — a surprising event can be explained from the log alone.
6. **Surprise** — something happens neither of us predicted.

Cost constants are chosen by us, so results must be checked with parameter
sweeps; report which findings are robust and which depend on a lucky constant.

## Framework

Start with Mesa 3.x (grid, spatial queries, seeded RNG, data collection).
Keep genes, decision scoring, memory and the event log in plain-Python modules
that do not import Mesa, so the framework can be swapped if performance
requires it. Revisit if populations in the thousands are too slow.

## Open parameters (tuned during build, not decided now)

Grid size, initial population, food regrowth rate, cost constants, mutation
rate, lifespan in ticks, learning rate and decay for memory.

## Implementation notes (what changed while building it)

These are deliberate deviations or details the design left open. Each one was
chosen for a reason that showed up in testing.

- **Contests are sequential.** The attacker challenges (paying a small
  `challenge_cost` win or lose); the defender then yields or resists; if it
  resists, the attacker either escalates to a fight or backs down. That yields
  exactly the three agreed outcomes. A fight resolves in one tick, but its
  length in rounds (more rounds when evenly matched) scales both the energy
  cost and how much each side learns.
- **What memory stores.** A belief about another creature's *disposition to
  stand firm / escalate*, as a mean and an uncertainty (a one-dimensional
  Kalman filter). Beliefs are updated by (a) contest outcomes, with small noise,
  and (b) weak "glimpses" of nearby creatures each tick, whose noise grows with
  distance squared, so ten distant sightings teach less than one close fight.
  Unseen beliefs lose certainty over time; when capacity is full, the least
  certain belief is dropped.
- **Aggression is hidden, size is visible.** Both fight decisions are scored
  from visible size, hunger, possession, memory of the opponent, aggression
  bias and noise. No creature can read another's aggression directly.
- **Boxed-in losers swap places with the winner.** Found via the explain tool:
  a loser with no free cell used to stay on the spot, so the winner re-challenged
  it every tick forever, inflating contest and rivalry counts.
- **Newborns disperse** to the nearest free cell within `birth_radius`.
  Adjacent-only placement blocked reproduction tens of thousands of times in
  crowded colonies, which removed energy as the limiting factor and hid
  selection on energy costs.
- **Satiation.** Creatures at or above `satiation` energy stop eating, so food
  is not hoarded and well-fed creatures stop seeking.
- **Default world.** Crowded colonies on two rich food patches, because that
  is where contests have consequences. `--preset spread` (many small patches)
  is the contrast case.
