"""Questions we can ask of a finished run, answered from the event log alone."""
from collections import Counter, defaultdict


def contests(events):
    return [e for e in events if e["kind"] == "contest"]


def winner_loser(e):
    """(winner, loser) of a contest, by who ended up holding the food spot."""
    a, d, out = e["attacker"], e["defender"], e["outcome"]
    if out in ("yield", "fight_attacker_wins"):
        return a, d
    return d, a


def outcome_counts(events):
    return Counter(e["outcome"] for e in contests(events))


def repeat_encounter_stats(events):
    """How often do creatures meet in a contest more than once? Memory is only
    worth paying for if the same individuals keep running into each other."""
    seen = set()
    repeat = knew = total = 0
    for e in contests(events):
        pair = frozenset((e["attacker"], e["defender"]))
        total += 1
        if pair in seen:
            repeat += 1
        seen.add(pair)
        if e.get("att_knew_def"):
            knew += 1
    return {"contests": total, "repeat_pair_fraction": repeat / total if total else 0.0,
            "attacker_knew_defender_fraction": knew / total if total else 0.0,
            "distinct_pairs": len(seen)}


def pair_histories(events):
    hist = defaultdict(list)
    for e in contests(events):
        hist[frozenset((e["attacker"], e["defender"]))].append(e)
    return hist


def relationships(events, min_contests=3, dominance=0.8):
    """Pairs with enough history, labeled by whether one side keeps winning.

    A 'dominance' relationship: one creature wins >= `dominance` of at least
    `min_contests` meetings. Returns a list of dicts sorted by meeting count.
    """
    out = []
    for pair, evs in pair_histories(events).items():
        if len(evs) < min_contests:
            continue
        wins = Counter(winner_loser(e)[0] for e in evs)
        top, n_top = wins.most_common(1)[0]
        frac = n_top / len(evs)
        out.append({"pair": sorted(pair), "meetings": len(evs), "top_winner": top,
                    "top_win_fraction": round(frac, 3), "dominance": frac >= dominance,
                    "first_tick": evs[0]["tick"], "last_tick": evs[-1]["tick"]})
    out.sort(key=lambda r: -r["meetings"])
    return out


def relationship_summary(events, **kw):
    rels = relationships(events, **kw)
    return {"pairs_with_history": len(rels), "dominance_pairs": sum(r["dominance"] for r in rels)}


def does_memory_change_outcomes(events):
    """Compare contests where the attacker already knew the defender with those
    where it did not: how often does the defender give way, and how often does
    the attacker back down after being resisted?"""
    rows = {True: Counter(), False: Counter()}
    for e in contests(events):
        rows[bool(e.get("att_knew_def"))][e["outcome"]] += 1
    summary = {}
    for knew, c in rows.items():
        n = sum(c.values())
        if n:
            summary["knew" if knew else "stranger"] = {
                "n": n, "yield": round(c["yield"] / n, 3), "backdown": round(c["backdown"] / n, 3),
                "fight": round((c["fight_attacker_wins"] + c["fight_defender_wins"]) / n, 3)}
    return summary


def belief_accuracy(events):
    """How well do attackers' beliefs about defenders match the defenders' true
    aggression? Returns the correlation over contests where the belief was informed."""
    xs, ys = [], []
    for e in contests(events):
        if e.get("att_knew_def"):
            xs.append(e["att_belief_of_def"])
            ys.append(e["true_aggression"][1])
    n = len(xs)
    if n < 10:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / (sxx * syy) ** 0.5 if sxx > 0 and syy > 0 else None


def death_causes(events):
    return Counter(e["cause"] for e in events if e["kind"] == "death")


def lineages(events):
    """parent map, children map, and generation of every creature ever born."""
    parent, children, gen = {}, defaultdict(list), {}
    for e in events:
        if e["kind"] == "birth":
            parent[e["id"]] = e["parent"]
            gen[e["id"]] = e["generation"]
            if e["parent"] is not None:
                children[e["parent"]].append(e["id"])
    return parent, children, gen


def descendants(children, root):
    out, stack = [], [root]
    while stack:
        for c in children.get(stack.pop(), []):
            out.append(c)
            stack.append(c)
    return out


def census_series(events, field):
    return [(e["tick"], e[field]) for e in events if e["kind"] == "census"]


def fitness_correlation(events, gene, outcome="children", min_age=0):
    """Correlation between a gene and a creature's reproductive success, over
    everyone who has died. A positive value means the gene is being selected for."""
    xs, ys = [], []
    for e in events:
        if e["kind"] == "death" and e["age"] >= min_age:
            xs.append(e["genes"][gene])
            ys.append(e["stats"][outcome])
    n = len(xs)
    if n < 20:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sxx * syy) ** 0.5
