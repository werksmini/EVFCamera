"""Bouldering-hold grips for the EVF camera: seeded generator -> watertight STL.

Each grip is a signed distance field (SDF): negative inside, positive outside.
Shapes are smooth unions of ellipsoid "lobes", carved with smooth subtractions
(finger scallops, thumb dish), clipped to a bounding box and cut flat at the
mating face (z = 0). Fastener holes are subtracted last, so they are always exact.
Marching cubes turns the field into a mesh.

Grip coordinates (mm), seen from outside, looking at the face the grip bolts to:
  x  across the camera; -x is the side nearest the lens (front) or EVF (rear)
  y  up
  z  out of the camera body; z = 0 is the flat mating face

  python3 gripgen.py front --seeds 0-11          # contact sheet + STLs + params
  python3 gripgen.py rear --seeds 3 --texture    # one textured grip
"""
import argparse
import json
import pathlib
from dataclasses import dataclass, asdict, field

import numpy as np
import trimesh
from skimage.measure import marching_cubes

# --- fasteners (ISO 4762 M2.5 SHCS; MJF holes slightly oversize) -------------------------------------
M25_CLEAR = 3.0          # clearance hole dia (2.9 nominal + MJF allowance)
M25_CB = 5.2             # counterbore dia (head 4.5)
M25_HEAD = 2.5           # head height
PIN_HOLE = 2.15          # slip fit on a 2 mm dowel pressed into the body
PIN_DEPTH = 4.0
WALL = 2.5               # minimum material around a counterbore
RECESS = 0.3             # head sits this far below the surface, at least


@dataclass
class Bounds:
    w: tuple             # footprint width range (x)
    h: tuple             # footprint height range (y)
    p: tuple             # protrusion range (z)
    seat: float          # material under the screw head
    screws: list         # screw positions as fractions of (w/2, h/2)
    pins: list = field(default_factory=list)


BOUNDS = {
    # front crimp/edge for the fingers: one screw + a dowel pin against rotation
    "front": Bounds(w=(20, 28), h=(45, 55), p=(9, 14), seat=3.0, screws=[(0.15, -0.05)], pins=[(0.15, 0.55)]),
    # rear thumb sloper with a dish: two screws, top and bottom, clear of the thumb pad
    "rear": Bounds(w=(18, 24), h=(30, 34), p=(6.5, 9), seat=2.5, screws=[(0.1, 0.55), (0.1, -0.55)]),
}

COLOURS = ["#ffd400", "#ff6a00", "#00b8a9", "#ff2e88", "#7cdf00", "#2f7bff", "#9d4dff", "#ff3b30"]


# --- SDF primitives ------------------------------------------------------------------------------------
def ellipsoid(P, c, r, rot=0.0):
    """Approximate ellipsoid distance (good near the surface). rot: tilt about z, radians."""
    q = P - np.asarray(c, float)
    if rot:
        cs, sn = np.cos(rot), np.sin(rot)
        q = np.stack([cs * q[..., 0] + sn * q[..., 1], -sn * q[..., 0] + cs * q[..., 1], q[..., 2]], -1)
    r = np.asarray(r, float)
    k0 = np.linalg.norm(q / r, axis=-1)
    k1 = np.linalg.norm(q / (r * r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def capsule_x(P, y, z, r, x0=-50, x1=50):
    """Horizontal capsule (along x) used for finger scallops."""
    qx = np.clip(P[..., 0], x0, x1)
    return np.sqrt((P[..., 0] - qx) ** 2 + (P[..., 1] - y) ** 2 + (P[..., 2] - z) ** 2) - r


def cylinder_z(P, x, y, r, z0, z1):
    d_r = np.hypot(P[..., 0] - x, P[..., 1] - y) - r
    d_z = np.maximum(z0 - P[..., 2], P[..., 2] - z1)
    return np.maximum(d_r, d_z)


def box(P, half):
    q = np.abs(P) - np.asarray(half, float)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


# --- shape recipes -------------------------------------------------------------------------------------
def make_params(kind, seed):
    rng = np.random.default_rng(seed)
    B = BOUNDS[kind]
    u = lambda lo, hi: float(rng.uniform(lo, hi))
    W, H, Pz = u(*B.w), u(*B.h), u(*B.p)
    prm = dict(kind=kind, seed=seed, W=W, H=H, P=Pz, colour=COLOURS[seed % len(COLOURS)])
    n = int(rng.integers(3, 6)) if kind == "front" else int(rng.integers(3, 5))
    # lobes spread along the height. Each is sized to fit inside the bounds (the box clip is only a safety
    # net) and centred below the mating face, so its edge meets the camera at a shallow angle like a real hold.
    ys = (np.linspace(-0.62, 0.62, n) + rng.uniform(-0.08, 0.08, n)) * H / 2
    lobes = []
    for y in ys:
        cx = u(-0.08, 0.14) * W
        sink = u(0.15, 0.4)                      # centre depth below z=0 as a fraction of rz
        peak = u(0.72, 1.0) * Pz
        rz = peak / (1 - sink)
        rx = (W / 2 - abs(cx)) * u(0.82, 0.98) / np.sqrt(1 - sink ** 2)
        ry = min(u(1.0, 1.35) * H / n + 4, (H / 2 - abs(y)) * u(0.9, 1.05)) / np.sqrt(1 - sink ** 2)
        lobes.append(dict(c=[cx, float(y), -sink * rz], r=[rx, max(ry, 6.0), rz], rot=u(-0.3, 0.3)))
    prm["lobes"] = lobes
    # dents: shallow smooth scoops that break up the surface, like the facets on a cast hold
    prm["dents"] = [dict(c=[u(-0.35, 0.35) * W, u(-0.4, 0.4) * H], r=u(3.5, 7), depth=u(0.4, 1.2))
                    for _ in range(int(rng.integers(1, 5)))]
    if kind == "front":
        # the crimp: a fat rail on the lens side, set high and blended in, overhanging the lens-side base
        rx = u(4.0, 6.0)
        prm["lip"] = dict(c=[-(W / 2 - rx - u(0.3, 1.5)), u(-0.08, 0.08) * H, u(0.5, 0.62) * Pz],
                          r=[rx, u(0.28, 0.36) * H, u(0.3, 0.42) * Pz], rot=u(-0.15, 0.15))
        nf = int(rng.integers(0, 4))
        prm["scallops"] = [dict(y=float(y), r=u(7, 10), depth=u(0.8, 2.0))
                           for y in (np.arange(nf) - (nf - 1) / 2) * u(15, 19)]
        prm["dish"] = None
    else:
        # thumb dish between the screws, and a raised rim on the EVF side to cradle the thumb
        rx = u(3.5, 5.0)
        prm["lip"] = dict(c=[-(W / 2 - rx - u(0.3, 1.5)), u(-0.06, 0.06) * H, u(0.5, 0.65) * Pz],
                          r=[rx, u(0.25, 0.33) * H, u(0.35, 0.45) * Pz], rot=u(-0.3, 0.3)) if rng.random() < 0.7 else None
        prm["scallops"] = []
        prm["dish"] = dict(c=[u(-0.05, 0.15) * W, u(-0.08, 0.08) * H], r=[u(9, 13), u(10, 14)], depth=u(1.5, 2.5))
    prm["texture"] = dict(seed=seed, amp=0.07, wl=(0.6, 1.6))
    return prm


def holes(prm):
    B = BOUNDS[prm["kind"]]
    W, H = prm["W"], prm["H"]
    s = [(fx * W / 2, fy * H / 2) for fx, fy in B.screws]
    p = [(fx * W / 2, fy * H / 2) for fx, fy in B.pins]
    return s, p


def shape_sdf(P, prm, texture=False, with_holes=True):
    B = BOUNDS[prm["kind"]]
    W, H, Pz = prm["W"], prm["H"], prm["P"]
    d = None
    for L in prm["lobes"]:
        e = ellipsoid(P, L["c"], L["r"], L["rot"])
        d = e if d is None else smin(d, e, 4.0)
    if prm["lip"]:
        L = prm["lip"]
        d = smin(d, ellipsoid(P, L["c"], L["r"], L["rot"]), 3.0)
    screws, pins = holes(prm)
    for D in prm.get("dents", []):
        d = smax(d, -ellipsoid(P, [D["c"][0], D["c"][1], Pz * 0.9 + D["r"] - D["depth"]], [D["r"]] * 3), 1.0)
    for S in prm["scallops"]:
        top = Pz + S["r"] - S["depth"]
        d = smax(d, -capsule_x(P, S["y"], top, S["r"]), 1.5)
    if prm["dish"]:
        D = prm["dish"]
        rz = (D["r"][0] + D["r"][1]) / 2
        d = smax(d, -ellipsoid(P, [D["c"][0], D["c"][1], Pz + rz - D["depth"]], [D["r"][0], D["r"][1], rz]), 1.5)
    # a boss under each fastener (added after carving) guarantees the seat and the wall around the counterbore
    for x, y in screws:
        rb = M25_CB / 2 + WALL + 0.8
        d = smin(d, ellipsoid(P, [x, y, 0], [rb, rb, B.seat + M25_HEAD + RECESS + 1.2]), 2.0)
    # stay inside the bounding box (soft) and cut the mating face flat (hard)
    d = smax(d, box(P - [0, 0, (Pz - 5) / 2], [W / 2, H / 2, (Pz + 5) / 2]), 3.0)   # box runs below z=0: only the hard cut makes the face
    if texture:
        d = d + sandy(P, prm["texture"]) * np.clip(P[..., 2] - 0.8, 0, 1)
    d = np.maximum(d, -P[..., 2])
    if with_holes:
        for x, y in screws:
            d = np.maximum(d, -cylinder_z(P, x, y, M25_CLEAR / 2, -1, 99))
            d = np.maximum(d, -cylinder_z(P, x, y, M25_CB / 2, B.seat, 99))
        for x, y in pins:
            d = np.maximum(d, -cylinder_z(P, x, y, PIN_HOLE / 2, -1, PIN_DEPTH))
    return d


def sandy(P, T):
    """Fine climbing-hold grain: a sum of random plane waves (cheap, smooth, isotropic)."""
    rng = np.random.default_rng(1000 + T["seed"])
    n = 28
    dirs = rng.normal(size=(n, 3))
    dirs /= np.linalg.norm(dirs, axis=1)[:, None]
    k = 2 * np.pi / rng.uniform(*T["wl"], n)
    ph = rng.uniform(0, 2 * np.pi, n)
    out = np.zeros(P.shape[:-1])
    for i in range(n):
        out += np.sin((P @ dirs[i]) * k[i] + ph[i])
    return out * T["amp"] / np.sqrt(n / 2)


# --- checks --------------------------------------------------------------------------------------------
def check(prm):
    """Return a list of problems (empty = OK): wall around counterbores, head below the surface."""
    B = BOUNDS[prm["kind"]]
    screws, pins = holes(prm)
    probs = []
    ang = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for i, (x, y) in enumerate(screws):
        r = M25_CB / 2 + WALL
        for z in np.linspace(0.3, B.seat + 0.5, 4):
            ring = np.stack([x + r * np.cos(ang), y + r * np.sin(ang), np.full_like(ang, z)], -1)
            if (shape_sdf(ring, prm, with_holes=False) > 0).any():
                probs.append(f"screw {i + 1}: wall < {WALL} mm at z={z:.1f}")
                break
        # surface height on the screw axis: the head must sit at least RECESS below it everywhere on its rim
        zz = np.linspace(0, 30, 601)
        for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
            cx, cy = x + M25_CB / 2 * np.cos(a), y + M25_CB / 2 * np.sin(a)
            col = np.stack([np.full_like(zz, cx), np.full_like(zz, cy), zz], -1)
            inside = shape_sdf(col, prm, with_holes=False) < 0
            top = zz[inside].max() if inside.any() else 0
            if top < B.seat + M25_HEAD + RECESS:
                probs.append(f"screw {i + 1}: head proud (surface {top:.1f} mm < {B.seat + M25_HEAD + RECESS:.1f})")
                break
    for i, (x, y) in enumerate(pins):
        col = np.array([[x, y, PIN_DEPTH + 1.5]])
        if shape_sdf(col, prm, with_holes=False)[0] > 0:
            probs.append(f"pin {i + 1}: less than 1.5 mm over the pin hole")
    return probs


# --- meshing -------------------------------------------------------------------------------------------
def mesh(prm, voxel=0.3, texture=False):
    W, H, Pz = prm["W"], prm["H"], prm["P"]
    lo = np.array([-W / 2 - 2, -H / 2 - 2, -voxel * 1.5])   # z grid straddles 0 -> exact flat face
    hi = np.array([W / 2 + 2, H / 2 + 2, Pz + 2])
    axes = [np.arange(lo[i], hi[i] + voxel, voxel) for i in range(3)]
    G = np.stack(np.meshgrid(*axes, indexing="ij"), -1)
    vol = shape_sdf(G, prm, texture=texture)
    v, f, _, _ = marching_cubes(vol, 0.0, spacing=(voxel,) * 3)
    m = trimesh.Trimesh(v + lo, f[:, ::-1], process=True)
    m = max(m.split(only_watertight=False), key=lambda p: len(p.faces))   # drop stray 1-2 triangle slivers
    m.fix_normals()
    return m


def good_seeds(kind, n, start=0):
    """The first n seeds from `start` whose grips pass every check."""
    out, s = [], start
    while len(out) < n:
        if not check(make_params(kind, s)):
            out.append(s)
        s += 1
    return out


def parse_seeds(s):
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=BOUNDS)
    ap.add_argument("--seeds", default="0-11")
    ap.add_argument("--good", type=int, help="instead of --seeds: the first N seeds that pass all checks")
    ap.add_argument("--voxel", type=float, default=0.3)
    ap.add_argument("--texture", action="store_true", help="add fine grain (use --voxel 0.15)")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(exist_ok=True)
    for s in (good_seeds(a.kind, a.good) if a.good else parse_seeds(a.seeds)):
        prm = make_params(a.kind, s)
        probs = check(prm)
        m = mesh(prm, a.voxel, a.texture)
        tag = f"{a.kind}_s{s:02d}" + ("_tex" if a.texture else "")
        m.export(out / f"{tag}.stl")
        prm["checks"] = probs or ["ok"]
        prm["volume_cm3"] = round(m.volume / 1000, 2)
        prm["watertight"] = bool(m.is_watertight)
        json.dump(prm, open(out / f"{tag}.json", "w"), indent=1)
        print(f"{tag}: {m.bounds[1] - m.bounds[0]} mm, {len(m.faces)} faces, "
              f"watertight={m.is_watertight}, {'; '.join(probs) or 'checks ok'}")
