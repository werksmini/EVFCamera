"""The camera's modes. Each mode decides what every action does and what the overlay shows.

    Shoot     live view; shutter takes a photo; thumb wheel = EV (Auto) or shutter (S, M)
    Magnify   5x / 10x centre crop for focusing
    Menu      settings pages
    Playback  review photos
"""
import os
import time

from PIL import Image

from . import menu
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

    def tick(self):
        """Called every loop. Return a mode name to switch on a timer, or None."""
        return None

    def render(self, md):
        raise NotImplementedError


class Shoot(Mode):
    name = "shoot"

    def on(self, a):
        app, st = self.app, self.app.settings
        if a == A.SHUTTER_FULL:
            app.take_photo()
        elif a == A.OK:
            return "magnify"
        elif a == A.MENU:
            return "menu"
        elif a == A.PLAY:
            return "playback"
        elif a in (A.DIAL_UP, A.DIAL_DOWN):
            # thumb wheel: EV in Auto, shutter speed in Shutter and Manual
            d = 1 if a == A.DIAL_UP else -1
            if st.exp_mode == "Auto":
                app.change("ev", d)                     # shown in the top bar
            else:
                app.change("shutter_us", -d)            # wheel right = faster
        elif a in (A.UP, A.DOWN) and st.exp_mode == "Manual":
            app.change("iso", 1 if a == A.UP else -1)
        elif a == A.BACK and st.ev and st.exp_mode != "Manual":
            st.ev = 0.0
            app.settings_changed("ev")
        return None

    def render(self, md):
        return self.app.ui.shoot(md, self.app.focus, self.app.settings, self.app.tags())


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
        return self.app.ui.magnify(md, self.app.focus, self.zoom, self.app.settings)


class Menu(Mode):
    """Two levels: the list of pages, then the items on one page.

    Pages:  Up/Down move, OK or Right opens, Back/Left/Menu closes.
    Items:  Up/Down move, Left/Right or the thumb wheel change the value, OK steps it
            (or runs an action), Back goes up to the pages, Menu closes.
    """
    name = "menu"

    def enter(self):
        self.page_cursor = getattr(self, "page_cursor", 0)    # remember where you were
        self.page = None
        self.item_cursor = 0

    def leave(self):
        self.app.save_settings()

    def on(self, a):
        if a in (A.SHUTTER_HALF, A.SHUTTER_FULL):
            return "shoot"                                    # half-press always leaves menus
        if self.page is None:
            n = len(menu.PAGES)
            if a == A.UP:
                self.page_cursor = (self.page_cursor - 1) % n
            elif a == A.DOWN:
                self.page_cursor = (self.page_cursor + 1) % n
            elif a in (A.OK, A.RIGHT):
                self.page, self.item_cursor = menu.PAGES[self.page_cursor], 0
            elif a in (A.MENU, A.BACK, A.LEFT):
                return "shoot"
            return None

        items = self.page.items
        item = items[self.item_cursor]
        if a == A.UP:
            self.item_cursor = (self.item_cursor - 1) % len(items)
        elif a == A.DOWN:
            self.item_cursor = (self.item_cursor + 1) % len(items)
        elif a in (A.LEFT, A.RIGHT, A.DIAL_UP, A.DIAL_DOWN) and item.kind == "choice":
            self.app.change(item.key, 1 if a in (A.RIGHT, A.DIAL_UP) else -1)
        elif a == A.OK and item.kind == "choice":
            self.app.change(item.key, 0, wrap=True)
        elif a == A.OK and item.kind == "action":
            self.app.run_action(item.action)
        elif a == A.BACK:
            self.page = None
        elif a == A.MENU:
            return "shoot"
        return None

    def render(self, md):
        ui = self.app.ui
        if self.page is None:
            rows = [(p.title, "", "page") for p in menu.PAGES]
            hint = "Up/Down = move   OK = open   Back = close"
            return ui.menu("MENU", rows, self.page_cursor, hint)
        rows = [(it.label, menu.display(self.app, it), it.kind) for it in self.page.items]
        hint = "Up/Down = move   Left/Right or wheel = change   Back = up"
        return ui.menu(f"MENU  >  {self.page.title}", rows, self.item_cursor, hint)


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


class Review(Mode):
    """The shot just taken, for a moment after saving (off unless review_s > 0)."""
    name = "review"

    def show(self, frame, name, seconds):
        self.frame, self.photo_name = frame, name
        self.until = time.monotonic() + seconds

    def tick(self):
        return "shoot" if time.monotonic() >= self.until else None

    def on(self, a):
        if a == A.PLAY:
            return "playback"
        return "shoot"                 # any other control ends the review early

    def render(self, md):
        return self.app.ui.review(self.frame, self.photo_name)


MODES = (Shoot, Magnify, Menu, Playback, Review)
