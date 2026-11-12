"""Retrofocus wide for the Pi HQ (IMX477): design study.

Sequential, spherical surfaces, real 3D ray trace (vectorised), 3 wavelengths.
Layout: negative meniscus | stop | cemented doublet | positive singlet | IR-cut plate | sensor.
Optimise shape for RMS spot over the field, then scale to EFL = 5.0 mm.
"""
import numpy as np
from scipy.optimize import minimize
from opticalglass import glassfactory as gf

WL = np.array([0.4861, 0.5876, 0.6563])        # F, d, C (um)
WW = np.array([0.5, 1.0, 0.5])
GLASS = {g: np.array([gf.create_glass(g, "Schott").rindex(w * 1000) for w in WL])
         for g in ("N-BK7", "N-SK16", "N-SF5", "N-LAK9", "N-SF6")}
AIR = np.ones(3)

HALF = 3.95          # sensor half-diagonal, mm
EFL_TARGET = 5.0


def build(p, k=1.0):
    """p: free parameters -> list of surfaces (curvature c, thickness after, index after), all lengths x k."""
    R1, R2, g1, g2, R3, R4, R5, g3, R6, R7 = np.array(p) * k
    t_front, t_cr, t_fl, t_s = 1.5 * k, 2.2 * k, 0.8 * k, 1.8 * k
    surf = [
        (1 / R1, t_front, GLASS["N-SF5"]),      # front negative meniscus (high index helps)
        (1 / R2, g1, AIR),
        (0.0, g2, AIR),                         # stop
        (1 / R3, t_cr, GLASS["N-LAK9"]),        # cemented doublet: crown
        (1 / R4, t_fl, GLASS["N-SF6"]),         #                   flint
        (1 / R5, g3, AIR),
        (1 / R6, t_s, GLASS["N-LAK9"]),         # rear positive singlet
        (1 / R7, 0.0, AIR),                     # gap to filter set later
    ]
    return surf


def paraxial(surf):
    """y-nu trace of a marginal ray from infinity: returns efl, bfl (from last surface)."""
    y, nu, n = 1.0, 0.0, 1.0
    for c, t, nn in surf:
        n2 = nn[1]
        nu = nu - y * c * (n2 - n)
        n = n2
        y = y + t * nu / n
    efl = -1.0 / nu
    bfl = -y / nu
    return efl, bfl


def stop_index(surf):
    return 2


def trace(surf, field_deg, fno, img_dist, filt=True, n_ring=3, pts=None, return_launch=False):
    """Trace a pupil grid at one field angle; returns image xy (wl, rays, 2) and validity."""
    efl, _ = paraxial(surf)
    # entrance pupil: find by paraxial trace from stop backwards (approx): aim rays at stop via iteration
    epd = efl / fno
    # build pupil pattern on the STOP (aperture radius found by scaling marginal ray)
    # stop radius: paraxial marginal ray height at stop for EPD
    y, nu, n = epd / 2, 0.0, 1.0
    for i, (c, t, nn) in enumerate(surf[:stop_index(surf)]):
        n2 = nn[1]; nu = nu - y * c * (n2 - n); n = n2; y = y + t * nu / n
    r_stop = abs(y)
    if pts is not None:
        pts = np.asarray(pts, float)
    else:
      pts = [(0.0, 0.0)]
      for k in range(1, n_ring + 1):
        m = 6 * k
        for j in range(m):
            a = 2 * np.pi * j / m
            rr = k / n_ring
            pts.append((rr * np.cos(a), rr * np.sin(a)))
      pts = np.array(pts)
    out = []
    ok_all = []
    th = np.radians(field_deg)
    dirv = np.array([0.0, np.sin(th), np.cos(th)])
    # Entrance pupil (paraxial image of the stop through the front element), from y-nu matrices:
    # object-space ray (y, u) at vertex 1 -> stop: y_s = A y + B u ; EP at z = B/A, radius r_stop/A.
    def to_stop(y, u):
        n = 1.0; nu = u
        for c, t, nn in surf[:stop_index(surf)]:
            n2 = nn[1]; nu = nu - y * c * (n2 - n); n = n2; y = y + t * nu / n
        return y
    A = to_stop(1.0, 0.0)
    B = to_stop(0.0, 1.0)
    z_ep, r_ep = B / A, epd / 2
    # aim the chief ray (real) at the stop centre with a 1D secant search on the launch height
    z_l = -40.0
    def chief_hit(y0):
        P = np.array([[0.0, y0, z_l]])
        h, _, ok = propagate(surf, P, dirv, 1, upto=stop_index(surf))
        return h[0, 1], ok[0]
    y_a = (z_ep - z_l) * -np.tan(th)                  # paraxial aim through the EP centre
    y_b = y_a + 0.01
    f_a, _ = chief_hit(y_a)
    f_b, _ = chief_hit(y_b)
    for _ in range(12):
        if abs(f_b - f_a) < 1e-12:
            break
        y_c = y_b - f_b * (y_b - y_a) / (f_b - f_a)
        y_a, f_a = y_b, f_b
        y_b = y_c
        f_b, okc = chief_hit(y_b)
        if abs(f_b) < 1e-7:
            break
    # pupil grid on the EP plane, centred on the aimed chief ray (circular EP: ignores pupil aberration)
    y_ep = y_b + (z_ep - z_l) * np.tan(th)
    start = np.zeros((len(pts), 3))
    start[:, 0] = pts[:, 0] * r_ep
    start[:, 1] = y_ep + pts[:, 1] * r_ep * np.cos(th)
    start[:, 2] = z_ep
    start = start - dirv * (z_ep - z_l) / dirv[2]      # back up to the launch plane along the ray
    if return_launch:
        return start, dirv
    for wi in range(3):
        p, v, ok = propagate(surf, start, dirv, wi, img_dist=img_dist, filt=filt)
        out.append(p[:, :2]); ok_all.append(ok)
    return np.array(out), np.array(ok_all)


def propagate(surf, P, d, wi, upto=None, img_dist=None, filt=True):
    P = P.copy().astype(float)
    D = np.tile(d, (len(P), 1)).astype(float)
    n = 1.0
    z0 = 0.0
    ok = np.ones(len(P), bool)
    seq = list(surf)
    if upto is None:
        seq = seq[:-1] + [(seq[-1][0], 0.0, seq[-1][2])]
    for i, (c, t, nn) in enumerate(seq if upto is None else seq[:upto + 1]):
        # intersect sphere with vertex at z0, curvature c
        Pz = P - np.array([0, 0, z0])
        if c == 0:
            s = -Pz[:, 2] / D[:, 2]
        else:
            F = c * (Pz ** 2).sum(1) - 2 * Pz[:, 2]
            G = D[:, 2] - c * (Pz * D).sum(1)
            disc = G * G - c * F
            ok &= disc >= 0
            s = F / (G + np.sqrt(np.clip(disc, 0, None)))
        P = P + D * s[:, None]
        if upto is not None and i == upto:
            return P, D, ok
        Pz = P - np.array([0, 0, z0])
        if c == 0:
            N = np.tile([0, 0, -1.0], (len(P), 1))
        else:
            N = np.column_stack([-c * Pz[:, 0], -c * Pz[:, 1], 1 - c * Pz[:, 2]])
            N = -N / np.linalg.norm(N, axis=1)[:, None]
        n2 = nn[wi]
        if n2 != n:
            mu = n / n2
            cosi = -(N * D).sum(1)
            k = 1 - mu ** 2 * (1 - cosi ** 2)
            ok &= k >= 0
            D = mu * D + (mu * cosi - np.sqrt(np.clip(k, 0, None)))[:, None] * N
        n = n2
        # aperture check: semi-diameter limit 0.95/|c|
        if c != 0:
            ok &= np.hypot(P[:, 0], P[:, 1]) < 0.9 / abs(c)
        z0 += t
    # after last surface: optional IR-cut plate (1.0 mm N-BK7) starting 0.5 mm behind
    z_last = z0
    if filt:
        for (zz, n2) in ((z_last + 0.5, GLASS["N-BK7"][wi]), (z_last + 1.5, 1.0)):
            s = (zz - P[:, 2]) / D[:, 2]
            P = P + D * s[:, None]
            mu = n / n2
            N = np.tile([0, 0, -1.0], (len(P), 1))
            cosi = -(N * D).sum(1)
            k = 1 - mu ** 2 * (1 - cosi ** 2)
            D = mu * D + (mu * cosi - np.sqrt(np.clip(k, 0, None)))[:, None] * N
            n = n2
    zi = z_last + img_dist
    s = (zi - P[:, 2]) / D[:, 2]
    P = P + D * s[:, None]
    return P, D, ok


FIELDS = np.array([0.0, 0.5, 0.75, 1.0])
FW = np.array([1.0, 1.0, 1.0, 0.8])


def scaled(p, k):
    q = np.array(p, float).copy()
    return q * k


def evaluate(p, fno, img_dist=None, verbose=False):
    efl0, _ = paraxial(build(p))
    if not (0 < efl0 < 200):
        return 1e6, None
    surf = build(p, EFL_TARGET / efl0)
    efl, bfl = paraxial(surf)
    if img_dist is None:
        img_dist = bfl + 1.0 * (1 - 1 / 1.5168)      # filter shifts focus back ~t(1-1/n)
    half_ang = np.degrees(np.arctan(HALF / EFL_TARGET))
    rms, chief, dist = [], [], []
    for f in FIELDS:
        xy, ok = trace(surf, f * half_ang, fno, img_dist)
        if not ok.all():
            return 1e6, None
        c = (xy[1, 0])                          # chief ray at d-line approx = pupil centre
        d = xy - c
        r2 = (d ** 2).sum(-1).mean(-1)
        rms.append(np.sqrt((r2 * WW).sum() / WW.sum()))
        chief.append(c[1])
    rms = np.array(rms)
    return (rms * FW) @ (rms * FW), dict(efl=efl, bfl=bfl, img=img_dist, rms=rms, chief=np.array(chief))


if __name__ == "__main__":
    p0 = [18.0, 5.0, 7.0, 1.0, 10.0, -4.5, -12.0, 0.4, 14.0, -14.0]
    print(evaluate(p0, 4.0))
