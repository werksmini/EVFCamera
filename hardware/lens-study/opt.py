import numpy as np, sys, json
from scipy.optimize import minimize
import retro

FNO = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
DMAX = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
DW = float(sys.argv[3]) if len(sys.argv) > 3 else 0.02
TAG = sys.argv[4] if len(sys.argv) > 4 else ''
HALF_ANG = np.degrees(np.arctan(retro.HALF / retro.EFL_TARGET))

def merit(p):
    p = np.asarray(p)
    if min(p[2], p[3], p[7]) < 0.1:          # gaps must stay open
        return 1e3
    m, info = retro.evaluate(p, FNO)
    if info is None:
        return 1e3
    k = retro.EFL_TARGET / retro.paraxial(retro.build(p))[0]
    gaps = np.array([p[2], p[3], p[7]]) * k
    pen = 0.0
    pen += 50 * max(0, 0.2 - gaps.min()) ** 2
    pen += 1e-2 * max(0, 5.0 - info["img"]) ** 2            # >= 5 mm behind last element (filter + mount)
    dist = (info["chief"][-1] - retro.EFL_TARGET * np.tan(np.radians(HALF_ANG))) / retro.HALF
    pen += DW * max(0, abs(dist) - DMAX) ** 2                # keep corner distortion within DMAX
    return m + pen

best = None
rng = np.random.default_rng(1)
starts = [[18.0, 5.0, 7.0, 1.0, 10.0, -4.5, -12.0, 0.4, 14.0, -14.0]]
for _ in range(3):
    starts.append(list(np.array(starts[0]) * rng.uniform(0.7, 1.3, 10)))
for s in starts:
    r = minimize(merit, s, method="Nelder-Mead", options=dict(maxiter=2500, xatol=1e-4, fatol=1e-11))
    r = minimize(merit, r.x, method="Powell", options=dict(maxiter=3, xtol=1e-4, ftol=1e-11))
    print(round(r.fun, 6), flush=True)
    if best is None or r.fun < best.fun:
        best = r
m, info = retro.evaluate(best.x, FNO)
k = retro.EFL_TARGET / retro.paraxial(retro.build(best.x))[0]
print("params", list(np.round(best.x, 4)), "scale", k)
print("rms um", np.round(info["rms"] * 1000, 1), "img", round(info["img"], 2))
dist = (info["chief"] / (retro.EFL_TARGET * np.tan(np.radians(retro.FIELDS * HALF_ANG))) - 1)[1:]
print("distortion %", np.round(dist * 100, 1))
json.dump(dict(fno=FNO, p=list(best.x), k=k), open(f"best_f{FNO}{TAG}.json", "w"))
