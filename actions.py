"""Business actions for ModDiver Laboratory, kept out of the Tk view.

Option B of the GUI split: core-adjacent logic moves here first, pages follow later.
The App keeps only layout and event wiring; these functions take (cfg, log, paths)
and do the work, so they can be tested without a display.
"""
from pathlib import Path

import core


def ensure_stock(cfg, log):
    if not core.STOCK.exists() or not any(core.STOCK.glob("*.dl_bin")):
        core.capture_stock(cfg, log)


def install_all(cfg, log, dry_run=False):
    ensure_stock(cfg, log)
    return core.deploy(cfg, log, dry_run=dry_run)


def capture_stock(cfg, log):
    return core.capture_stock(cfg, log)


def purge(cfg, log):
    return core.purge(cfg, log)


def export_mod(cfg, path, log):
    return core.export_mod(cfg, path, log)


def add_zip(cfg, path, log):
    mod = core.parse_mod(Path(path))
    if not mod.get("targets"):
        raise RuntimeError("No deployable data in that ZIP.")
    cfg.setdefault("mods", []).append({
        "path": mod["path"], "name": mod["name"], "type": mod["type"],
        "targets": mod["targets"], "enabled": True, "selected": {},
    })
    core.save_config(cfg)
    log("added " + mod["name"])
    return mod


def set_game(cfg, path):
    cfg["game"] = str(path).strip()
    core.save_config(cfg)


def remove_mod(cfg, i, log):
    m = cfg["mods"].pop(i)
    core.save_config(cfg)
    log("removed " + str(m.get("name")) + " from the library (built-in package kept; use Purge to restore game files)")


def toggle_mod(cfg, i):
    m = cfg["mods"][i]
    m["enabled"] = not m.get("enabled", True)
    core.save_config(cfg)


def move_mod(cfg, i, delta):
    j = i + delta
    if 0 <= j < len(cfg["mods"]):
        cfg["mods"][i], cfg["mods"][j] = cfg["mods"][j], cfg["mods"][i]
        core.save_config(cfg)
        return j
    return i


def toggle_category(cfg, i):
    m = cfg["mods"][i]
    current = m.get("category") or core.mod_category(m.get("targets") or [])
    m["category"] = "gameplay" if current == "visual" else "visual"
    core.save_config(cfg)
    return m["category"]
