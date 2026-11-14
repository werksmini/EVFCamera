"""Contact sheet: ray-march each grip's distance field from three views (oblique, face-on, side profile).

  python3 sheet.py front out/front_sheet.png --seeds 0-11
"""
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb

import gripgen as g

BG = np.array(to_rgb("#1d1d1f"))
L1 = np.array([-0.5, 0.6, 0.65]); L1 /= np.linalg.norm(L1)


def look(eye_dir, up):
    f = -np.asarray(eye_dir, float); f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    return f, r, np.cross(r, f)


def render(prm, eye_dir, up=(0, 1, 0), px=200, texture=False):
    W, H, P = prm["W"], prm["H"], prm["P"]
    c = np.array([0, 0, P / 2])
    half = max(W, H, P) / 2 + 3
    f, r, u = look(eye_dir, np.asarray(up, float))
    s = np.linspace(-half, half, px)
    X, Y = np.meshgrid(s, -s)
    O = c - f * 60 + X[..., None] * r + Y[..., None] * u            # orthographic rays
    O = O.reshape(-1, 3)
    t = np.zeros(len(O)); hit = np.zeros(len(O), bool); alive = np.ones(len(O), bool)
    sdf = lambda Q: g.shape_sdf(Q, prm, texture=texture)
    for _ in range(160):
        idx = np.where(alive)[0]
        if not len(idx):
            break
        d = sdf(O[idx] + t[idx, None] * f)
        t[idx] += np.maximum(d * 0.7, 0.02)
        h = d < 0.02
        hit[idx[h]] = True; alive[idx[h]] = False
        alive[idx[t[idx] > 120]] = False
    img = np.tile(BG, (len(O), 1))
    if hit.any():
        Pp = O[hit] + t[hit, None] * f
        e = 0.05
        n = np.stack([sdf(Pp + e * np.eye(3)[k]) - sdf(Pp - e * np.eye(3)[k]) for k in range(3)], -1)
        n /= np.linalg.norm(n, axis=1)[:, None] + 1e-9
        diff = np.clip(n @ L1, 0, 1)
        rim = np.clip(1 + n @ f, 0, 1) ** 3
        base = np.array(to_rgb(prm["colour"]))
        img[hit] = np.clip(base * (0.28 + 0.72 * diff[:, None]) + 0.25 * rim[:, None], 0, 1)
    return img.reshape(px, px, 3)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=g.BOUNDS)
    ap.add_argument("out")
    ap.add_argument("--seeds", default="0-11")
    ap.add_argument("--good", type=int, help="instead of --seeds: the first N seeds that pass all checks")
    a = ap.parse_args()
    seeds = g.good_seeds(a.kind, a.good) if a.good else g.parse_seeds(a.seeds)
    views = [((0.55, -0.45, 0.7), (0, 0, 1)), ((0, 0, 1), (0, 1, 0)), ((0, -1, 0.0001), (0, 0, 1))]
    names = ["oblique", "face (looking at it)", "side (from below; lens side left)"]
    cols = 2
    rows = int(np.ceil(len(seeds) / cols))
    fig, axs = plt.subplots(rows, cols * 3, figsize=(cols * 3 * 2.1, rows * 2.4), facecolor=BG)
    axs = np.atleast_2d(axs)
    for ax in axs.flat:
        ax.axis("off")
    for i, s in enumerate(seeds):
        prm = g.make_params(a.kind, s)
        probs = g.check(prm)
        for k, (eye, up) in enumerate(views):
            ax = axs[i // cols, (i % cols) * 3 + k]
            ax.imshow(render(prm, eye, up), interpolation="lanczos")
            if k == 0:
                ok = not probs
                ax.set_title(f"s{s:02d}  {prm['W']:.0f}×{prm['H']:.0f}×{prm['P']:.0f} mm" + ("" if ok else "  ✗"),
                             color="w" if ok else "#ff6b6b", fontsize=9, loc="left")
            if i < cols:
                ax.text(0.5, -0.04, names[k], color="#888", fontsize=7, ha="center", va="top", transform=ax.transAxes)
    fig.suptitle(f"{a.kind} grips", color="w", fontsize=12)
    fig.tight_layout()
    fig.savefig(a.out, dpi=110, facecolor=BG)
    print("wrote", a.out)
