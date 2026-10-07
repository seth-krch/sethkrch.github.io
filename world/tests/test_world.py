import numpy as np
import pytest
from sim.config import Config
from sim.events import EventLog
from sim.model import WorldModel
from sim.runner import simulate

STAGE1 = dict(enable_reproduction=False, enable_contests=False, enable_memory=False)


def run(cfg, ticks):
    m = WorldModel(cfg, EventLog())
    m.run(ticks)
    return m


def check_consistency(m):
    seen = set()
    for c in m.by_id.values():
        assert c.alive
        assert m.occ[c.y, c.x] == c.unique_id
        assert (c.x, c.y) not in seen
        seen.add((c.x, c.y))
    assert int((m.occ > 0).sum()) == len(m.by_id)
    assert (m.food >= -1e-9).all() and (m.food <= m.cap + 1e-9).all()


def test_stage1_is_consistent_and_creatures_live():
    m = run(Config(seed=3, **STAGE1), 300)
    check_consistency(m)
    assert 0 < len(m.by_id) <= 120


def test_barren_world_starves_everyone_and_logs_why():
    m = run(Config(seed=3, food_cap=0.0, **STAGE1), 400)
    assert len(m.by_id) == 0
    deaths = [e for e in m.log.events if e["kind"] == "death"]
    assert len(deaths) == 120 and {d["cause"] for d in deaths} == {"starvation"}


def test_old_age_kills_even_in_a_rich_world():
    m = run(Config(seed=3, max_age=100, **STAGE1), 150)
    assert len(m.by_id) == 0
    causes = [e["cause"] for e in m.log.events if e["kind"] == "death"]
    assert causes.count("old_age") > 0.8 * len(causes)   # a few start far from food and starve first


@pytest.mark.parametrize("stage", [
    STAGE1,
    dict(enable_reproduction=True, enable_contests=False, enable_memory=False),
    dict(enable_reproduction=True, enable_contests=True, enable_memory=False),
    dict(enable_reproduction=True, enable_contests=True, enable_memory=True),
])
def test_every_stage_stays_consistent(stage):
    m = run(Config(seed=5, **stage), 400)
    check_consistency(m)


def test_same_seed_same_history():
    a = run(Config(seed=11), 300)
    b = run(Config(seed=11), 300)
    c = run(Config(seed=12), 300)
    assert a.log.events == b.log.events
    assert a.log.events != c.log.events


def test_log_is_complete_and_coherent():
    m = run(Config(seed=2, init_aggression_sd=0.25), 800)
    births = {e["id"]: e for e in m.log.events if e["kind"] == "birth"}
    deaths = [e for e in m.log.events if e["kind"] == "death"]
    ids = [d["id"] for d in deaths]
    assert len(ids) == len(set(ids)), "creature died twice"
    for d in deaths:
        assert d["id"] in births
        assert d["age"] >= 1
    for b in births.values():
        if b["parent"] is not None:
            assert b["parent"] in births and births[b["parent"]]["tick"] <= b["tick"]
    alive = set(births) - set(ids)
    assert alive == set(m.by_id)
    for e in m.log.events:
        if e["kind"] == "contest":
            assert e["attacker"] in births and e["defender"] in births
            assert e["outcome"] in ("yield", "backdown", "fight_attacker_wins", "fight_defender_wins")


def test_ablation_flag_changes_behavior_but_not_costs():
    base = Config(seed=7)
    a = run(base, 600)
    b = run(base.with_(memory_has_effect=False), 600)
    assert a.log.events != b.log.events
