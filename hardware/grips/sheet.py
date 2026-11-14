"""Contact sheet for the v2 grips: one row per style x bolt count, N passing seeds, three views each.

  python3 sheet.py front front_sheet.png      # front-crimp / front-pinch, 1 and 2 bolts
  python3 sheet.py rear rear_sheet.png --n 3
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb

import gripgen as g

BG = np.array(to_rgb("#1d1d1f"))
LIGHT = np.array([-0.5, 0.6, 0.65]) / np.linalg.norm([-0.5, 0.6, 0.65])
VIEWS = [((0.55, -0.45, 0.7), (0, 0, 1), "oblique"),
         ((0, 0, 1), (0, 1, 0), "face"),
         ((0, -1, 0.0001), (0, 0, 1), "side (lens/EVF side left)")]


def render(prm, eye, up, px=190):
    W, L, P = prm["W"], prm["L"], prm["P"]
    c = np.array([0, 0, P / 2])
    half = max(W, L, P) / 2 + 3
    f = -np.asarray(eye, float); f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    s = np.linspace(-half, half, px)
    X, Y = np.meshgrid(s, -s)
    O = (c - f * 60 + X[..., None] * r + Y[..., None] * u).reshape(-1, 3)
    t = np.zeros(len(O)); hit = np.zeros(len(O), bool); alive = np.ones(len(O), bool)
    sdf = lambda Q: g.shape_sdf(Q, prm)
    for _ in range(500):
        idx = np.where(alive)[0]
        if not len(idx):
            break
        d = sdf(O[idx] + t[idx, None] * f)
        t[idx] += np.maximum(d * 0.3, 0.01)
        hh = d < 0.015
        hit[idx[hh]] = True; alive[idx[hh]] = False
        alive[idx[t[idx] > 120]] = False
    img = np.tile(BG, (len(O), 1))
    if hit.any():
        Pp = O[hit] + t[hit, None] * f
        e = 0.05
        n = np.stack([sdf(Pp + e * np.eye(3)[k]) - sdf(Pp - e * np.eye(3)[k]) for k in range(3)], -1)
        n /= np.linalg.norm(n, axis=1)[:, None] + 1e-9
        diff = np.clip(n @ LIGHT, 0, 1)
        spec = np.clip(n @ (LIGHT - f) / np.linalg.norm(LIGHT - f), 0, 1) ** 40
        rim = np.clip(1 + n @ f, 0, 1) ** 3
        base = np.array(to_rgb(prm["colour"]))
        img[hit] = np.clip(base * (0.25 + 0.75 * diff[:, None]) + 0.25 * spec[:, None] + 0.2 * rim[:, None], 0, 1)
    return img.reshape(px, px, 3)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("side", choices=("front", "rear"))
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    rows = [(st, b) for st in g.STYLES if st.startswith(a.side) for b in (2, 1)]
    fig, axs = plt.subplots(len(rows), a.n * 3, figsize=(a.n * 3 * 1.9, len(rows) * 2.3), facecolor=BG)
    for ax in axs.flat:
        ax.axis("off")
    for ri, (st, b) in enumerate(rows):
        for ci, s in enumerate(g.good_seeds(st, b, a.n)):
            prm = g.make_params(st, b, s)
            for k, (eye, up, name) in enumerate(VIEWS):
                ax = axs[ri, ci * 3 + k]
                ax.imshow(render(prm, eye, up), interpolation="lanczos")
                if k == 0:
                    ax.set_title(f"{g.tag(prm)}  {prm['W']:.0f}×{prm['L']:.0f}×{prm['P']:.0f}",
                                 color="w", fontsize=8, loc="left")
                if ri == len(rows) - 1:
                    ax.text(0.5, -0.03, name, color="#888", fontsize=7, ha="center", va="top", transform=ax.transAxes)
    fig.suptitle(f"{a.side} grips v2 — rows: style, bolts (2 = M2.5 at ±10 mm; 1 = M2.5 at 0 + locator at +10)",
                 color="w", fontsize=10)
    fig.tight_layout()
    fig.savefig(a.out, dpi=110, facecolor=BG)
    print("wrote", a.out)
