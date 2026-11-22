"""Fixed settings for the hardware. Everything the user can change lives in settings.py."""
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
    # Physical buttons: BCM GPIO -> action name (evfcam.actions.A). Each switch closes to ground;
    # the Pi's internal pull-ups are used, so no resistors. MVP milled board: every button is on
    # the header's outer row (even pins), so the single-sided board breaks them all out on one side.
    # Left to right along the header (pin 1 at the SD-card end).
    buttons: dict = field(default_factory=lambda: {
        18: "FN",           # pin 12  upper left; does what Setup > Fn button says (default Magnify)
        23: "MENU",         # pin 16
        24: "PLAY",         # pin 18  also Back inside the menu
        25: "UP",           # pin 22  D-pad (Adafruit 504)
        8: "LEFT",          # pin 24  (SPI CE0: keep SPI off)
        7: "DOWN",          # pin 26  (SPI CE1)
        12: "RIGHT",        # pin 32
        16: "OK",           # pin 36  D-pad press: magnify
        21: "SHUTTER_FULL",  # pin 40  right of the D-pad; single-stage for now
    })

    zoom_levels: tuple = (5, 10)          # Magnify mode steps
    in_focus: float = 0.95                # focus square goes green within 95% of peak sharpness
    peak_decay: float = 0.999             # how fast the "best focus" mark forgets
    redraw_s: float = 0.2                 # overlay refresh interval
    settings_path: str = os.path.expanduser("~/.config/evfcam/settings.json")



def bench() -> Config:
    return Config()


def evf() -> Config:
    """The 0.4" EVF: 1280x960, filled edge to edge, not flipped."""
    return Config(win_x=0, win_y=0, win_w=1280, win_h=960, flip=False)
