"""Mode, menu and settings logic, run with the fake camera:  python3 tests/test_modes.py"""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evfcam import config, menu                 # noqa: E402
from evfcam.actions import A                    # noqa: E402
from evfcam.app import App                      # noqa: E402
from evfcam.camcore import FakeCamera, aspect_rect   # noqa: E402
from evfcam.inputs import split_keys            # noqa: E402
from evfcam.settings import Settings            # noqa: E402


def make_app(settings_path=None, **settings):
    cfg = config.bench()
    tmp = tempfile.mkdtemp()
    cfg.photos_dir = os.path.join(tmp, "photos")
    cfg.settings_path = settings_path or os.path.join(tmp, "settings.json")
    if settings:
        st = Settings(**settings)
        st.save(cfg.settings_path)
    return App(cfg, FakeCamera(cfg))


def press(app, *actions):
    for a in actions:
        app.handle(a)
    app.draw()


def open_item(app, page_title, label):
    """Navigate the menu to an item, from Shoot mode."""
    press(app, A.MENU)
    while menu.PAGES[app.mode.page_cursor].title != page_title:
        press(app, A.DOWN)
    press(app, A.OK)
    while app.mode.page.items[app.mode.item_cursor].label != label:
        press(app, A.DOWN)


# --- milestone 1 behaviour -------------------------------------------------------------
def test_starts_in_shoot_and_draws():
    app = make_app()
    app.draw()
    assert app.mode.name == "shoot"
    assert app.cam.last_overlay.shape == (720, 960, 4)


def test_shutter_saves_photo_and_same_second_names_dont_collide():
    app = make_app()
    press(app, A.SHUTTER_FULL, A.SHUTTER_FULL)
    assert len(os.listdir(app.cfg.photos_dir)) == 2


def test_magnify_cycles_and_exits():
    app = make_app()
    press(app, A.OK)
    assert app.mode.name == "magnify" and app.cam.zoom == 5
    press(app, A.OK)
    assert app.cam.zoom == 10
    press(app, A.OK)
    assert app.mode.name == "shoot" and app.cam.zoom == 1


def test_playback_browses_and_returns():
    app = make_app()
    press(app, A.SHUTTER_FULL, A.SHUTTER_FULL, A.PLAY)
    assert app.mode.name == "playback" and len(app.mode.files) == 2 and app.mode.index == 1
    press(app, A.LEFT)
    assert app.mode.index == 0
    press(app, A.PLAY)
    assert app.mode.name == "shoot"


def test_capture_flash_shown_before_capture():
    app = make_app()
    shown = []
    real_capture = app.cam.capture
    app.cam.capture = lambda path: (shown.append(app.cam.last_overlay[5, 5].tolist()), real_capture(path))[1]
    press(app, A.SHUTTER_FULL)
    assert shown and shown[0][3] == 255
    assert app.mode.name == "shoot"              # review is off by default


def test_quit_and_key_split():
    app = make_app()
    app.handle(A.QUIT)
    assert not app.running
    assert list(split_keys("\x1b[Aq \x1b[D")) == ["\x1b[A", "q", " ", "\x1b[D"]


# --- milestone 2: menu and settings ----------------------------------------------------------
def test_menu_pages_and_items():
    app = make_app()
    open_item(app, "Colour", "Black and white")
    assert app.mode.page.title == "Colour"
    press(app, A.RIGHT)                          # right = On
    assert app.settings.mono is True and app.cam.controls["Saturation"] == 0.0
    press(app, A.LEFT)
    assert app.settings.mono is False and app.cam.controls["Saturation"] == 1.0
    press(app, A.OK)                             # OK steps it round
    assert app.settings.mono is True
    press(app, A.BACK)
    assert app.mode.page is None
    press(app, A.SHUTTER_HALF)
    assert app.mode.name == "shoot"


def test_menu_change_applies_and_saves():
    app = make_app()
    open_item(app, "Exposure", "Mode")
    press(app, A.RIGHT, A.RIGHT)                 # Auto -> Shutter -> Manual
    assert app.settings.exp_mode == "Manual"
    c = app.cam.controls
    assert c["ExposureTimeMode"] == "Manual" and c["AnalogueGainMode"] == "Manual"
    assert c["AnalogueGain"] == app.settings.iso / 100
    press(app, A.MENU)                           # closing the menu saves
    with open(app.cfg.settings_path) as f:
        assert json.load(f)["exp_mode"] == "Manual"


def test_settings_survive_restart_and_bad_values_are_ignored():
    app = make_app(aspect="3:2", wb="Cloudy")
    assert app.settings.aspect == "3:2" and app.cam.still["size"] == (4056, 2704)
    with open(app.cfg.settings_path, "w") as f:
        json.dump({"aspect": "5:4", "wb": "Daylight"}, f)
    app2 = make_app(settings_path=app.cfg.settings_path)
    assert app2.settings.aspect == "4:3"         # not a menu value: default kept
    assert app2.settings.wb == "Daylight"


def test_wheel_does_ev_in_auto_and_shutter_in_manual():
    app = make_app()
    press(app, A.DIAL_UP, A.DIAL_UP, A.DIAL_UP)
    assert app.settings.ev == 1.0 and app.cam.ev == 1.0
    press(app, A.BACK)
    assert app.settings.ev == 0
    app2 = make_app(exp_mode="Manual", shutter_us=8000, iso=200)
    press(app2, A.DIAL_UP)                       # faster
    assert app2.settings.shutter_us == 4000 and app2.cam.controls["ExposureTime"] == 4000
    press(app2, A.UP)
    assert app2.settings.iso == 400


def test_long_shutter_slows_preview():
    app = make_app(exp_mode="Shutter", shutter_us=250000)
    assert app.cam.controls["FrameDurationLimits"][1] == 250000
    assert app.cam.controls["AnalogueGainMode"] == "Auto"


def test_raw_plus_jpeg_writes_two_files():
    app = make_app(file_format="RAW+JPEG")
    press(app, A.SHUTTER_FULL)
    names = sorted(os.listdir(app.cfg.photos_dir))
    assert len(names) == 2 and names[0].endswith(".dng") and names[1].endswith(".jpg")


def test_review_setting():
    app = make_app(review_s=0.5)
    press(app, A.SHUTTER_FULL)
    assert app.mode.name == "review"
    time.sleep(0.55)
    app.switch(app.mode.tick())
    assert app.mode.name == "shoot"
    press(app, A.SHUTTER_FULL, A.DOWN)           # any control ends review early
    assert app.mode.name == "shoot"


def test_reset_action():
    app = make_app(mono=True, aspect="1:1")
    open_item(app, "Setup", "Reset all settings")
    press(app, A.OK)
    assert app.settings == Settings()
    assert app.cam.still["size"] == (4056, 3040)


def test_aspect_rect():
    assert aspect_rect((0, 0, 4056, 3040), "1:1") == (508, 0, 3040, 3040)
    assert aspect_rect((0, 0, 4056, 3040), "16:9") == (0, 380, 4056, 2280)


def test_every_menu_page_renders():
    app = make_app()
    press(app, A.MENU)
    for _ in menu.PAGES:
        press(app, A.OK)
        for _ in app.mode.page.items:
            press(app, A.DOWN)
        press(app, A.BACK, A.DOWN)


if __name__ == "__main__":
    import io
    import contextlib
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            with contextlib.redirect_stdout(io.StringIO()):
                fn()
            print("ok", name)
