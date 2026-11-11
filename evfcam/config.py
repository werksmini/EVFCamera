"""Fixed settings for the hardware. User-adjustable settings arrive in milestone 2 (settings.py)."""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # Where the preview window sits on the screen, and its size (= overlay size).
    # Bench: Waveshare 10.4" 1600x720, flipped 180 deg, 4:3 window in the middle.
    win_x: int = 320
    win_y: int = 0
    win_w: int = 960
    win_h: int = 720
    flip: bool = True                     # bench monitor is mounted upside down

    preview_size: tuple = (1280, 960)     # camera stream for the preview
    sensor_mode: tuple = (2028, 1520)     # full sensor, binned: preview framing = photo framing
    photos_dir: str = os.path.expanduser("~/evfpi/photos")
    shutter_gpio: int = 27                # header pin 13; other leg to GND (pin 14)

    zoom_levels: tuple = (5, 10)          # Magnify mode steps
    in_focus: float = 0.95                # focus square goes green within 95% of peak sharpness
    peak_decay: float = 0.999             # how fast the "best focus" mark forgets
    redraw_s: float = 0.2                 # overlay refresh interval

    menu_pages: list = field(default_factory=lambda: [
        "Shooting", "Exposure", "Colour", "Lens", "Display", "Setup"])


def bench() -> Config:
    return Config()


def evf() -> Config:
    """The 0.4" EVF: 1280x960, filled edge to edge, not flipped."""
    return Config(win_x=0, win_y=0, win_w=1280, win_h=960, flip=False)
