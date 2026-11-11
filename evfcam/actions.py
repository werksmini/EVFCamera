"""Everything the camera's controls can ask for, and how keys map to it.

The real buttons and dials will be set up (milestone 5) to send the same Linux key codes
as the keyboard keys below, so the app never needs to know which one it's talking to.
"""
from enum import Enum, auto


class A(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    OK = auto()
    MENU = auto()
    BACK = auto()
    PLAY = auto()
    FN = auto()
    DIAL_UP = auto()
    DIAL_DOWN = auto()
    SHUTTER_HALF = auto()
    SHUTTER_FULL = auto()
    QUIT = auto()


# Keys typed in the SSH terminal.
TERMINAL_KEYS = {
    "\x1b[A": A.UP, "\x1b[B": A.DOWN, "\x1b[C": A.RIGHT, "\x1b[D": A.LEFT,
    "\r": A.OK, "\n": A.OK,
    " ": A.SHUTTER_FULL, "h": A.SHUTTER_HALF,
    "m": A.MENU, "p": A.PLAY, "f": A.FN,
    "\x7f": A.BACK, "\x08": A.BACK, "\x1b": A.BACK, "b": A.BACK,
    "[": A.DIAL_DOWN, "]": A.DIAL_UP, ",": A.DIAL_DOWN, ".": A.DIAL_UP,
    "q": A.QUIT,
}

# Linux key codes, from a USB keyboard plugged into the Pi (and later the gpio-key buttons).
EVDEV_KEYS = {
    "KEY_UP": A.UP, "KEY_DOWN": A.DOWN, "KEY_LEFT": A.LEFT, "KEY_RIGHT": A.RIGHT,
    "KEY_ENTER": A.OK, "KEY_KPENTER": A.OK,
    "KEY_SPACE": A.SHUTTER_FULL, "KEY_CAMERA": A.SHUTTER_FULL, "KEY_H": A.SHUTTER_HALF,
    "KEY_CAMERA_FOCUS": A.SHUTTER_HALF,
    "KEY_M": A.MENU, "KEY_MENU": A.MENU, "KEY_P": A.PLAY, "KEY_F": A.FN,
    "KEY_BACKSPACE": A.BACK, "KEY_ESC": A.BACK, "KEY_B": A.BACK,
    "KEY_LEFTBRACE": A.DIAL_DOWN, "KEY_RIGHTBRACE": A.DIAL_UP,
    "KEY_COMMA": A.DIAL_DOWN, "KEY_DOT": A.DIAL_UP,
    "KEY_Q": A.QUIT,
}

HELP = ("arrows = pad   Enter = OK   space = shutter   h = half-press   m = Menu   "
        "p = Play   b/Backspace = Back   [ ] = thumb wheel   f = Fn   q = quit")
