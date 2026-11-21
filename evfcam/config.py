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
    # the Pi's internal pull-ups are used, so no resistors. Header pin in the comment.
    buttons: dict = field(default_factory=lambda: {
        5: "UP",            # pin 29  D-pad (Adafruit 504)
        6: "DOWN",          # pin 31
        13: "LEFT",         # pin 33
        19: "RIGHT",        # pin 35
        26: "OK",           # pin 37  D-pad press
        22: "BACK",         # pin 15
        23: "PLAY",         # pin 16
        21: "FN",           # pin 40
        17: "SHUTTER_HALF",  # pin 11
        27: "SHUTTER_FULL",  # pin 13
        24: "DIAL_DOWN",    # pin 18  thumb jog left (SparkFun 08184)
        25: "DIAL_UP",      # pin 22  thumb jog right
        18: "MENU",         # pin 12  thumb jog press
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
