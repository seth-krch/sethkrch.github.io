"""The world and its creatures (Mesa glue). Decision math, genes and memory
live in framework-independent modules; this file wires them to a grid."""
import math
import numpy as np
import mesa

from .config import Config
from .events import EventLog
from .genes import random_genes, mutate
from .memory import Memory
from . import decision as dec

DIRS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
STAT_KEYS = ("eaten", "moves", "challenges", "took_spot", "challenged", "resisted", "yielded",
             "fights", "fights_won", "backdowns", "children")


class Creature(mesa.Agent):
    def __init__(self, model, genes, pos, energy, parent_id=None, generation=0):
        super().__init__(model)
        self.genes = genes
        self.x, self.y = pos
        self.energy = energy
        self.age = 0
        self.parent_id = parent_id
        self.generation = generation
        self.alive = True
        slots = genes.memory if model.cfg.enable_memory else 0
        self.memory = Memory(slots, model.cfg)
        self.heading = (0, 0)
        self.stats = dict.fromkeys(STAT_KEYS, 0)

    # ------------------------------------------------------------------ tick
    def step(self):
        m, cfg, g = self.model, self.model.cfg, self.genes
        self.age += 1
        upkeep = cfg.base_cost * g.size + cfg.perception_cost * g.perception
        if cfg.enable_memory:
            upkeep += cfg.memory_cost * g.memory
        self.energy -= upkeep
        if self._starved_or_old():
            return

        x0, y0, fw, ow = self._window()
        others = self._perceive(ow, x0, y0)
        if cfg.enable_memory and self.memory.capacity > 0:
            self._glimpse(others)

        if self.energy < cfg.satiation:
            if m.food[self.y, self.x] >= cfg.min_food:
                bite = min(cfg.bite, float(m.food[self.y, self.x]))
                m.food[self.y, self.x] -= bite
                self.energy += bite
                self.stats["eaten"] += bite
            else:
                self._seek(x0, y0, fw, ow)
                if not self.alive:
                    return

        if (cfg.enable_reproduction and self.energy >= cfg.repro_threshold
                and self.age >= cfg.maturity_age):
            self._reproduce()
        self._starved_or_old()

    def _starved_or_old(self):
        if self.energy <= 0.0:
            self.model.kill(self, "starvation")
            return True
        if self.age >= self.model.cfg.max_age:
            self.model.kill(self, "old_age")
            return True
        return False

    # ------------------------------------------------------------ perception
    def _window(self):
        m, r = self.model, self.genes.perception
        x0, x1 = max(0, self.x - r), min(m.w, self.x + r + 1)
        y0, y1 = max(0, self.y - r), min(m.h, self.y + r + 1)
        return x0, y0, m.food[y0:y1, x0:x1], m.occ[y0:y1, x0:x1]

    def _perceive(self, ow, x0, y0):
        """Other creatures in view as (distance, creature)."""
        out = []
        by_id = self.model.by_id
        ys, xs = np.nonzero(ow)
        for iy, ix in zip(ys.tolist(), xs.tolist()):
            other = by_id[int(ow[iy, ix])]
            if other is self:
                continue
            d = max(abs(other.x - self.x), abs(other.y - self.y))
            out.append((d, other))
        return out

    def _glimpse(self, others):
        """Weak evidence about others' disposition from merely seeing them;
        noise grows with distance, so far-off sightings teach very little."""
        cfg, rnd, tick = self.model.cfg, self.model.random, self.model.tick
        for d, other in others:
            var = cfg.glimpse_var * (1 + d) ** 2
            z = other.genes.aggression + rnd.gauss(0.0, math.sqrt(var))
            self.memory.observe(other.unique_id, z, var, tick)

    def belief(self, other_id):
        """Believed escalation tendency of another creature (the prior if memory is ignored)."""
        cfg = self.model.cfg
        if not (cfg.enable_memory and cfg.memory_has_effect):
            return cfg.prior_mean
        return self.memory.estimate(other_id, self.model.tick)[0]

    # ------------------------------------------------------------- movement
    def _seek(self, x0, y0, fw, ow):
        m, cfg, g, rnd = self.model, self.model.cfg, self.genes, self.model.random
        disc_base = 0.8
        best = None
        best_score = 0.0
        ys, xs = np.nonzero(fw >= cfg.min_food)
        for iy, ix in zip(ys.tolist(), xs.tolist()):
            cx, cy = x0 + ix, y0 + iy
            if cx == self.x and cy == self.y:
                continue
            d = max(abs(cx - self.x), abs(cy - self.y))
            food = float(fw[iy, ix])
            oid = int(ow[iy, ix])
            disc = disc_base ** (d - 1)
            if oid == 0:
                prize = dec.stake(cfg, food, self.energy)
                score = prize * disc - cfg.move_cost * g.size * d
                contest = None
            elif cfg.enable_contests:
                other = m.by_id[oid]
                prize = dec.stake(cfg, food, self.energy)
                p_att = dec.p_attacker_wins(cfg, g.size, other.genes.size)
                ev = dec.attacker_ev(cfg, prize, p_att, self.belief(oid))
                score = ((ev - cfg.challenge_cost) * disc + cfg.aggression_weight * (g.aggression - 0.5)
                         - cfg.move_cost * g.size * d)
                contest = other
            else:
                continue
            score += rnd.gauss(0.0, cfg.decision_noise)
            if score > best_score:
                best_score, best = score, (cx, cy, d, contest)
        if best is None:
            self._wander()
        else:
            cx, cy, d, contest = best
            if contest is not None and d == 1:
                self._challenge(contest)
            else:
                self._step_toward(cx, cy)

    def _free_neighbors(self):
        m = self.model
        out = []
        for dx, dy in DIRS:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < m.w and 0 <= ny < m.h and m.occ[ny, nx] == 0:
                out.append((nx, ny))
        return out

    def _move_to(self, nx, ny):
        m = self.model
        m.occ[self.y, self.x] = 0
        self.heading = (nx - self.x, ny - self.y)
        self.x, self.y = nx, ny
        m.occ[ny, nx] = self.unique_id
        self.energy -= self.model.cfg.move_cost * self.genes.size
        self.stats["moves"] += 1

    def _step_toward(self, tx, ty):
        free = self._free_neighbors()
        if not free:
            return
        cur = (self.x - tx) ** 2 + (self.y - ty) ** 2
        scored = [((nx - tx) ** 2 + (ny - ty) ** 2, nx, ny) for nx, ny in free]
        lo = min(s[0] for s in scored)
        if lo >= cur:
            return
        nx, ny = self.model.random.choice([(s[1], s[2]) for s in scored if s[0] == lo])
        self._move_to(nx, ny)

    def _wander(self):
        free = self._free_neighbors()
        if not free:
            return
        rnd = self.model.random
        hx, hy = self.heading
        if (hx or hy) and rnd.random() < 0.6:
            tgt = (self.x + hx, self.y + hy)
            if tgt in free:
                self._move_to(*tgt)
                return
        self._move_to(*rnd.choice(free))

    def _flee(self, ax, ay, steps):
        for _ in range(steps):
            free = self._free_neighbors()
            if not free:
                return
            far = max((nx - ax) ** 2 + (ny - ay) ** 2 for nx, ny in free)
            if far <= (self.x - ax) ** 2 + (self.y - ay) ** 2:
                return
            nx, ny = self.model.random.choice(
                [(nx, ny) for nx, ny in free if (nx - ax) ** 2 + (ny - ay) ** 2 == far])
            self._move_to(nx, ny)

    # ------------------------------------------------------------- contests
    def _challenge(self, d):
        """This creature (attacker) challenges `d` for the food spot `d` is eating.

        d decides whether to yield or resist; if it resists the attacker decides
        whether to escalate to a fight or back down. Both decisions are scored
        from state, size, and (if remembered) the other's past behavior.
        """
        m, cfg, rnd = self.model, self.model.cfg, self.model.random
        a = self
        a_id, d_id = a.unique_id, d.unique_id
        food = float(m.food[d.y, d.x])
        a_e0, d_e0 = a.energy, d.energy
        a.energy -= cfg.challenge_cost
        a.stats["challenges"] += 1
        d.stats["challenged"] += 1
        m.window["challenges"] += 1

        p_att = dec.p_attacker_wins(cfg, a.genes.size, d.genes.size)
        a_prize = dec.stake(cfg, food, a.energy)
        d_prize = dec.stake(cfg, food, d.energy)

        # defender: yield or resist?
        q = d.belief(a_id)
        d_ev = dec.defender_ev(cfg, d_prize, 1.0 - p_att, q)
        d_score = d_ev + cfg.aggression_weight * (d.genes.aggression - 0.5) + rnd.gauss(0.0, cfg.decision_noise)
        resists = d_score > 0.0
        a_belief = a.belief(d_id)
        rec = {
            "attacker": a_id, "defender": d_id, "pos": [d.x, d.y], "food": round(food, 2),
            "sizes": [round(a.genes.size, 3), round(d.genes.size, 3)],
            "true_aggression": [round(a.genes.aggression, 3), round(d.genes.aggression, 3)],
            "p_att_win": round(p_att, 3),
            "att_belief_of_def": round(a_belief, 3), "def_belief_of_att": round(q, 3),
            "att_knew_def": a.memory.estimate(d_id, m.tick)[2] if cfg.enable_memory else False,
            "def_knew_att": d.memory.estimate(a_id, m.tick)[2] if cfg.enable_memory else False,
            "def_ev": round(d_ev, 3), "def_score": round(d_score, 3),
            "energy_before": [round(a_e0, 2), round(d_e0, 2)],
        }
        rounds = 0
        if not resists:
            outcome = "yield"
            d.stats["yielded"] += 1
            a.stats["took_spot"] += 1
            m.window["yields"] += 1
            z_a_of_d, var_a = 0.0, cfg.contest_var          # a saw d give way at once
            z_d_of_a, var_d = 0.7, cfg.contest_var * 2.0    # d saw a push and win without a fight
        else:
            d.stats["resisted"] += 1
            a_ev = dec.fight_value(cfg, p_att, a_prize)
            a_score = a_ev + cfg.aggression_weight * (a.genes.aggression - 0.5) + rnd.gauss(0.0, cfg.decision_noise)
            rec["att_ev"], rec["att_score"] = round(a_ev, 3), round(a_score, 3)
            if a_score <= 0.0:
                outcome = "backdown"
                a.stats["backdowns"] += 1
                m.window["backdowns"] += 1
                z_a_of_d, var_a = 1.0, cfg.contest_var      # a saw d stand firm
                z_d_of_a, var_d = 0.3, cfg.contest_var * 2.0
            else:
                spread = (cfg.max_rounds - 1) * (1.0 - abs(2.0 * p_att - 1.0))
                rounds = 1 + rnd.randint(0, int(round(spread)))
                a_wins = rnd.random() < p_att
                a.energy -= rounds * cfg.round_cost
                d.energy -= rounds * cfg.round_cost
                (d if a_wins else a).energy -= cfg.injury_cost
                a.stats["fights"] += 1
                d.stats["fights"] += 1
                m.window["fights"] += 1
                if a_wins:
                    a.stats["fights_won"] += 1
                    a.stats["took_spot"] += 1
                    outcome = "fight_attacker_wins"
                else:
                    d.stats["fights_won"] += 1
                    outcome = "fight_defender_wins"
                z_a_of_d = z_d_of_a = 1.0
                var_a = var_d = cfg.contest_var / rounds    # longer fights teach more

        if cfg.enable_memory:
            rec["att_mem_update"] = _fmt_update(a.memory.observe(d_id, z_a_of_d, var_a, m.tick))
            rec["def_mem_update"] = _fmt_update(d.memory.observe(a_id, z_d_of_a, var_d, m.tick))
        rec.update(outcome=outcome, rounds=rounds,
                   energy_after=[round(a.energy, 2), round(d.energy, 2)])
        m.log.emit("contest", m.tick, **rec)

        # physical consequences
        for c in (a, d):
            if c.energy <= 0.0:
                m.kill(c, "fight")
        if outcome in ("yield", "fight_attacker_wins"):
            px, py = rec["pos"]
            if d.alive:
                d._flee(a.x, a.y, cfg.flee_distance)
                if a.alive and (d.x, d.y) == (px, py):
                    # boxed in with nowhere to flee: the loser is pushed into the winner's place
                    m.swap(a, d)
                    a.energy -= cfg.move_cost * a.genes.size
                    a.stats["moves"] += 1
            if a.alive and m.occ[py, px] == 0:
                a._move_to(px, py)
        elif outcome == "fight_defender_wins":
            if a.alive:
                a._flee(d.x, d.y, cfg.flee_distance)

    # --------------------------------------------------------- reproduction
    def _reproduce(self):
        m, cfg = self.model, self.model.cfg
        if len(m.by_id) >= cfg.max_population:
            return
        free = self._free_neighbors()
        if not free:
            return
        pos = m.random.choice(free)
        self.energy -= cfg.child_energy + cfg.repro_overhead
        self.stats["children"] += 1
        m.spawn(mutate(self.genes, cfg, m.random), pos, cfg.child_energy,
                parent_id=self.unique_id, generation=self.generation + 1)


def _fmt_update(upd):
    if upd is None:
        return None
    (m0, v0), (m1, v1) = upd
    return [round(m0, 3), round(v0, 4), round(m1, 3), round(v1, 4)]


class WorldModel(mesa.Model):
    def __init__(self, cfg=None, log=None):
        cfg = cfg or Config()
        super().__init__(rng=cfg.seed)
        self.cfg = cfg
        self.log = log or EventLog()
        self.w, self.h = cfg.width, cfg.height
        self.tick = 0
        self.by_id = {}
        self.occ = np.zeros((self.h, self.w), dtype=np.int64)
        self.history = []
        self.window = dict.fromkeys(("births", "deaths", "challenges", "yields", "backdowns", "fights"), 0)
        self._build_world()
        self.log.emit("world", 0, config=cfg.to_dict(), cap_cells=int((self.cap > 0).sum()))
        for _ in range(cfg.initial_population):
            free = np.argwhere(self.occ == 0)
            y, x = free[self.random.randrange(len(free))]
            self.spawn(random_genes(cfg, self.random), (int(x), int(y)),
                       cfg.initial_energy * (0.75 + 0.5 * self.random.random()))

    # ---------------------------------------------------------------- world
    def _build_world(self):
        cfg = self.cfg
        cap = np.full((self.h, self.w), cfg.barren_cap, dtype=np.float64)
        if cfg.n_patches <= 0:
            cap[:] = cfg.food_cap
        else:
            yy, xx = np.mgrid[0:self.h, 0:self.w]
            for _ in range(cfg.n_patches):
                cx, cy = self.random.randrange(self.w), self.random.randrange(self.h)
                cap[(xx - cx) ** 2 + (yy - cy) ** 2 <= cfg.patch_radius ** 2] = cfg.food_cap
        self.cap = cap
        self.food = cap.copy()

    # ------------------------------------------------------------ creatures
    def spawn(self, genes, pos, energy, parent_id=None, generation=0):
        c = Creature(self, genes, pos, energy, parent_id, generation)
        self.by_id[c.unique_id] = c
        self.occ[pos[1], pos[0]] = c.unique_id
        self.window["births"] += 1
        self.log.emit("birth", self.tick, id=c.unique_id, parent=parent_id, generation=generation,
                      pos=[pos[0], pos[1]], energy=round(energy, 2), genes=genes.to_dict())
        return c

    def kill(self, c, cause):
        if not c.alive:
            return
        c.alive = False
        self.occ[c.y, c.x] = 0
        del self.by_id[c.unique_id]
        self.window["deaths"] += 1
        self.log.emit("death", self.tick, id=c.unique_id, cause=cause, age=c.age, pos=[c.x, c.y],
                      energy=round(c.energy, 2), parent=c.parent_id, generation=c.generation,
                      genes=c.genes.to_dict(),
                      stats={k: (round(v, 2) if isinstance(v, float) else v) for k, v in c.stats.items()},
                      memory=c.memory.snapshot(self.tick))
        c.remove()

    def swap(self, a, b):
        """Exchange the positions of two creatures."""
        a.x, a.y, b.x, b.y = b.x, b.y, a.x, a.y
        self.occ[a.y, a.x] = a.unique_id
        self.occ[b.y, b.x] = b.unique_id

    # ----------------------------------------------------------------- tick
    def step(self):
        self.tick += 1
        np.minimum(self.cap, self.food + self.cfg.regrow, out=self.food)
        order = list(self.by_id.values())
        self.random.shuffle(order)
        for c in order:
            if c.alive:
                c.step()
        if self.tick % self.cfg.census_every == 0:
            self._census()

    def run(self, ticks):
        for _ in range(ticks):
            self.step()
            if not self.by_id:
                break

    def _census(self):
        cs = list(self.by_id.values())
        n = len(cs)

        def mean(f):
            return sum(f(c) for c in cs) / n if n else 0.0

        agg_mean = mean(lambda c: c.genes.aggression)
        agg_sd = math.sqrt(mean(lambda c: (c.genes.aggression - agg_mean) ** 2)) if n else 0.0
        rec = {
            "tick": self.tick, "pop": n,
            "food": round(float(self.food.sum()), 1),
            "mean_energy": round(mean(lambda c: c.energy), 2),
            "mean_age": round(mean(lambda c: c.age), 1),
            "size": round(mean(lambda c: c.genes.size), 3),
            "aggression": round(agg_mean, 3),
            "aggression_sd": round(agg_sd, 3),
            "perception": round(mean(lambda c: c.genes.perception), 2),
            "memory": round(mean(lambda c: c.genes.memory), 2),
            "known": round(mean(lambda c: len(c.memory)), 2),
            **self.window,
        }
        self.history.append(rec)
        self.log.emit("census", self.tick, **{k: v for k, v in rec.items() if k != "tick"})
        for k in self.window:
            self.window[k] = 0

    # ------------------------------------------------------------ rendering
    def render(self):
        """Tiny ASCII map: creatures as a digit (aggression decile), food as shading."""
        shades = " .:*#"
        rows = []
        for y in range(self.h):
            row = []
            for x in range(self.w):
                oid = self.occ[y, x]
                if oid:
                    row.append(str(min(9, int(self.by_id[int(oid)].genes.aggression * 10))))
                else:
                    f = self.food[y, x] / self.cfg.food_cap if self.cfg.food_cap else 0
                    row.append(shades[min(4, int(f * 4.99))] if self.cap[y, x] > 0 else " ")
            rows.append("".join(row))
        return "\n".join(rows)
