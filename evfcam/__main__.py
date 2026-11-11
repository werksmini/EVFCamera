"""Start the camera app:  python3 -m evfcam  [--evf] [--fake] [--review SECONDS] [--no-flash]"""
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
    ap.add_argument("--review", type=float, default=0.0, metavar="SECONDS",
                    help="show each shot for this long after saving (default 0 = off)")
    ap.add_argument("--no-flash", action="store_true", help="no border flash at the shutter press")
    args = ap.parse_args()

    cfg = config.evf() if args.evf else config.bench()
    if args.photos:
        cfg.photos_dir = args.photos
    cfg.review_s = args.review
    cfg.capture_flash = not args.no_flash

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
    try:
        App(cfg, cam, q).run()
    except KeyboardInterrupt:
        pass
    finally:
        inputs.close()
        cam.close()
        print("bye")


if __name__ == "__main__":
    main()
