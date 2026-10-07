import random
import pytest
from sim.config import Config
from sim.genes import Genes, random_genes, mutate
from sim.memory import Memory
from sim import decision as dec

CFG = Config()


def test_mutation_stays_in_bounds_and_changes_things():
    rng = random.Random(0)
    g = random_genes(CFG, rng)
    seen = set()
    for _ in range(2000):
        g = mutate(g, CFG, rng)
        assert 0.0 <= g.aggression <= 1.0
        assert 0.5 <= g.size <= 2.5
        assert 1 <= g.perception <= CFG.max_perception
        assert 0 <= g.memory <= CFG.max_memory
        seen.add(g.memory)
    assert len(seen) > 3  # memory capacity actually varies


def test_no_memory_genes_when_memory_disabled():
    cfg = CFG.with_(enable_memory=False)
    rng = random.Random(0)
    g = random_genes(cfg, rng)
    assert g.memory == 0 and mutate(g, cfg, rng).memory == 0


def test_close_evidence_beats_distant_glimpses():
    far = Memory(5, CFG)
    for t in range(10):                       # ten distant glimpses, 8 cells away
        far.observe(1, 1.0, CFG.glimpse_var * 9 ** 2, t)
    close = Memory(5, CFG)
    close.observe(1, 1.0, CFG.contest_var / 4, 0)   # one 4-round fight
    assert close.estimate(1, 0)[1] < far.estimate(1, 10)[1]
    assert abs(close.estimate(1, 0)[0] - 1.0) < abs(far.estimate(1, 10)[0] - 1.0)


def test_unknown_subject_returns_prior():
    m = Memory(3, CFG)
    mean, var, known = m.estimate(99, 0)
    assert (mean, var, known) == (CFG.prior_mean, CFG.prior_var, False)


def test_zero_capacity_remembers_nothing():
    m = Memory(0, CFG)
    assert m.observe(1, 1.0, 0.01, 0) is None and len(m) == 0


def test_capacity_is_respected_and_least_certain_is_evicted():
    m = Memory(2, CFG)
    m.observe(1, 1.0, 0.01, 0)    # confident
    m.observe(2, 0.0, 5.0, 0)     # barely informative
    assert len(m) == 2
    m.observe(3, 1.0, 0.02, 0)    # informative newcomer displaces id 2
    assert set(m.beliefs) == {1, 3}
    assert m.observe(4, 0.5, 50.0, 0) is None   # useless newcomer is not stored
    assert set(m.beliefs) == {1, 3}


def test_memories_fade_toward_the_prior():
    m = Memory(2, CFG)
    m.observe(1, 1.0, 0.01, 0)
    v0 = m.estimate(1, 0)[1]
    v_later = m.estimate(1, 500)[1]
    assert v_later > v0 and v_later <= CFG.prior_var


def test_bigger_attacker_wins_more_and_possession_helps_defender():
    small, big = 0.8, 1.6
    assert dec.p_attacker_wins(CFG, big, small) > dec.p_attacker_wins(CFG, small, big)
    assert dec.p_attacker_wins(CFG, 1.0, 1.0) < 0.5


def test_challenge_is_worth_more_against_a_creature_known_to_yield():
    prize, p = 8.0, 0.4
    assert dec.attacker_ev(CFG, prize, p, 0.05) > dec.attacker_ev(CFG, prize, p, 0.95)


def test_hungry_creatures_value_food_more():
    assert dec.stake(CFG, 9.0, 5.0) > dec.stake(CFG, 9.0, 39.0)
