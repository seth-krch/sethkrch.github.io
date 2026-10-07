"""Run a world headless and report to the terminal."""
import time
from .config import Config
from .events import EventLog
from .model import WorldModel

HEADER = (f"{'tick':>6} {'pop':>5} {'food':>7} {'enrg':>5} {'age':>5} {'size':>5} {'aggr':>5} "
          f"{'perc':>5} {'mem':>5} {'known':>5} | {'born':>4} {'died':>4} {'chal':>4} {'yld':>4} {'bkdn':>4} {'fght':>4}")


def format_census(r):
    return (f"{r['tick']:>6} {r['pop']:>5} {r['food']:>7.0f} {r['mean_energy']:>5.1f} {r['mean_age']:>5.0f} "
            f"{r['size']:>5.2f} {r['aggression']:>5.2f} {r['perception']:>5.2f} {r['memory']:>5.2f} "
            f"{r['known']:>5.2f} | {r['births']:>4} {r['deaths']:>4} {r['challenges']:>4} {r['yields']:>4} "
            f"{r['backdowns']:>4} {r['fights']:>4}")


def simulate(cfg, ticks, log_path=None, keep_events=False, report_every=0, map_every=0, out=print):
    log = EventLog(log_path, keep=keep_events)
    model = WorldModel(cfg, log)
    t0 = time.time()
    if report_every:
        out(HEADER)
    shown = 0
    for _ in range(ticks):
        model.step()
        if report_every and model.tick % report_every == 0:
            # report the census nearest to this tick
            if not model.history or model.history[-1]["tick"] != model.tick:
                model._census()
            out(format_census(model.history[-1]))
        if map_every and model.tick % map_every == 0:
            out(f"--- map at tick {model.tick} ---")
            out(model.render())
        if not model.by_id:
            out(f"*** extinct at tick {model.tick} ***")
            break
    log.close()
    model.wall_seconds = time.time() - t0
    return model
