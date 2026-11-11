"""Camera class against a mock Picamera2 that, like the real one, resets controls on every mode switch.

Guards the bug where settings (e.g. black and white) were lost when a photo was taken.
    python3 tests/test_camera_mock.py
"""
import os
import sys
import tempfile
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class _Enum:
    def __getattr__(self, name):
        return f"enum:{name}"


def install_mocks():
    lc = types.ModuleType("libcamera")
    lc.Transform = lambda **kw: ("Transform", tuple(sorted(kw.items())))
    lc.controls = types.SimpleNamespace(ExposureTimeModeEnum=_Enum(), AnalogueGainModeEnum=_Enum(),
                                        AeMeteringModeEnum=_Enum(), AwbModeEnum=_Enum())
    sys.modules["libcamera"] = lc

    pc = types.ModuleType("picamera2")

    class Picamera2:
        camera_controls = {k: (0, 1, 0) for k in (
            "ExposureTimeMode", "AnalogueGainMode", "ExposureTime", "AnalogueGain", "ExposureValue",
            "AeMeteringMode", "AwbEnable", "AwbMode", "Contrast", "Saturation", "Sharpness",
            "FrameDurationLimits", "ScalerCrop")}

        def __init__(self):
            self.controls, self.options, self.shots = {}, {}, []

        def _cfg(self, **kw):
            return {"controls": dict(kw.get("controls") or {}), **{k: v for k, v in kw.items() if k != "controls"}}

        create_preview_configuration = _cfg
        create_still_configuration = _cfg

        def configure(self, cfg):
            self.controls = dict(cfg["controls"])      # the real behaviour: controls reset here
            self.config = cfg

        switch_mode = configure

        def set_controls(self, c):
            self.controls.update(c)

        def start_preview(self, *a, **k):
            pass

        def start(self):
            pass

        def capture_metadata(self):
            return {"ScalerCrop": (0, 0, 4056, 3040)}

        def camera_configuration(self):
            return {"sensor": {"output_size": (2028, 1520), "bit_depth": 12}}

        def capture_file(self, path):
            self.shots.append(dict(self.controls))
            open(path, "wb").close()

    pc.Picamera2 = Picamera2
    pc.Preview = types.SimpleNamespace(DRM="DRM")
    sys.modules["picamera2"] = pc


install_mocks()

from evfcam import config                 # noqa: E402
from evfcam.camcore import Camera         # noqa: E402
from evfcam.settings import Settings      # noqa: E402


def test_settings_survive_capture_and_return_to_preview():
    cam = Camera(config.bench())
    st = Settings()
    cam.apply(st)
    cam.update_still(st)
    st.mono = True                         # changed after the still setup was built
    cam.apply(st)
    path = os.path.join(tempfile.mkdtemp(), "x.jpg")
    cam.capture(path)
    assert cam.p.shots[0]["Saturation"] == 0.0, "photo taken without black and white"
    assert cam.p.controls["Saturation"] == 0.0, "preview lost black and white after the shot"
    assert cam.p.config is cam.preview_cfg


def test_aspect_crop_and_settings_together():
    cam = Camera(config.bench())
    st = Settings(aspect="1:1", contrast=2)
    cam.apply(st)
    cam.update_still(st)
    cam.capture(os.path.join(tempfile.mkdtemp(), "x.jpg"))
    shot = cam.p.shots[0]
    assert shot["ScalerCrop"] == (508, 0, 3040, 3040) and shot["Contrast"] == 1.5
    assert "ScalerCrop" not in cam.preview_cfg["controls"]   # preview keeps the full frame


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
