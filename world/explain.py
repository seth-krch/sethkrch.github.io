#!/usr/bin/env python3
"""Reconstruct *why* things happened from an event log.

  python explain.py LOG summary
  python explain.py LOG life 42            # one creature: birth, ancestry, fights, death
  python explain.py LOG rivalry 42 17      # every meeting between two creatures
  python explain.py LOG contest 1893       # one contest, explained step by step
  python explain.py LOG rivals [N]         # the most-repeated pairings
  python explain.py LOG ancestry 42        # ancestors and descendant count
"""
import sys
from collections import Counter

from sim.events import read_events
from sim import analysis as A

OUTCOME_TEXT = {
    "yield": "{d} gave way at once and {a} took the spot",
    "backdown": "{d} stood firm and {a} backed down",
    "fight_attacker_wins": "{d} stood firm, they fought {r} round(s), and {a} won the spot",
    "fight_defender_wins": "{d} stood firm, they fought {r} round(s), and {d} kept the spot",
}


def explain_contest(e):
    a, d = e["attacker"], e["defender"]
    lines = [f"[eid {e['eid']}, tick {e['tick']}] creature {a} challenged creature {d} for a spot at "
             f"{tuple(e['pos'])} holding {e['food']} food."]
    sa, sd = e["sizes"]
    lines.append(f"  size {sa} vs {sd} -> attacker's chance to win a fight {e['p_att_win']:.0%} "
                 f"(the defender has the spot, which counts for something).")
    for who, knew, belief, other in ((a, e.get("att_knew_def"), e["att_belief_of_def"], d),
                                     (d, e.get("def_knew_att"), e["def_belief_of_att"], a)):
        if knew:
            lines.append(f"  {who} remembered {other}: believed a {belief:.0%} chance of standing firm/escalating.")
        else:
            lines.append(f"  {who} had no memory of {other} and assumed {belief:.0%}.")
    lines.append(f"  defender's decision score {e['def_score']:+.2f} (expected value of resisting {e['def_ev']:+.2f}, "
                 f"plus aggression bias and noise) -> {'stand firm' if e['outcome'] != 'yield' else 'give way'}.")
    if "att_score" in e:
        lines.append(f"  attacker's escalation score {e['att_score']:+.2f} (expected value of fighting "
                     f"{e['att_ev']:+.2f}, plus aggression bias and noise) -> "
                     f"{'fight' if e['outcome'].startswith('fight') else 'back down'}.")
    lines.append("  result: " + OUTCOME_TEXT[e["outcome"]].format(a=a, d=d, r=e["rounds"]) + ".")
    lines.append(f"  energy {a}: {e['energy_before'][0]} -> {e['energy_after'][0]}; "
                 f"{d}: {e['energy_before'][1]} -> {e['energy_after'][1]}.")
    for who, key in ((a, "att_mem_update"), (d, "def_mem_update")):
        upd = e.get(key)
        if upd:
            lines.append(f"  {who}'s memory updated: belief {upd[0]:.2f} (var {upd[1]:.3f}) -> "
                         f"{upd[2]:.2f} (var {upd[3]:.3f}).")
        elif key in e:
            lines.append(f"  {who} had no room to remember this.")
    ta, td = e["true_aggression"]
    lines.append(f"  (ground truth, never visible to either: aggression {a}={ta}, {d}={td})")
    return "\n".join(lines)


def cmd_summary(ev):
    kinds = Counter(e["kind"] for e in ev)
    print("events:", dict(kinds))
    print("outcomes:", dict(A.outcome_counts(ev)))
    print("deaths:", dict(A.death_causes(ev)))
    print("repeat encounters:", A.repeat_encounter_stats(ev))
    print("relationships:", A.relationship_summary(ev, min_contests=5, dominance=0.85))
    print("memory vs stranger:", A.does_memory_change_outcomes(ev))
    last = [e for e in ev if e["kind"] == "census"]
    if last:
        print("last census:", {k: v for k, v in last[-1].items() if k not in ('eid', 'kind')})


def cmd_life(ev, cid):
    birth = next((e for e in ev if e["kind"] == "birth" and e["id"] == cid), None)
    if not birth:
        sys.exit(f"no creature {cid}")
    print(f"creature {cid}: born tick {birth['tick']} gen {birth['generation']} parent {birth['parent']} "
          f"genes {birth['genes']}")
    mine = [e for e in ev if e["kind"] == "contest" and cid in (e["attacker"], e["defender"])]
    print(f"{len(mine)} contests")
    for e in mine[:40]:
        role = "attacked" if e["attacker"] == cid else "was challenged by"
        other = e["defender"] if e["attacker"] == cid else e["attacker"]
        print(f"  tick {e['tick']:>6}: {role} {other} -> {e['outcome']}")
    if len(mine) > 40:
        print(f"  ... {len(mine) - 40} more")
    death = next((e for e in ev if e["kind"] == "death" and e["id"] == cid), None)
    if death:
        print(f"died tick {death['tick']} of {death['cause']} aged {death['age']}; "
              f"children {death['stats']['children']}, ate {death['stats']['eaten']}")
        print("memory at death [id, belief, uncertainty, observations]:", death["memory"])
    else:
        print("still alive at end of log")


def cmd_rivalry(ev, x, y):
    pair = frozenset((x, y))
    hist = [e for e in A.contests(ev) if frozenset((e["attacker"], e["defender"])) == pair]
    if not hist:
        print(f"{x} and {y} never contested anything")
        return
    wins = Counter(A.winner_loser(e)[0] for e in hist)
    print(f"{x} and {y} met {len(hist)} times; wins: {dict(wins)}\n")
    for e in hist:
        print(explain_contest(e), "\n")


def cmd_rivals(ev, n):
    for r in A.relationships(ev, min_contests=3)[:n]:
        tag = "dominance" if r["dominance"] else "contested"
        print(f"{r['pair']}: {r['meetings']} meetings, ticks {r['first_tick']}-{r['last_tick']}, "
              f"{r['top_winner']} wins {r['top_win_fraction']:.0%}  [{tag}]")


def cmd_ancestry(ev, cid):
    parent, children, gen = A.lineages(ev)
    chain, cur = [], cid
    while cur is not None and cur in parent:
        chain.append(cur)
        cur = parent[cur]
    print("ancestors (self first):", chain)
    print("descendants:", len(A.descendants(children, cid)))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ev = list(read_events(sys.argv[1]))
    cmd, args = sys.argv[2], sys.argv[3:]
    if cmd == "summary":
        cmd_summary(ev)
    elif cmd == "life":
        cmd_life(ev, int(args[0]))
    elif cmd == "rivalry":
        cmd_rivalry(ev, int(args[0]), int(args[1]))
    elif cmd == "contest":
        e = next((e for e in ev if e["eid"] == int(args[0]) and e["kind"] == "contest"), None)
        print(explain_contest(e) if e else "no such contest event")
    elif cmd == "rivals":
        cmd_rivals(ev, int(args[0]) if args else 15)
    elif cmd == "ancestry":
        cmd_ancestry(ev, int(args[0]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
