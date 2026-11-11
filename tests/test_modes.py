"""Mode and control logic, run with the fake camera:  python3 -m pytest tests  (or python3 tests/test_modes.py)"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evfcam import config                       # noqa: E402
from evfcam.actions import A                    # noqa: E402
from evfcam.app import App                      # noqa: E402
from evfcam.camcore import FakeCamera           # noqa: E402
from evfcam.inputs import split_keys            # noqa: E402


def make_app(**kw):
    cfg = config.bench()
    cfg.photos_dir = tempfile.mkdtemp()
    for k, v in kw.items():
        setattr(cfg, k, v)
    return App(cfg, FakeCamera(cfg))


def press(app, *actions):
    for a in actions:
        app.handle(a)
    app.draw()


def test_starts_in_shoot_and_draws():
    app = make_app()
    app.draw()
    assert app.mode.name == "shoot"
    assert app.cam.last_overlay.shape == (720, 960, 4)


def test_shutter_saves_photo():
    app = make_app()
    press(app, A.SHUTTER_FULL)
    assert len(os.listdir(app.cfg.photos_dir)) == 1


def test_magnify_cycles_and_exits():
    app = make_app()
    press(app, A.OK)
    assert app.mode.name == "magnify" and app.cam.zoom == 5
    press(app, A.OK)
    assert app.cam.zoom == 10
    press(app, A.OK)
    assert app.mode.name == "shoot" and app.cam.zoom == 1


def test_menu_navigation():
    app = make_app()
    press(app, A.MENU, A.DOWN, A.DOWN)
    assert app.mode.name == "menu" and app.mode.cursor == 2
    press(app, A.OK)
    assert app.mode.open_page == 2
    press(app, A.BACK)
    assert app.mode.open_page is None
    press(app, A.SHUTTER_HALF)
    assert app.mode.name == "shoot"


def test_playback_browses_and_returns():
    app = make_app()
    press(app, A.SHUTTER_FULL, A.SHUTTER_FULL, A.PLAY)      # same second: must not overwrite
    assert app.mode.name == "playback" and len(app.mode.files) == 2
    assert app.mode.index == 1
    press(app, A.LEFT)
    assert app.mode.index == 0
    press(app, A.PLAY)
    assert app.mode.name == "shoot"


def test_dial_sets_exposure_compensation():
    app = make_app()
    press(app, A.DIAL_UP, A.DIAL_UP, A.DIAL_UP)
    assert abs(app.ev - 1.0) < 1e-9 and abs(app.cam.ev - 1.0) < 1e-9
    press(app, A.BACK)
    assert app.ev == 0


def test_quit():
    app = make_app()
    app.handle(A.QUIT)
    assert not app.running


def test_terminal_key_split():
    assert list(split_keys("\x1b[Aq \x1b[D")) == ["\x1b[A", "q", " ", "\x1b[D"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
