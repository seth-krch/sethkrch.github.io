"""Heritable traits. Inheritance plus random mutation is the only way genes
change; nothing here is aimed at producing any particular outcome."""
import math
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Genes:
    size: float        # visible to others; drives upkeep cost and fighting strength
    aggression: float  # hidden; willingness to challenge and to resist, in [0, 1]
    perception: int    # vision range in cells; costs energy per tick
    memory: int        # number of other creatures that can be remembered; costs energy per tick

    def to_dict(self):
        return asdict(self)


SIZE_MIN, SIZE_MAX = 0.5, 2.5


def _clip(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def random_genes(cfg, rng):
    return Genes(
        size=_clip(math.exp(rng.gauss(0.0, 0.12)), SIZE_MIN, SIZE_MAX),
        aggression=_clip(rng.gauss(cfg.init_aggression_mean, cfg.init_aggression_sd), 0.0, 1.0),
        perception=rng.randint(*cfg.init_perception_range),
        memory=rng.randint(*cfg.init_memory_range) if cfg.enable_memory else 0,
    )


def _mutate_int(v, lo, hi, rate, rng):
    if rng.random() < rate:
        v += rng.choice((-2, -1, -1, 1, 1, 2))
    return int(_clip(v, lo, hi))


def mutate(g, cfg, rng):
    """Child genes: parent's genes with small random changes."""
    return Genes(
        size=_clip(g.size * math.exp(rng.gauss(0.0, cfg.size_sigma)), SIZE_MIN, SIZE_MAX),
        aggression=_clip(g.aggression + rng.gauss(0.0, cfg.aggression_sigma), 0.0, 1.0),
        perception=_mutate_int(g.perception, 1, cfg.max_perception, cfg.mutation_rate, rng),
        memory=_mutate_int(g.memory, 0, cfg.max_memory, cfg.mutation_rate, rng) if cfg.enable_memory else 0,
    )
