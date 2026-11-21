"""Start the camera app:  python3 -m evfcam  [--evf] [--fake] [--photos DIR]"""
import argparse
import os
import queue
import signal
import threading

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
    inputs = Inputs(q, buttons=None if args.fake else cfg.buttons).start()
    print("EVFCamera running. Controls from:", ", ".join(inputs.sources) or "none")
    print(HELP)
    app = App(cfg, cam, q)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    try:
        app.run()
        print("quit: closing down")
    except KeyboardInterrupt:
        print("interrupted: closing down")
    finally:
        shutdown(app, inputs, cam)


def shutdown(app, inputs, cam, timeout=3.0):
    """Close everything, step by step; if any step hangs, say which and force the exit."""
    steps = [("settings", app.save_settings), ("buttons and keyboard", inputs.close), ("camera", cam.close)]

    def run_steps():
        for name, fn in steps:
            print(f"  closing {name}...", flush=True)
            try:
                fn()
            except Exception as e:
                print(f"  {name}: {e}")

    t = threading.Thread(target=run_steps, daemon=True)
    t.start()
    t.join(timeout * len(steps))
    if t.is_alive():
        print("  a step hung (last one shown above): forcing exit", flush=True)
        try:
            inputs.restore_terminal()
        except Exception:
            pass
        os._exit(1)
    print("bye")


if __name__ == "__main__":
    main()
