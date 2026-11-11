"""The camera's modes. Each mode decides what every action does and what the overlay shows.

    Shoot     live view; shutter takes a photo; thumb wheel = exposure compensation
    Magnify   5x / 10x centre crop for focusing
    Menu      settings pages (contents arrive in milestone 2)
    Playback  review photos
"""
import os

from PIL import Image

from .actions import A


class Mode:
    name = ""

    def __init__(self, app):
        self.app = app

    def enter(self):
        pass

    def leave(self):
        pass

    def on(self, action):
        """Handle one action. Return the name of a mode to switch to, or None to stay."""
        return None

    def render(self, md):
        raise NotImplementedError


class Shoot(Mode):
    name = "shoot"

    def on(self, a):
        app = self.app
        if a == A.SHUTTER_FULL:
            app.take_photo()
        elif a == A.OK:
            return "magnify"
        elif a == A.MENU:
            return "menu"
        elif a == A.PLAY:
            return "playback"
        elif a in (A.DIAL_UP, A.DIAL_DOWN):
            step = 1 / 3 if a == A.DIAL_UP else -1 / 3
            app.ev = max(-3.0, min(3.0, round((app.ev + step) * 3) / 3))
            app.cam.set_ev(app.ev)
            app.ui.toast(f"EV {app.ev:+.1f}", 0.8)
        elif a == A.BACK and app.ev:
            app.ev = 0.0
            app.cam.set_ev(0.0)
            app.ui.toast("EV reset", 0.8)
        return None

    def render(self, md):
        return self.app.ui.shoot(md, self.app.cam.mode_txt, self.app.focus, self.app.ev)


class Magnify(Mode):
    name = "magnify"

    def enter(self):
        self.step = 0
        self.app.cam.set_zoom(self.zoom)

    def leave(self):
        self.app.cam.set_zoom(1)

    @property
    def zoom(self):
        return self.app.cfg.zoom_levels[self.step]

    def on(self, a):
        if a == A.OK:
            self.step += 1
            if self.step >= len(self.app.cfg.zoom_levels):
                return "shoot"
            self.app.cam.set_zoom(self.zoom)
        elif a in (A.BACK, A.MENU, A.SHUTTER_HALF):
            return "shoot"
        elif a == A.SHUTTER_FULL:
            self.app.take_photo()                   # capture resets the crop to the full frame
            return "shoot"
        elif a == A.PLAY:
            return "playback"
        return None

    def render(self, md):
        return self.app.ui.magnify(md, self.app.focus, self.zoom)


class Menu(Mode):
    name = "menu"

    def enter(self):
        self.cursor = getattr(self, "cursor", 0)    # remember the last page
        self.open_page = None

    def on(self, a):
        pages = self.app.cfg.menu_pages
        if a in (A.SHUTTER_HALF, A.SHUTTER_FULL):
            return "shoot"                          # like a real camera: half-press leaves menus
        if self.open_page is None:
            if a == A.UP:
                self.cursor = (self.cursor - 1) % len(pages)
            elif a == A.DOWN:
                self.cursor = (self.cursor + 1) % len(pages)
            elif a in (A.OK, A.RIGHT):
                self.open_page = self.cursor
            elif a in (A.MENU, A.BACK, A.LEFT):
                return "shoot"
        else:
            if a in (A.BACK, A.LEFT):
                self.open_page = None
            elif a == A.MENU:
                return "shoot"
        return None

    def render(self, md):
        return self.app.ui.menu(self.app.cfg.menu_pages, self.cursor, self.open_page)


class Playback(Mode):
    name = "playback"

    def enter(self):
        d = self.app.cfg.photos_dir
        self.files = sorted(f for f in os.listdir(d) if f.lower().endswith(".jpg")) if os.path.isdir(d) else []
        self.index = len(self.files) - 1            # start on the newest photo
        self._cache = (None, None)

    def on(self, a):
        if a in (A.PLAY, A.BACK, A.MENU, A.SHUTTER_HALF, A.SHUTTER_FULL):
            return "shoot"
        if self.files and a in (A.LEFT, A.DIAL_DOWN):
            self.index = (self.index - 1) % len(self.files)
        elif self.files and a in (A.RIGHT, A.DIAL_UP):
            self.index = (self.index + 1) % len(self.files)
        return None

    def _photo(self):
        if not self.files:
            return None
        name = self.files[self.index]
        if self._cache[0] != name:
            ui = self.app.ui
            im = Image.open(os.path.join(self.app.cfg.photos_dir, name))
            im.draft("RGB", (ui.W, ui.H))           # JPEG decodes straight to a small size: fast
            im = im.convert("RGBA")
            im.thumbnail((ui.W, ui.H))
            self._cache = (name, im)
        return self._cache[1]

    def render(self, md):
        photo = self._photo()
        name = self.files[self.index] if self.files else ""
        return self.app.ui.playback(photo, self.index, len(self.files), name)


MODES = (Shoot, Magnify, Menu, Playback)
