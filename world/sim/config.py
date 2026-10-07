"""All tunable parameters in one place. Everything is measured in ticks and
energy units; nothing here refers to real-world time."""
from dataclasses import dataclass, asdict, replace


@dataclass(frozen=True)
class Config:
    # --- run ---
    seed: int = 1

    # --- world (stage 1) ---
    width: int = 40
    height: int = 40
    n_patches: int = 8            # fertile patches; 0 = uniform fertility
    patch_radius: int = 4
    food_cap: float = 10.0        # max food on a fertile cell
    barren_cap: float = 0.0       # max food outside patches
    regrow: float = 0.15          # food regrown per cell per tick

    # --- creatures: energy economy (stage 1) ---
    initial_population: int = 120
    initial_energy: float = 20.0
    bite: float = 3.0             # max food eaten per tick
    base_cost: float = 0.20       # per tick, scaled by size
    move_cost: float = 0.08       # per step, scaled by size
    perception_cost: float = 0.012  # per tick per unit of perception range
    memory_cost: float = 0.010    # per tick per memory slot (paid whether used or not)
    max_age: int = 300
    satiation: float = 40.0       # creatures at/above this energy stop eating
    min_food: float = 1.0         # a cell with less food does not attract creatures
    max_population: int = 1500

    # --- reproduction / genes (stage 2) ---
    enable_reproduction: bool = True
    repro_threshold: float = 32.0
    maturity_age: int = 40
    birth_radius: int = 4         # children settle at the nearest free cell within this distance
    child_energy: float = 12.0
    repro_overhead: float = 4.0
    mutation_rate: float = 0.20   # per integer gene per birth
    size_sigma: float = 0.07      # log-normal jitter on size per birth
    aggression_sigma: float = 0.06
    init_aggression_mean: float = 0.5
    init_aggression_sd: float = 0.08
    init_memory_range: tuple = (2, 6)
    init_perception_range: tuple = (2, 5)
    max_memory: int = 20
    max_perception: int = 8

    # --- contests (stage 3) ---
    enable_contests: bool = True
    contest_horizon: float = 4.0      # ticks of eating a contested spot is worth
    hunger_weight: float = 1.0        # how much hunger inflates the value of food
    aggression_weight: float = 6.0    # score bias per unit of (aggression - 0.5)
    possession_bonus: float = 0.6     # logit bonus to the creature already eating
    size_advantage: float = 3.0       # logit per unit of ln(size ratio)
    round_cost: float = 0.5           # energy each combatant pays per fight round
    injury_cost: float = 1.5          # extra energy the loser loses
    max_rounds: int = 4
    decision_noise: float = 0.8       # sd of noise added to action scores
    flee_distance: int = 3
    challenge_cost: float = 0.3       # energy paid just for challenging, win or lose

    # --- memory (stage 4) ---
    enable_memory: bool = True
    memory_has_effect: bool = True    # ablation switch: creatures pay for memory but ignore it
    prior_mean: float = 0.5
    prior_var: float = 0.25
    glimpse_var: float = 0.5          # observation variance of a glimpse at distance 0
    contest_var: float = 0.04         # observation variance of a contest outcome
    forget_rate: float = 0.002        # variance regained per tick unseen (decay toward the prior)

    # --- logging ---
    census_every: int = 50

    def with_(self, **kw):
        return replace(self, **kw)

    def to_dict(self):
        d = asdict(self)
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()}
