"""Turns keys and buttons into actions on a queue.

Three sources, all optional, all feeding the same queue:
  - the SSH terminal you start the app from
  - any keyboard plugged into the Pi (and later the gpio-key / rotary-encoder controls)
  - the bench shutter button on a GPIO pin
"""
import os
import queue
import select
import sys
import termios
import threading
import tty

from .actions import A, EVDEV_KEYS, TERMINAL_KEYS


class Inputs:
    def __init__(self, q: queue.Queue, shutter_gpio=None):
        self.q = q
        self.shutter_gpio = shutter_gpio
        self._term_state = None
        self._stop = threading.Event()
        self._devices = []
        self._button = None
        self.sources = []

    def start(self):
        self._start_terminal()
        self._start_evdev()
        self._start_gpio()
        return self

    # --- SSH terminal --------------------------------------------------------------
    def _start_terminal(self):
        if not sys.stdin.isatty():
            return
        fd = sys.stdin.fileno()
        self._term_state = termios.tcgetattr(fd)
        tty.setcbreak(fd)                  # keys arrive immediately, without Enter
        threading.Thread(target=self._read_terminal, args=(fd,), daemon=True).start()
        self.sources.append("terminal")

    def _read_terminal(self, fd):
        while not self._stop.is_set():
            ready, _, _ = select.select([fd], [], [], 0.2)
            if not ready:
                continue
            data = os.read(fd, 32).decode(errors="ignore")
            for key in split_keys(data):
                action = TERMINAL_KEYS.get(key)
                if action:
                    self.q.put(action)

    # --- keyboards and (later) the camera's own buttons --------------------------
    def _start_evdev(self):
        try:
            import evdev
        except ImportError:
            return
        wanted = {evdev.ecodes.ecodes[name] for name in EVDEV_KEYS if name in evdev.ecodes.ecodes}
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                keys = set(dev.capabilities().get(evdev.ecodes.EV_KEY, []))
                if not keys & wanted:
                    continue
                try:
                    dev.grab()             # stop the keys also typing into the console login
                except OSError:
                    pass
            except (PermissionError, OSError):
                continue
            self._devices.append(dev)
            self.sources.append(dev.name)
            threading.Thread(target=self._read_evdev, args=(dev, evdev), daemon=True).start()

    def _read_evdev(self, dev, evdev):
        try:
            for ev in dev.read_loop():
                if ev.type != evdev.ecodes.EV_KEY or ev.value == 0:   # 1 = press, 2 = held
                    continue
                name = evdev.ecodes.KEY.get(ev.code)
                names = name if isinstance(name, list) else [name]
                for n in names:
                    action = EVDEV_KEYS.get(n)
                    if action and not (ev.value == 2 and action in (A.SHUTTER_FULL, A.QUIT)):
                        self.q.put(action)
                        break
        except OSError:
            pass                           # device unplugged

    # --- bench shutter button ---------------------------------------------------------
    def _start_gpio(self):
        if self.shutter_gpio is None:
            return
        try:
            from gpiozero import Button
            self._button = Button(self.shutter_gpio, pull_up=True, bounce_time=0.05)
            self._button.when_pressed = lambda: self.q.put(A.SHUTTER_FULL)
            self.sources.append(f"GPIO {self.shutter_gpio} shutter")
        except Exception as e:             # not on a Pi, or pin busy
            print(f"shutter button not available: {e}")

    def close(self):
        self._stop.set()
        if self._term_state is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._term_state)
        for dev in self._devices:
            try:
                dev.ungrab()
            except OSError:
                pass
        if self._button:
            self._button.close()


def split_keys(data: str):
    """Split terminal input into keys; arrow keys arrive as 3-character escape sequences."""
    i = 0
    while i < len(data):
        if data.startswith("\x1b[", i) and i + 2 < len(data):
            yield data[i:i + 3]
            i += 3
        else:
            yield data[i]
            i += 1
