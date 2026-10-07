"""Turn human-friendly choices (preset, stage, FIELD=VALUE overrides) into a Config.
Shared by the command line and the browser page so they cannot drift apart."""
import dataclasses
from .config import Config, PRESETS

# Each stage adds one system on top of the previous one.
STAGES = {
    1: dict(enable_reproduction=False, enable_contests=False, enable_memory=False),
    2: dict(enable_reproduction=True, enable_contests=False, enable_memory=False),
    3: dict(enable_reproduction=True, enable_contests=True, enable_memory=False),
    4: dict(enable_reproduction=True, enable_contests=True, enable_memory=True),
}


def parse_set(cfg, items):
    """Apply FIELD=VALUE strings to a config. Raises ValueError on a bad field or value."""
    fields = {f.name for f in dataclasses.fields(Config)}
    kw = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"expected FIELD=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        k, v = k.strip(), v.strip()
        if k not in fields:
            raise ValueError(f"unknown setting: {k}")
        cur = getattr(cfg, k)
        try:
            if isinstance(cur, bool):
                if v.lower() not in ("1", "0", "true", "false", "yes", "no"):
                    raise ValueError("expected true or false")
                kw[k] = v.lower() in ("1", "true", "yes")
            elif isinstance(cur, tuple):
                kw[k] = tuple(int(x) for x in v.strip("()[]").split(","))
            else:
                kw[k] = type(cur)(v)
        except ValueError as e:
            raise ValueError(f"bad value for {k}: {v!r} ({e})") from None
    return cfg.with_(**kw)


def build_config(preset="crowded", stage=4, seed=1, sets=()):
    if preset not in PRESETS:
        raise ValueError(f"unknown preset: {preset}")
    if int(stage) not in STAGES:
        raise ValueError(f"stage must be one of {sorted(STAGES)}")
    cfg = Config(seed=int(seed), **{**PRESETS[preset], **STAGES[int(stage)]})
    return parse_set(cfg, list(sets))


def describe_fields():
    """Every setting with its default, for display."""
    cfg = Config()
    return [{"name": f.name, "default": getattr(cfg, f.name)} for f in dataclasses.fields(Config)]
