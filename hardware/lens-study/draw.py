"""Draw the optimised retrofocus: lens cross-section with ray bundles, plus spot sizes and prescription."""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import retro

data = json.load(open(sys.argv[1]))
p, k, fno = np.array(data["p"]), data["k"], data["fno"]
surf = retro.build(p, k)
m, info = retro.evaluate(p, fno)
half_ang = np.degrees(np.arctan(retro.HALF / retro.EFL_TARGET))

# --- meridional ray fans (d line) ------------------------------------------------------------------------
fig = plt.figure(figsize=(12, 6.2))
ax = fig.add_axes([0.04, 0.12, 0.62, 0.8])
z = 0.0
zs = []
for c, t, nn in surf:
    zs.append(z)
    z += t
z_last = zs[-1]
img_z = z_last + info["img"]

# element outlines: draw each glass between consecutive surfaces
def sag(c, y):
    if c == 0:
        return 0 * y
    return c * y ** 2 / (1 + np.sqrt(np.clip(1 - (c * y) ** 2, 0, None)))

# semi-diameters from traced rays
semi = np.zeros(len(surf))
cols = {0: "#1f77b4", 1: "#2ca02c", 2: "#d62728", 3: "#9467bd"}
# simpler: re-aim a vertical fan by brute force through the stop using retro internals
def fan(field_deg, n=9):
    pts = np.column_stack([np.zeros(n), np.linspace(-1, 1, n)])
    start, dirv = retro.trace(surf, field_deg, fno, info["img"], pts=pts, return_launch=True)
    path = [start.copy()]
    for upto in range(len(surf)):
        h, _, _ = retro.propagate(surf, start, dirv, 1, upto=upto)
        path.append(h.copy())
    end, _, _ = retro.propagate(surf, start, dirv, 1, img_dist=info["img"])
    path.append(end)
    return np.array(path)

for fi, f in enumerate((0.0, 0.5, 0.75, 1.0)):
    path = fan(f * half_ang)
    path[0] = path[1] - (path[2] - path[1]) / np.linalg.norm(path[2] - path[1], axis=1)[:, None] * 4
    for r in range(path.shape[1]):
        ax.plot(path[:, r, 2], path[:, r, 1], color=list(cols.values())[fi], lw=0.6, alpha=0.8)
    semi = np.maximum(semi, np.abs(path[1:len(surf) + 1, :, 1]).max(1))

glass_pairs = [(0, 1), (3, 4), (4, 5), (6, 7)]
def surf_h(i):
    h = semi[i] * 1.06 + 0.15
    c = surf[i][0]
    return min(h, 0.97 / abs(c)) if c else h
for i, j in glass_pairs:
    hi, hj = surf_h(i), surf_h(j)
    h = max(hi, hj)
    yi = np.linspace(-hi, hi, 80); yj = np.linspace(-hj, hj, 80)
    zi = zs[i] + sag(surf[i][0], yi); zj = zs[j] + sag(surf[j][0], yj)
    # outline: front surface, rear surface, and flat mounting faces joining their rims at height h
    zi_e, zj_e = zi[-1], zj[-1]
    poly_z = list(zi) + [zi_e, zj_e] + list(zj[::-1]) + [zj_e, zi_e]
    poly_y = list(yi) + [h, h] + list(yj[::-1]) + [-h, -h]
    # make the rim faces radial: front rim goes out to h at its own z, rear rim likewise
    poly_z = list(zi) + [zi_e, zj_e, zj_e] + list(zj[::-1]) + [zj_e, zj_e, zi_e, zi_e]
    poly_y = list(yi) + [h, h, hj] + list(yj[::-1]) + [-hj, -h, -h, -hi]
    ax.fill(poly_z, poly_y, color="#a8d0f0" if i != 4 else "#7fb2e0", alpha=0.6, lw=0)
    ax.plot(poly_z + [poly_z[0]], poly_y + [poly_y[0]], "k", lw=0.9)
# stop
hs = semi[2]
ax.plot([zs[2], zs[2]], [hs, hs * 2.2], "k", lw=2.5); ax.plot([zs[2], zs[2]], [-hs, -hs * 2.2], "k", lw=2.5)
ax.text(zs[2], hs * 2.4, "iris", ha="center", fontsize=9)
# filter and sensor
ax.add_patch(plt.Rectangle((z_last + 0.5, -4.4), 1.0, 8.8, color="#f4c2c2", alpha=0.7))
ax.text(z_last + 1.0, 4.7, "IR-cut", ha="center", fontsize=8)
ax.plot([img_z, img_z], [-retro.HALF, retro.HALF], color="k", lw=3)
ax.text(img_z, -4.9, "sensor", ha="center", fontsize=8)
ax.set_aspect("equal"); ax.set_xlabel("mm (light travels left to right)"); ax.set_yticks([])
ax.set_title(f"Retrofocus study: EFL 5.0 mm (28 mm equiv.), f/{fno:g}, 77° field", fontsize=11)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)

# --- text panel ---------------------------------------------------------------------------------------------
tx = fig.add_axes([0.68, 0.05, 0.31, 0.9]); tx.axis("off")
dist = (info["chief"][1:] / (retro.EFL_TARGET * np.tan(np.radians(retro.FIELDS[1:] * half_ang))) - 1) * 100
names = ["Front meniscus (N-SF5)", "", "Iris (stop)", "Doublet crown (N-LAK9)", "Doublet flint (N-SF6)", "",
         "Rear singlet (N-LAK9)", ""]
lines = ["Prescription (mm)", "surf  radius     thickness  diam."]
for i, (c, t, nn) in enumerate(surf):
    R = "flat" if c == 0 else f"{1 / c:8.2f}"
    tt = t if i < len(surf) - 1 else 0.5
    lines.append(f"{i + 1:>3}  {R:>8}  {tt:8.2f}   {2 * semi[i] * 1.08:5.1f}  {names[i]}")
lines += ["", f"IR-cut 1.0 mm, then {info['img'] - 1.5:.2f} mm to sensor",
          f"Back clearance (last glass to sensor): {info['img']:.2f} mm",
          f"Total length (front glass to sensor): {img_z:.1f} mm", "",
          "RMS blur radius (all colours)",
          "  field:   0%    50%    75%    100%",
          "  µm:   " + "  ".join(f"{v * 1000:5.1f}" for v in info["rms"]),
          f"  pixel = 1.55 µm",
          "", "Distortion at 50/75/100% field:",
          "  " + "  ".join(f"{d:+.1f}%" for d in dist)]
tx.text(0, 1, "\n".join(lines), va="top", family="monospace", fontsize=8.2)
out = sys.argv[2]
fig.savefig(out, dpi=150)
print("wrote", out)
