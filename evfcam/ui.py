"""Draws the viewfinder overlay. Everything is a transparent RGBA image laid over the preview;
an opaque image (Playback, Menu background) hides the preview behind it."""
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WHITE = (255, 255, 255, 255)
GREY = (170, 170, 170, 255)
YELLOW = (255, 210, 0, 255)
GREEN = (60, 220, 90, 255)
RED = (235, 60, 50, 255)
BAR = (0, 0, 0, 150)
PANEL = (12, 12, 14, 255)       # Menu and Playback hide the preview completely
SELECT = (58, 58, 64, 255)
SOLID_BAR = (16, 16, 18, 255)


def load_font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def shutter_txt(us):
    if not us:
        return "--"
    s = us / 1_000_000
    return f"1/{round(1 / s)}" if s < 0.5 else f"{s:.1f}s"


class UI:
    def __init__(self, cfg):
        self.cfg = cfg
        self.W, self.H = cfg.win_w, cfg.win_h
        k = self.H / 720                         # scale text to the screen
        self.big = load_font(int(30 * k))
        self.mid = load_font(int(24 * k))
        self.small = load_font(int(20 * k))
        self.bar_h = int(48 * k)
        self._toast, self._toast_until = "", 0.0

    # --- helpers ----------------------------------------------------------------------
    def canvas(self, fill=(0, 0, 0, 0)):
        img = Image.new("RGBA", (self.W, self.H), fill)
        return img, ImageDraw.Draw(img)

    def toast(self, text, seconds=1.5):
        self._toast, self._toast_until = text, time.monotonic() + seconds

    def clear_toast(self):
        self._toast_until = 0.0

    def finish(self, img) -> np.ndarray:
        if time.monotonic() < self._toast_until:
            d = ImageDraw.Draw(img)
            cx = self.W // 2
            y = self.bar_h + 22
            tw = d.textlength(self._toast, font=self.small)
            d.rectangle([cx - tw / 2 - 20, y, cx + tw / 2 + 20, y + 50], fill=(0, 0, 0, 190))
            d.text((cx, y + 25), self._toast, font=self.small, fill=GREEN, anchor="mm")
        if self.cfg.flip:
            img = img.rotate(180)
        return np.asarray(img)

    def _top_bar(self, d, md, ev):
        W = self.W
        d.rectangle([0, 0, W, self.bar_h], fill=BAR)
        y = self.bar_h // 2
        gain = md.get("AnalogueGain", 1.0) * md.get("DigitalGain", 1.0)
        d.text((16, y), shutter_txt(md.get("ExposureTime")), font=self.big, fill=WHITE, anchor="lm")
        d.text((W * 0.19, y), f"ISO {round(gain * 100)}", font=self.big, fill=WHITE, anchor="lm")
        d.text((W * 0.40, y), f"{md.get('ColourTemperature', 0)}K", font=self.big, fill=WHITE, anchor="lm")
        if ev:
            # Heuristic: the auto exposure only adds digital gain once shutter and analogue gain
            # are maxed out, so more +EV can't brighten the picture any further.
            limit = ev > 0 and md.get("DigitalGain", 1.0) > 1.1
            d.text((W * 0.58, y), f"{ev:+.1f} EV" + (" MAX" if limit else ""), font=self.big,
                   fill=RED if limit else YELLOW, anchor="lm")
        locked = md.get("AeLocked", False)
        d.text((W - 16, y), "AE LOCK" if locked else "AE", font=self.big,
               fill=GREEN if locked else WHITE, anchor="rm")

    def _bottom_bar(self, d, md, mode_txt, focus, label=None):
        W, H = self.W, self.H
        d.rectangle([0, H - self.bar_h, W, H], fill=BAR)
        y = H - self.bar_h // 2
        fps = 1_000_000 / md["FrameDuration"] if md.get("FrameDuration") else 0
        text = label or f"{mode_txt}   {fps:.0f} fps   {md.get('Lux', 0):.0f} lux"
        d.text((16, y), text, font=self.small, fill=WHITE, anchor="lm")
        level, in_focus = focus
        bx0, bx1 = W - 316, W - 16
        d.text((bx0 - 12, y), "FOCUS", font=self.small, fill=WHITE, anchor="rm")
        d.rectangle([bx0, y - 8, bx1, y + 8], outline=WHITE, width=1)
        d.rectangle([bx0, y - 8, bx0 + int((bx1 - bx0) * level), y + 8],
                    fill=GREEN if in_focus else YELLOW)

    def _focus_square(self, d, in_focus, size=18):
        cx, cy = self.W // 2, self.H // 2
        d.rectangle([cx - size, cy - size, cx + size, cy + size],
                    outline=GREEN if in_focus else WHITE, width=3)

    # --- screens -----------------------------------------------------------------------
    def shoot(self, md, mode_txt, focus, ev):
        img, d = self.canvas()
        self._top_bar(d, md, ev)
        self._focus_square(d, focus[1])
        self._bottom_bar(d, md, mode_txt, focus)
        return img

    def magnify(self, md, focus, zoom):
        img, d = self.canvas()
        self._top_bar(d, md, 0)
        # corner brackets show you're looking at a crop, not the whole frame
        m, L = 24, 60
        for x, y, sx, sy in ((m, self.bar_h + m, 1, 1), (self.W - m, self.bar_h + m, -1, 1),
                             (m, self.H - self.bar_h - m, 1, -1),
                             (self.W - m, self.H - self.bar_h - m, -1, -1)):
            d.line([(x, y), (x + sx * L, y)], fill=WHITE, width=3)
            d.line([(x, y), (x, y + sy * L)], fill=WHITE, width=3)
        self._bottom_bar(d, md, "", focus, label=f"MAGNIFY {zoom}x    OK = next    Back = exit")
        return img

    def menu(self, pages, cursor, open_page):
        img, d = self.canvas(PANEL)
        W, H = self.W, self.H
        title = "MENU" if open_page is None else f"MENU  >  {pages[open_page]}"
        d.text((32, 30), title, font=self.big, fill=WHITE)
        d.line([(32, 78), (W - 32, 78)], fill=GREY, width=1)
        row_h = int(H * 0.085)
        if open_page is None:
            for i, name in enumerate(pages):
                y = 100 + i * row_h
                if i == cursor:
                    d.rectangle([24, y, W - 24, y + row_h - 8], fill=SELECT)
                d.text((48, y + (row_h - 8) // 2), name, font=self.mid,
                       fill=WHITE if i == cursor else GREY, anchor="lm")
                d.text((W - 48, y + (row_h - 8) // 2), ">", font=self.mid, fill=GREY, anchor="rm")
        else:
            d.text((48, 120), "Settings for this page arrive in milestone 2.", font=self.mid, fill=GREY)
        hint = "Up/Down = move   OK = open   Back = up a level   Menu = close"
        d.text((32, H - 40), hint, font=self.small, fill=GREY, anchor="lm")
        return img

    def capture_flash(self):
        """Shown from the shutter press until the photo is saved: dark screen, white border."""
        img, d = self.canvas((0, 0, 0, 255))
        b = max(6, self.W // 120)
        d.rectangle([b // 2, b // 2, self.W - b // 2, self.H - b // 2], outline=WHITE, width=b)
        r = 9
        d.ellipse([self.W - 40 - r, 30 - r, self.W - 40 + r, 30 + r], fill=RED)
        return img

    def review(self, frame, name):
        """The frame grabbed at the shutter press, shown briefly after saving."""
        img, d = self.canvas((0, 0, 0, 255))
        frame = frame.copy()
        frame.thumbnail((self.W, self.H))
        img.paste(frame, ((self.W - frame.width) // 2, (self.H - frame.height) // 2))
        d = ImageDraw.Draw(img)
        d.rectangle([0, self.H - self.bar_h, self.W, self.H], fill=SOLID_BAR)
        d.text((16, self.H - self.bar_h // 2), "SAVED " + name, font=self.small, fill=GREEN, anchor="lm")
        return img

    def playback(self, photo, index, count, name):
        img, d = self.canvas((0, 0, 0, 255))
        if photo is None:
            d.text((self.W // 2, self.H // 2), "No photos yet", font=self.big, fill=GREY, anchor="mm")
        else:
            img.paste(photo, ((self.W - photo.width) // 2, (self.H - photo.height) // 2))
            d = ImageDraw.Draw(img)
            d.rectangle([0, self.H - self.bar_h, self.W, self.H], fill=SOLID_BAR)
            y = self.H - self.bar_h // 2
            d.text((16, y), f"{index + 1} / {count}", font=self.small, fill=WHITE, anchor="lm")
            d.text((self.W - 16, y), name, font=self.small, fill=WHITE, anchor="rm")
        d.text((16, 16), "PLAY", font=self.mid, fill=GREEN)
        return img
