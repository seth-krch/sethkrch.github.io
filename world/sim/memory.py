"""Per-creature memory of other individuals.

Each remembered individual gets a belief about their (hidden) disposition to
escalate: a mean in [0, 1] and a variance (uncertainty). Observations update
the belief like a one-dimensional Kalman filter: an observation with small
noise variance (a close fight) moves the belief a lot; a noisy one (a glimpse
from far away) barely moves it. Unseen beliefs decay back toward the prior.
Capacity is limited; when full, the least certain memory is dropped.
"""


class Belief:
    __slots__ = ("mean", "var", "last_seen", "n_obs")

    def __init__(self, mean, var, last_seen):
        self.mean = mean
        self.var = var
        self.last_seen = last_seen
        self.n_obs = 0


class Memory:
    def __init__(self, capacity, cfg):
        self.capacity = capacity
        self.cfg = cfg
        self.beliefs = {}

    def __len__(self):
        return len(self.beliefs)

    def _eff_var(self, b, tick):
        v = b.var + self.cfg.forget_rate * (tick - b.last_seen)
        return v if v < self.cfg.prior_var else self.cfg.prior_var

    def estimate(self, subject_id, tick):
        """(mean, variance, known) for a subject; the prior if never remembered."""
        b = self.beliefs.get(subject_id)
        if b is None:
            return self.cfg.prior_mean, self.cfg.prior_var, False
        return b.mean, self._eff_var(b, tick), True

    def observe(self, subject_id, z, noise_var, tick):
        """Fold in one observation z with noise variance `noise_var`.

        Returns (before, after) as (mean, var) pairs if the belief is stored,
        or None if there is no room and the observation was not informative
        enough to displace an existing memory.
        """
        if self.capacity <= 0:
            return None
        b = self.beliefs.get(subject_id)
        if b is not None:
            mean0, var0 = b.mean, self._eff_var(b, tick)
        else:
            mean0, var0 = self.cfg.prior_mean, self.cfg.prior_var
        gain = var0 / (var0 + noise_var)
        mean1 = mean0 + gain * (z - mean0)
        var1 = (1.0 - gain) * var0
        if b is None:
            if len(self.beliefs) >= self.capacity:
                worst_id, worst_var = None, -1.0
                for sid, ob in self.beliefs.items():
                    v = self._eff_var(ob, tick)
                    if v > worst_var:
                        worst_id, worst_var = sid, v
                if worst_var <= var1:
                    return None
                del self.beliefs[worst_id]
            b = Belief(mean1, var1, tick)
            self.beliefs[subject_id] = b
            b.n_obs = 1
            return (mean0, var0), (mean1, var1)
        b.mean, b.var, b.last_seen = mean1, var1, tick
        b.n_obs += 1
        return (mean0, var0), (mean1, var1)

    def snapshot(self, tick):
        return [[sid, round(b.mean, 3), round(self._eff_var(b, tick), 4), b.n_obs]
                for sid, b in self.beliefs.items()]
