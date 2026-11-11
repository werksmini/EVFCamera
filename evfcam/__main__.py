"""Start the camera app:  python3 -m evfcam  [--evf] [--fake] [--photos DIR]"""
import argparse
import queue

from . import config
from .actions import HELP
from .app import App
from .inputs import Inputs


def main():
    ap = argparse.ArgumentParser(prog="evfcam")
    ap.add_argument("--evf", action="store_true", help="use the 1280x960 EVF layout (no flip)")
    ap.add_argument("--fake", action="store_true", help="no camera: develop the UI anywhere")
    ap.add_argument("--photos", help="folder for photos (default ~/evfpi/photos)")
    args = ap.parse_args()

    cfg = config.evf() if args.evf else config.bench()
    if args.photos:
        cfg.photos_dir = args.photos

    if args.fake:
        from .camcore import FakeCamera
        cam = FakeCamera(cfg)
    else:
        from .camcore import Camera
        cam = Camera(cfg)

    q = queue.Queue()
    inputs = Inputs(q, shutter_gpio=None if args.fake else cfg.shutter_gpio).start()
    print("EVFCamera running. Controls from:", ", ".join(inputs.sources) or "none")
    print(HELP)
    app = App(cfg, cam, q)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.save_settings()
        inputs.close()
        cam.close()
        print("bye")


if __name__ == "__main__":
    main()
