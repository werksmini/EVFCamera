"""Main loop: take actions off the queue, give them to the current mode, redraw the overlay."""
import os
import queue
import time
from datetime import datetime

from .actions import A
from .modes import MODES
from .ui import UI


class App:
    def __init__(self, cfg, cam, q=None):
        self.cfg = cfg
        self.cam = cam
        self.q = q or queue.Queue()
        self.ui = UI(cfg)
        self.ev = 0.0
        self.peak = 1.0
        self.focus = (0.0, False)          # (level 0..1, in focus?)
        self.running = True
        self.modes = {m.name: m(self) for m in MODES}
        self.mode = self.modes["shoot"]
        self.mode.enter()
        os.makedirs(cfg.photos_dir, exist_ok=True)

    def switch(self, name):
        if name and name != self.mode.name:
            self.mode.leave()
            if name in ("menu", "playback", "review"):
                self.ui.clear_toast()             # messages belong to the live view
            self.mode = self.modes[name]
            self.mode.enter()

    def handle(self, action):
        if action == A.QUIT:
            self.running = False
            return
        self.switch(self.mode.on(action))

    def take_photo(self):
        cfg = self.cfg
        stem = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, n = stem + ".jpg", 2
        while os.path.exists(os.path.join(cfg.photos_dir, name)):   # two shots in one second
            name, n = f"{stem}_{n}.jpg", n + 1
        path = os.path.join(cfg.photos_dir, name)

        frame = self.cam.grab_preview() if cfg.review_s > 0 else None   # free: already in memory
        if cfg.capture_flash:
            self.cam.show_overlay(self.ui.finish(self.ui.capture_flash()))
            self.cam.wait_frame()          # let the flash reach the screen before the preview freezes
        self.cam.capture(path)
        print("saved", path, flush=True)

        if frame is not None:
            self.modes["review"].show(frame, name, cfg.review_s)
            self.switch("review")
        else:
            self.ui.toast("SAVED " + name)

    def update_focus(self, md):
        fom = md.get("FocusFoM", 0)
        self.peak = max(self.peak * self.cfg.peak_decay, fom, 1)
        self.focus = (min(fom / self.peak, 1.0), fom >= self.cfg.in_focus * self.peak)

    def draw(self):
        md = self.cam.metadata()
        self.update_focus(md)
        self.cam.show_overlay(self.ui.finish(self.mode.render(md)))

    def run(self):
        last = 0.0
        while self.running:
            try:
                self.handle(self.q.get(timeout=0.05))
                while not self.q.empty():          # take everything that's waiting
                    self.handle(self.q.get_nowait())
                last = 0.0                         # redraw right away after input
            except queue.Empty:
                pass
            self.switch(self.mode.tick())
            if self.running and time.monotonic() - last >= self.cfg.redraw_s:
                self.draw()
                last = time.monotonic()
