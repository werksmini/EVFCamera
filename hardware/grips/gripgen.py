"""Bouldering-hold grips for the EVF camera: seeded generator -> watertight STL.

v2: smooth, continuous holds like real cast holds. Each grip is ONE swept form:
  - a gently curved spine running up the grip (bow + slight S),
  - a cross-section profile swept along it (crimp, pinch or sloper),
  - a superellipse envelope that tapers width and height to rounded ends.
Nothing random is added on the surface, so curvature stays continuous.

Signed distance field (SDF): negative inside, positive outside. Fastener bosses are blended in,
the mating face is cut flat at z = 0, holes are cut last and exactly. Marching cubes -> STL (mm).

Standard hole patterns on the camera body (three tapped holes in a vertical line):
  front: M2.5 at y = -10, 0, +10 mm (10 mm pitch)
  rear:  M2   at y = -5, 0, +5 mm  (5 mm pitch)
  2-bolt grips: SHCS in the outer two holes.
  1-bolt grips: SHCS in the centre hole, located against rotation by a set screw standing
                proud in the upper hole (M2.5 x 4 / M2 x 3); the grip has a blind pocket over it.

Grip coordinates (mm), looking at the face the grip bolts to:
  x across the camera, -x = lens side (front) / EVF side (rear); y up; z out of the body.

  python3 gripgen.py front-crimp --bolts 2 --seeds 0-3
  python3 gripgen.py rear-sloper --bolts 1 --good 4
"""
import argparse
import json
import pathlib
from dataclasses import dataclass

import numpy as np
import trimesh
from skimage.measure import marching_cubes

# --- fasteners (ISO 4762 SHCS). MJF holes print ~0.1 mm small, so these are close-fit + a little ----------
@dataclass
class Screw:
    name: str
    clear: float      # clearance hole dia
    cb: float         # counterbore dia
    head: float       # head height
    pitch: float      # standard hole pitch on the body
    loc_hole: float   # blind pocket over the locating set screw
    loc_depth: float  # set screw stands (loc_depth - 0.3) mm proud of the body
    wall: float       # minimum material around the counterbore


# front: M2.5 (head 4.5 x 2.5); body holes at y = -10, 0, +10
M25 = Screw("M2.5", clear=2.8, cb=4.9, head=2.5, pitch=10.0, loc_hole=2.9, loc_depth=2.8, wall=1.5)
# rear: M2 (head 3.8 x 2.0); body holes at y = -5, 0, +5
M2 = Screw("M2", clear=2.4, cb=4.1, head=2.0, pitch=5.0, loc_hole=2.4, loc_depth=2.3, wall=1.2)
RECESS = 0.3             # head sits at least this far below the surface


def pattern(bolts, sc):
    """(screws, locators) as (x, y) in grip coordinates."""
    if bolts == 2:
        return [(0.0, -sc.pitch), (0.0, sc.pitch)], []
    return [(0.0, 0.0)], [(0.0, sc.pitch)]


@dataclass
class Style:
    w: tuple        # footprint width range (x), mm
    h: tuple        # footprint height range (y), mm
    p: tuple        # protrusion parameter range (z), mm; crimps finish ~80 % of this
    seat: float     # material under the screw head
    profile: str    # crimp | pinch | sloper
    screw: Screw


STYLES = {
    # fingers curl over a rounded positive edge on the lens side; the face slopes back toward the body end
    "front-crimp": Style(w=(13.5, 18), h=(44, 54), p=(6.3, 8), seat=1.8, profile="crimp", screw=M25),
    # a narrow fin with two pinchable flanks
    "front-pinch": Style(w=(10.5, 13.5), h=(44, 54), p=(6, 7.5), seat=1.8, profile="pinch", screw=M25),
    # thumb edge: a small crimp the thumb pad hooks over
    "rear-crimp": Style(w=(10, 13), h=(18, 22), p=(5.0, 6.0), seat=1.2, profile="crimp", screw=M2),
    # thumb sloper: a low dome with a shallow dish for the thumb pad
    "rear-sloper": Style(w=(11, 14), h=(18, 22), p=(4.4, 5.3), seat=1.2, profile="sloper", screw=M2),
}

COLOURS = ["#ffd400", "#ff6a00", "#00b8a9", "#ff2e88", "#7cdf00", "#2f7bff", "#9d4dff", "#ff3b30"]


# --- SDF helpers ---------------------------------------------------------------------------------------
def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def superellipse(a, b, ra, rb, n):
    return (np.abs(a / ra) ** n + np.abs(b / rb) ** n) ** (1 / n) - 1


def ellipsoid(P, c, r):
    q = (P - np.asarray(c, float)) / np.asarray(r, float)
    k0 = np.linalg.norm(q, axis=-1)
    k1 = np.linalg.norm(q / np.asarray(r, float), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def cylinder_z(P, x, y, r, z0, z1):
    d_r = np.hypot(P[..., 0] - x, P[..., 1] - y) - r
    return np.maximum(d_r, np.maximum(z0 - P[..., 2], P[..., 2] - z1))


# --- recipe ----------------------------------------------------------------------------------------------
def make_params(style, bolts, seed):
    rng = np.random.default_rng(seed * 7919 + bolts * 31 + sum(map(ord, style)))
    S = STYLES[style]
    u = lambda lo, hi: float(rng.uniform(lo, hi))
    prm = dict(style=style, bolts=bolts, seed=seed, profile=S.profile, colour=COLOURS[seed % len(COLOURS)],
               W=u(*S.w), L=u(*S.h), P=u(*S.p),
               bow=u(-0.04, 0.04), sbend=u(-0.025, 0.025),       # spine curvature, fraction of length
               yoff=u(-0.04, 0.04),                            # spine centre offset along y, fraction
               env_n=u(2.2, 3.2),                              # end shape: 2 = elliptical, higher = squarer
               wtaper=u(-0.25, 0.25), htaper=u(-0.2, 0.2),    # one end wider / taller (bean shape)
               n=u(2.2, 2.8), cb=u(0.3, 0.5))                  # section squareness, how deep the dome sinks
    if S.profile == "crimp":
        # edge side (-x) squarer than the back, top leans over the edge, face slopes down to the back
        prm.update(tilt=u(0.15, 0.3), n_edge=u(3.4, 4.6), lean=u(0.12, 0.24), lip=None,
                   hole_a=u(-0.3, -0.18))                     # hole line sits this far toward the edge
    elif S.profile == "pinch":
        prm.update(tilt=u(-0.08, 0.08), lip=None, waist=u(0.0, 0.12))
    else:
        prm.update(tilt=u(0.05, 0.18), lip=None,
                   dish=dict(x=u(0.0, 0.12), y=u(-0.06, 0.06), r=u(0.5, 0.65) * prm["W"], depth=u(0.08, 0.14) * prm["P"]))
    return prm


def shape_sdf(P, prm, with_holes=True):
    S = STYLES[prm["style"]]
    W, L, Pz = prm["W"], prm["L"], prm["P"]
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    yc = y - prm["yoff"] * L
    uu = 2 * yc / L                                              # -1 .. 1 along the spine
    spine = lambda q: L * (prm["bow"] * (1 - q ** 2) + prm["sbend"] * np.sin(np.pi * q / 2))
    sc = S.screw
    hy = np.array([p[1] for p in sum(pattern(prm["bolts"], sc), [])])
    x_fix = spine(2 * (hy - prm["yoff"] * L) / L).mean()       # keep the spine centred on the hole line
    if prm["profile"] == "crimp":
        x_fix += prm["hole_a"] * W / 2                             # ...or, for crimps, the thick ridge on it
    sx = spine(uu) - x_fix
    slope = (prm["bow"] * (-2 * uu) + prm["sbend"] * np.pi / 2 * np.cos(np.pi * uu / 2)) * 2
    s = (x - sx) / np.sqrt(1 + slope ** 2)
    env = np.clip(1 - np.abs(uu) ** prm["env_n"], 1e-4, 1) ** (1 / prm["env_n"])
    w = W / 2 * env * (1 + prm["wtaper"] * uu)
    h = Pz * env ** 0.45 * (1 + prm["htaper"] * uu) / (1 + abs(prm["htaper"]))
    a, b = s / w, z / h
    # cross-section in normalised (a, b): dome sinks cb below the face, top at b = 1
    cb, n = prm["cb"], prm["n"]
    if prm["profile"] == "crimp":
        a = a + prm["lean"] * np.clip(b, 0, 1.5) ** 2             # top overhangs the edge side: positive hold
        n = n + (prm["n_edge"] - n) / (1 + np.exp(np.clip(a / 0.2, -50, 50)))       # squarer toward the edge, smooth blend
        b = b * (1 + prm["tilt"])                                  # keep the peak at the protrusion P
    b2 = b + prm["tilt"] * a
    if prm["profile"] == "pinch":
        a = a * (1 + prm["waist"] * np.exp(-((b - 0.45) / 0.3) ** 2))   # slight waist on the flanks
    sec = superellipse(a, b2 + cb, 1.0, 1.0 + cb, n)
    d = sec * np.minimum(w, h) * 0.8                              # back to roughly mm
    d = np.maximum(d, np.abs(yc) - L / 2)
    if prm.get("dish"):
        D = prm["dish"]
        c = [D["x"] * W, D["y"] * L, Pz + D["r"] - D["depth"]]
        d = smax(d, -ellipsoid(P, c, [D["r"], D["r"] * 1.2, D["r"]]), 2.0)
    screws, locs = pattern(prm["bolts"], sc)
    # no bosses: the form itself must carry the fasteners (check() rejects seeds that are too thin),
    # which keeps the surface one continuous shape
    d = np.maximum(d, -z)                                         # flat mating face
    if with_holes:
        for (hx, hy) in screws:
            d = np.maximum(d, -cylinder_z(P, hx, hy, sc.clear / 2, -1, 99))
            d = np.maximum(d, -cylinder_z(P, hx, hy, sc.cb / 2, S.seat, 99))
        for (hx, hy) in locs:
            d = np.maximum(d, -cylinder_z(P, hx, hy, sc.loc_hole / 2, -1, sc.loc_depth))
    return d


# --- checks ------------------------------------------------------------------------------------------------
def check(prm):
    S = STYLES[prm["style"]]
    sc = S.screw
    screws, locs = pattern(prm["bolts"], sc)
    probs = []
    ang = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for i, (x, y) in enumerate(screws):
        r = sc.cb / 2 + sc.wall
        for zz in np.linspace(0.3, S.seat + 0.5, 4):
            ring = np.stack([x + r * np.cos(ang), y + r * np.sin(ang), np.full_like(ang, zz)], -1)
            if (shape_sdf(ring, prm, with_holes=False) > 0).any():
                probs.append(f"screw {i + 1}: wall < {sc.wall} mm")
                break
        col_z = np.linspace(0, 30, 601)
        for t in np.linspace(0, 2 * np.pi, 12, endpoint=False):
            col = np.stack([np.full_like(col_z, x + sc.cb / 2 * np.cos(t)),
                            np.full_like(col_z, y + sc.cb / 2 * np.sin(t)), col_z], -1)
            inside = shape_sdf(col, prm, with_holes=False) < 0
            top = col_z[inside].max() if inside.any() else 0
            if top < S.seat + sc.head + RECESS:
                probs.append(f"screw {i + 1}: head proud")
                break
    for (x, y) in locs:
        if shape_sdf(np.array([[x, y, sc.loc_depth + 1.2]]), prm, with_holes=False)[0] > 0:
            probs.append("locator: < 1.2 mm over the pocket")
    return probs


def good_seeds(style, bolts, n, start=0):
    out, s = [], start
    while len(out) < n and s < start + 200:
        if not check(make_params(style, bolts, s)):
            out.append(s)
        s += 1
    return out


# --- meshing ------------------------------------------------------------------------------------------------
def mesh(prm, voxel=0.25):
    W, L, Pz = prm["W"], prm["L"], prm["P"]
    lo = np.array([-W / 2 - 6, -L / 2 - 4, -voxel * 1.5])
    hi = np.array([W / 2 + 6, L / 2 + 4, Pz + 4])
    axes = [np.arange(lo[i], hi[i] + voxel, voxel) for i in range(3)]
    G = np.stack(np.meshgrid(*axes, indexing="ij"), -1)
    v, f, _, _ = marching_cubes(shape_sdf(G, prm), 0.0, spacing=(voxel,) * 3)
    m = trimesh.Trimesh(v + lo, f[:, ::-1], process=True)
    m = max(m.split(only_watertight=False), key=lambda p: len(p.faces))
    m.fix_normals()
    return m


def tag(prm):
    return f"{prm['style']}-{prm['bolts']}b_s{prm['seed']:02d}"


def parse_seeds(s):
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("style", choices=STYLES)
    ap.add_argument("--bolts", type=int, choices=(1, 2), default=2)
    ap.add_argument("--seeds", default="0-3")
    ap.add_argument("--good", type=int, help="instead of --seeds: the first N seeds that pass all checks")
    ap.add_argument("--voxel", type=float, default=0.25)
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(exist_ok=True)
    seeds = good_seeds(a.style, a.bolts, a.good) if a.good else parse_seeds(a.seeds)
    for s in seeds:
        prm = make_params(a.style, a.bolts, s)
        probs = check(prm)
        m = mesh(prm, a.voxel)
        m.export(out / f"{tag(prm)}.stl")
        ext = m.bounds[1] - m.bounds[0]
        prm.update(checks=probs or ["ok"], size_mm=[round(float(e), 1) for e in ext],
                   volume_cm3=round(m.volume / 1000, 2), watertight=bool(m.is_watertight))
        json.dump(prm, open(out / f"{tag(prm)}.json", "w"), indent=1)
        print(f"{tag(prm)}: {np.round(ext, 1)} mm, watertight={m.is_watertight}, {'; '.join(probs) or 'ok'}")
