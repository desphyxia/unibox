"""The border collie's shape (collie.py), as one signed distance field: a sitting dog of blended ellipsoids and round
cones (rump and haunches on the ground, the chest upright, straight front legs, the hind legs folded along the ground),
a head with a stop, a tapering muzzle, a lower jaw dropped open in a smile, eye sockets and a black nose. Uses the
primitives and the mesher from unicorn2_shape.py.

Axes (Blender): x forward, y across (+y the near side), z up; ground z = 0. The head is modelled straight in
"head-local" coordinates, then tilted, turned toward the viewer and tipped to one side (HEAD_*)."""
import numpy as np
from unicorn2_shape import (sphere, ellipsoid, round_cone, squash, smin, smax, rot, sample, surface_nets, project, grad,
                            _len)

HEAD_PIVOT = np.array([0.52, 0.0, 2.85])                      # where the neck meets the head
HEAD_YAW = 20.0                                               # toward the viewer
HEAD_PITCH = -4.0                                             # chin up a little, looking at you
HEAD_ROLL = 9.0                                               # the curious head tilt
HEAD_M = rot((0, 0, 1), HEAD_YAW) @ rot((0, 1, 0), HEAD_PITCH) @ rot((1, 0, 0), HEAD_ROLL)


def head_to_world(L):
    return HEAD_PIVOT + (np.asarray(L) - HEAD_PIVOT) @ HEAD_M.T


def world_to_head(P):
    return HEAD_PIVOT + (P - HEAD_PIVOT) @ HEAD_M


def head_dir(v):
    return np.asarray(v) @ HEAD_M.T


SKULL = (np.array([0.62, 0.0, 3.38]), np.array([0.6, 0.56, 0.54]))
NOSE = (np.array([1.66, 0.0, 3.14]), np.array([0.12, 0.145, 0.1]))
MOUTH = (np.array([1.26, 0.0, 2.97]), np.array([0.42, 0.21, 0.075]))
TONGUE = (np.array([1.28, 0.0, 2.93]), np.array([0.27, 0.17, 0.055]))
EYE_HALF = (0.15, 0.11)


def _head_raw(L):
    c, r = SKULL
    d = ellipsoid(L, c, r)
    d = smin(d, sphere(L, np.array([0.96, 0.0, 3.4]), 0.35), 0.25)                       # the stop and brow
    d = smin(d, ellipsoid(L, np.array([0.86, 0.0, 3.12]), (0.42, 0.5, 0.32)), 0.2)      # cheeks
    d = smin(d, squash(round_cone, L, 0.9, (1.0, 0.0, 3.2), (1.56, 0.0, 3.1), 0.3, 0.2), 0.16)   # the muzzle
    d = smin(d, ellipsoid(L, NOSE[0], NOSE[1]), 0.06)
    jaw = squash(round_cone, L, 0.85, (0.88, 0.0, 2.94), (1.4, 0.0, 2.82), 0.24, 0.13)
    d = smin(d, jaw, 0.08)
    return d


def _ray_hit(fn, o, d, lo=0.0, hi=2.0):
    o = np.asarray(o, np.float64)
    d = np.asarray(d, np.float64) / np.linalg.norm(d)
    for _ in range(60):
        m = (lo + hi) / 2
        if fn((o + d * m)[None])[0] < 0:
            lo = m
        else:
            hi = m
    return o + d * lo


def _eye_frame(side):
    c, _ = SKULL
    E = _ray_hit(_head_raw, c, np.array([0.86, 0.44 * side, 0.15]))
    n = grad(_head_raw, E[None])[0]
    u = np.array([1.0, 0.0, 0.0]) - n * n[0]
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    if v[2] < 0:
        v = -v
    return E, n, u, v


EYES = {s: _eye_frame(s) for s in (1, -1)}


def almond(u, v):
    a, b = EYE_HALF
    v = v + 0.12 * u                                           # the outer (back) corner a little higher
    x = np.clip(np.abs(u) / a, 0.0, 1.0)
    top = b * (1.0 - x ** 2.4) ** 0.6
    bot = b * 0.92 * (1.0 - x ** 2.0) ** 0.7
    return np.maximum(np.abs(u) - a, np.abs(v) - np.where(v >= 0, top, bot))


def _socket(L, side):
    E, n, u, v = EYES[side]
    q = L - E
    return np.maximum(almond(q @ u, q @ v), np.maximum(q @ n - 0.3, -(q @ n) - 0.22))


def eye_ball(side):
    E, n, u, v = EYES[side]
    R = 0.2
    return E - n * (R + 0.008), R


def head_sdf(L):
    d = _head_raw(L)
    for s in (1, -1):
        d = smax(d, -_socket(L, s), 0.025)
    c, r = MOUTH
    d = smax(d, -ellipsoid(L, c, r), 0.03)                    # the open mouth
    for s in (1, -1):                                          # nostrils
        d = smax(d, -ellipsoid(L, NOSE[0] + np.array([0.1, 0.055 * s, 0.0]), (0.03, 0.022, 0.02)), 0.015)
    return d


# ------------------------------------------------------------------ body (world)
LEGS = {
    # front legs straight down from the chest to the paws; the paws point forward
    "nf": [((0.42, 0.27, 1.4), 0.2), ((0.55, 0.29, 0.5), 0.13), ((0.6, 0.3, 0.16), 0.12)],
    "ff": [((0.42, -0.27, 1.4), 0.2), ((0.55, -0.29, 0.5), 0.13), ((0.6, -0.3, 0.16), 0.12)],
}
PAWS = {"nf": (0.7, 0.3, 0.1), "ff": (0.7, -0.3, 0.1), "nh": (-0.08, 0.47, 0.09), "fh": (-0.08, -0.47, 0.09)}
TAIL_BASE = np.array([-1.18, 0.0, 0.55])


def paw(P, c, fwd=1.0):
    c = np.asarray(c, np.float64)
    d = ellipsoid(P, c, (0.19, 0.14, 0.095))
    for k in (-1.5, -0.5, 0.5, 1.5):                            # four toes
        d = smin(d, sphere(P, c + np.array([0.13 * fwd, 0.055 * k, -0.01]), 0.055), 0.03)
    return d


def body_sdf(P):
    rump = ellipsoid(P, np.array([-0.55, 0.0, 0.78]), (0.72, 0.68, 0.72))
    torso = squash(round_cone, P, 0.92, (-0.4, 0.0, 1.0), (0.2, 0.0, 1.85), 0.68, 0.6)
    chest = ellipsoid(P, np.array([0.32, 0.0, 1.7]), (0.55, 0.58, 0.75))
    d = smin(smin(rump, torso, 0.3), chest, 0.3)
    return d


def neck_sdf(P):
    return squash(round_cone, P, 0.9, (0.28, 0.0, 2.1), (0.52, 0.0, 2.88), 0.52, 0.42)


def front_leg(P, name):
    j = LEGS[name]
    d = None
    for (a, ra), (b, rb) in zip(j[:-1], j[1:]):
        x = round_cone(P, np.array(a), np.array(b), ra, rb)
        d = x if d is None else smin(d, x, 0.06)
    return smin(d, paw(P, PAWS[name]), 0.06)


def hind_leg(P, side):
    s = 1 if side == "nh" else -1
    thigh = ellipsoid(P, np.array([-0.45, 0.42 * s, 0.72]), (0.56, 0.3, 0.5))
    hock = round_cone(P, np.array([-0.82, 0.43 * s, 0.32]), np.array([-0.2, 0.46 * s, 0.12]), 0.14, 0.11)
    d = smin(thigh, hock, 0.15)
    return smin(d, paw(P, PAWS[side]), 0.06)


def parts(P):
    out = {"body": body_sdf(P), "neck": neck_sdf(P), "head": head_sdf(world_to_head(P))}
    for n in ("nf", "ff"):
        out[n] = front_leg(P, n)
    for n in ("nh", "fh"):
        out[n] = hind_leg(P, n)
    return out


def sdf(P):
    p = parts(P)
    d = smin(p["body"], p["neck"], 0.3)
    for n in ("nf", "ff", "nh", "fh"):
        d = smin(d, p[n], 0.16)
    return smin(d, p["head"], 0.22)


def sdf_raw(P):
    """the same without the eyes, mouth and nostrils carved (to place things on the face)"""
    p = parts(P)
    d = smin(p["body"], p["neck"], 0.3)
    for n in ("nf", "ff", "nh", "fh"):
        d = smin(d, p[n], 0.16)
    return smin(d, _head_raw(world_to_head(P)), 0.22)
