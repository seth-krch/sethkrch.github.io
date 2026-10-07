"""A minimal stand-in for the two Mesa classes the simulation uses.

The browser page runs the simulation in Pyodide, where installing real Mesa would
also pull in pandas and scipy (a heavy download on a phone). The simulation only
needs Mesa's Model (a seeded random generator) and Agent (a numbered object), and
Mesa's `Model.random` is exactly `random.Random(seed)`. tests/test_web.py proves
that runs under this shim and under real Mesa produce identical event logs.
"""
import random


class Model:
    def __init__(self, *args, rng=None, seed=None, **kwargs):
        self.random = random.Random(rng if rng is not None else seed)
        self._next_agent_id = 1


class Agent:
    def __init__(self, model, *args, **kwargs):
        self.model = model
        self.unique_id = model._next_agent_id
        model._next_agent_id += 1

    def remove(self):
        pass
