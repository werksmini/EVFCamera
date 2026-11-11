"""Save a PNG of every screen, drawn over a test image, for checking the UI without a Pi.

    python3 tools/render_screens.py [--evf] [outdir]
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np                              # noqa: E402
from PIL import Image                           # noqa: E402

from evfcam import config                       # noqa: E402
from evfcam.actions import A                    # noqa: E402
from evfcam.app import App                      # noqa: E402
from evfcam.camcore import FakeCamera           # noqa: E402

evf = "--evf" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
out = args[0] if args else "screens"
os.makedirs(out, exist_ok=True)

cfg = config.evf() if evf else config.bench()
cfg.flip = False                                # draw upright for viewing
cfg.photos_dir = tempfile.mkdtemp()
cfg.settings_path = os.path.join(cfg.photos_dir, "settings.json")
app = App(cfg, FakeCamera(cfg))

# backdrop standing in for the live preview
W, H = cfg.win_w, cfg.win_h
yy, xx = np.mgrid[0:H, 0:W]
backdrop = Image.fromarray(np.dstack([(80 + 60 * np.sin(xx / 90)).astype(np.uint8),
                                      (90 + 50 * np.cos(yy / 70)).astype(np.uint8),
                                      np.full((H, W), 110, np.uint8)])).convert("RGBA")


def shot(name, *actions):
    for a in actions:
        app.handle(a)
    app.draw()
    frame = Image.alpha_composite(backdrop, Image.fromarray(app.cam.last_overlay))
    frame.convert("RGB").save(os.path.join(out, f"{name}.png"))
    print("wrote", name)


shot("01_shoot_auto")
shot("02_shoot_ev", A.DIAL_UP, A.DIAL_UP)
shot("03_magnify", A.OK)
shot("04_menu", A.BACK, A.MENU, A.DOWN)
shot("05_menu_exposure", A.OK, A.RIGHT, A.RIGHT, A.DOWN)       # Manual, cursor on shutter
shot("06_menu_display", A.BACK, A.DOWN, A.DOWN, A.DOWN, A.OK)
shot("07_menu_setup", A.BACK, A.DOWN, A.OK, A.DOWN, A.DOWN, A.DOWN, A.DOWN)
# Shooting page: 3:2; Colour page: B&W on
press_seq = [A.BACK, A.UP, A.UP, A.UP, A.UP, A.UP, A.OK, A.DOWN, A.DOWN, A.RIGHT, A.BACK,
             A.DOWN, A.DOWN, A.OK, A.UP, A.RIGHT, A.MENU]
shot("08_shoot_manual_32_bw", *press_seq)
app.cam.show_overlay(app.ui.finish(app.ui.capture_flash()))
Image.alpha_composite(backdrop, Image.fromarray(app.cam.last_overlay)).convert("RGB").save(
    os.path.join(out, "09_flash.png"))
shot("10_playback", A.SHUTTER_FULL, A.PLAY)
