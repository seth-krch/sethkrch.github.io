import io
import contextlib
import sys
import pytest
from sim.config import Config
from sim.events import EventLog
from sim.model import WorldModel
from sim import analysis as A

sys.path.insert(0, ".")
import explain


@pytest.fixture(scope="module")
def run():
    m = WorldModel(Config(seed=4, init_aggression_sd=0.25, n_patches=2, patch_radius=3, food_cap=40, regrow=1.0), EventLog())
    m.run(600)
    return m


def test_contests_are_logged_with_decision_state(run):
    cs = A.contests(run.log.events)
    assert len(cs) > 100
    for e in cs[:200]:
        for key in ("p_att_win", "def_score", "att_belief_of_def", "def_belief_of_att", "energy_before",
                    "energy_after", "outcome", "true_aggression"):
            assert key in e
        if e["outcome"] in ("backdown", "fight_attacker_wins", "fight_defender_wins"):
            assert "att_score" in e   # the escalation decision is only logged when it happened


def test_every_contest_can_be_explained_in_words(run):
    for e in A.contests(run.log.events)[:50]:
        text = explain.explain_contest(e)
        assert str(e["attacker"]) in text and str(e["defender"]) in text and "result:" in text


def test_memory_updates_are_logged_and_consistent(run):
    with_updates = [e for e in A.contests(run.log.events) if e.get("att_mem_update")]
    assert with_updates
    for e in with_updates:
        m0, v0, m1, v1 = e["att_mem_update"]
        assert v1 < v0 + 1e-9, "an observation should never make a belief less certain"


def test_relationships_form_between_repeat_opponents(run):
    rels = A.relationships(run.log.events, min_contests=3)
    assert rels and all(r["meetings"] >= 3 for r in rels)


def test_energy_never_appears_from_nowhere_in_a_contest(run):
    for e in A.contests(run.log.events)[:300]:
        a0, d0 = e["energy_before"]
        a1, d1 = e["energy_after"]
        assert a1 <= a0 + 1e-6 and d1 <= d0 + 1e-6


def test_lineage_parents_precede_children(run):
    parent, children, gen = A.lineages(run.log.events)
    for c, p in parent.items():
        if p is not None:
            assert gen[c] == gen[p] + 1
