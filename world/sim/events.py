"""Append-only structured event log. Every interesting thing that happens
leaves a record with enough state to reconstruct why it happened."""
import json


class EventLog:
    def __init__(self, path=None, keep=True):
        self.path = path
        self.keep = keep
        self.events = [] if keep else None
        self._fh = open(path, "w", buffering=1 << 16) if path else None
        self.next_id = 0
        self.counts = {}

    def emit(self, kind, tick, **data):
        ev = {"eid": self.next_id, "tick": tick, "kind": kind, **data}
        self.next_id += 1
        self.counts[kind] = self.counts.get(kind, 0) + 1
        if self.keep:
            self.events.append(ev)
        if self._fh:
            self._fh.write(json.dumps(ev, separators=(",", ":")) + "\n")
        return ev

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None


def read_events(path):
    with open(path) as fh:
        for line in fh:
            yield json.loads(line)
