"""The menu, written as data. Each setting is one Item; the Menu mode and UI draw every page the same way.

Item kinds:
    choice  a setting with a list of values (changed with left/right or the thumb wheel)
    info    read-only line, e.g. free space
    action  runs something when you press OK, e.g. reset
"""
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from . import __version__

SHUTTERS = [250, 500, 1000, 2000, 4000, 8000, 16667, 33333, 66667, 125000, 250000, 500000, 1000000]
ISOS = [100, 200, 400, 800, 1600]
EVS = [round(i / 3, 2) for i in range(-9, 10)]
STEPS = [-2, -1, 0, 1, 2]
ON_OFF = [False, True]                       # right = On


def shutter_label(us):
    s = us / 1_000_000
    return f"1/{round(1 / s)}" if s < 0.5 else f"{s:g} s"


def ev_label(v):
    return "0" if v == 0 else f"{v:+.1f}"


def step_label(v):
    return "0" if v == 0 else f"{v:+d}"


def on_off(v):
    return "On" if v else "Off"


def review_label(v):
    return "Off" if v == 0 else f"{v:g} s"


@dataclass
class Item:
    label: str
    key: str = ""                              # Settings field, for choice items
    values: list = field(default_factory=list)
    fmt: Callable = str
    kind: str = "choice"
    info: Optional[Callable] = None            # info items: app -> text
    action: str = ""                           # action items: name handled by the app


@dataclass
class Page:
    title: str
    items: list


def _free_space(app):
    try:
        u = shutil.disk_usage(app.cfg.photos_dir)
        return f"{u.free / 1e9:.1f} GB free"
    except OSError:
        return "?"


def _photo_count(app):
    d = app.cfg.photos_dir
    return str(sum(f.lower().endswith(".jpg") for f in os.listdir(d))) if os.path.isdir(d) else "0"


PAGES = [
    Page("Shooting", [
        Item("File format", "file_format", ["JPEG", "RAW+JPEG"]),
        Item("JPEG quality", "jpeg_quality", [75, 85, 90, 93, 95, 98]),
        Item("Aspect ratio", "aspect", ["4:3", "3:2", "1:1", "16:9"]),
    ]),
    Page("Exposure", [
        Item("Mode", "exp_mode", ["Auto", "Shutter", "Manual"]),
        Item("Shutter speed", "shutter_us", SHUTTERS, shutter_label),
        Item("ISO", "iso", ISOS),
        Item("Exposure comp.", "ev", EVS, ev_label),
        Item("Metering", "metering", ["Centre", "Spot", "Average"]),
    ]),
    Page("Colour", [
        Item("White balance", "wb", ["Auto", "Daylight", "Cloudy", "Tungsten", "Fluorescent", "Indoor"]),
        Item("Contrast", "contrast", STEPS, step_label),
        Item("Saturation", "saturation", STEPS, step_label),
        Item("Sharpness", "sharpness", STEPS, step_label),
        Item("Black and white", "mono", ON_OFF, on_off),
    ]),
    Page("Lens", [
        Item("Lens", "lens", ["9 mm f/1.4", "17 mm f/1.7", "Other"]),
        Item("Note", kind="info", info=lambda app: "Saved into photos in milestone 4"),
    ]),
    Page("Display", [
        Item("Capture flash", "capture_flash", ON_OFF, on_off),
        Item("Review after shot", "review_s", [0.0, 0.5, 1.0, 2.0], review_label),
        Item("Focus square", "focus_square", ON_OFF, on_off),
        Item("Focus bar", "focus_bar", ON_OFF, on_off),
        Item("Info shown", "info", ["Full", "Minimal"]),
    ]),
    Page("Setup", [
        Item("Date and time", kind="info", info=lambda app: datetime.now().strftime("%Y-%m-%d %H:%M")),
        Item("Storage", kind="info", info=_free_space),
        Item("Photos", kind="info", info=_photo_count),
        Item("Version", kind="info", info=lambda app: f"evfcam {__version__}"),
        Item("Reset all settings", kind="action", action="reset"),
    ]),
]

ITEMS = {it.key: it for p in PAGES for it in p.items if it.kind == "choice"}


def valid(key, value):
    it = ITEMS.get(key)
    return it is not None and value in it.values


def step(settings, key, delta):
    """Move a setting delta places along its list of values (stops at the ends). Returns the new value."""
    it = ITEMS[key]
    vals = it.values
    cur = getattr(settings, key)
    i = vals.index(cur) if cur in vals else 0
    new = vals[max(0, min(len(vals) - 1, i + delta))]
    setattr(settings, key, new)
    return new


def cycle(settings, key):
    """Next value, wrapping round (for OK on a setting)."""
    it = ITEMS[key]
    vals = it.values
    cur = getattr(settings, key)
    new = vals[(vals.index(cur) + 1) % len(vals)] if cur in vals else vals[0]
    setattr(settings, key, new)
    return new


def display(app, item):
    """The value text shown for an item."""
    if item.kind == "choice":
        return item.fmt(getattr(app.settings, item.key))
    if item.kind == "info":
        return item.info(app)
    return ""
