"""Scoring math for decisions. Pure functions of numbers: no randomness, no
Mesa, nothing hidden. A decision is "score the options, pick the best, add
noise", and every term here can be printed for the event log."""
import math


def logistic(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def need(cfg, energy):
    """0 when full, 1 when empty."""
    n = 1.0 - energy / cfg.satiation
    return 0.0 if n < 0.0 else 1.0 if n > 1.0 else n


def stake(cfg, food, energy):
    """Energy value of holding a food spot for a while; hungry creatures value it more."""
    horizon = cfg.bite * cfg.contest_horizon
    amount = food if food < horizon else horizon
    return amount * (0.3 + cfg.hunger_weight * need(cfg, energy))


def p_attacker_wins(cfg, size_att, size_def):
    return logistic(cfg.size_advantage * math.log(size_att / size_def) - cfg.possession_bonus)


def expected_rounds(cfg, p):
    return 1.0 + 0.5 * (cfg.max_rounds - 1) * (1.0 - abs(2.0 * p - 1.0))


def fight_value(cfg, p_win, prize):
    """Expected net energy of fighting for `prize`, relative to not fighting."""
    return p_win * prize - expected_rounds(cfg, p_win) * cfg.round_cost - (1.0 - p_win) * cfg.injury_cost


def defender_ev(cfg, prize, p_def_win, q_escalate):
    """Value of resisting a challenge. q_escalate: belief the challenger will fight on."""
    return (1.0 - q_escalate) * prize + q_escalate * fight_value(cfg, p_def_win, prize)


def attacker_ev(cfg, prize, p_att_win, p_resist):
    """Value of challenging, assuming we only escalate when fighting is worth it."""
    fv = fight_value(cfg, p_att_win, prize)
    return (1.0 - p_resist) * prize + p_resist * (fv if fv > 0.0 else 0.0)
