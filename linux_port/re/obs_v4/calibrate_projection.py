"""calibrate_projection.py -- world -> screen projection for the obs-v4 overlay, from the camera in RAM.

Camera (re/stage_geometry STAGE.md section 3): back vector (unit, target -> eye) at 0x8C541194 (CONFIRMED yaw),
eye position at 0x8C5411A4 (LIKELY). The view basis is built from those two; the intrinsics (fx, fy, cx, cy) and
a per-object-type height offset are FITTED here by ABLATION (the items_ground p05 method): at several frames, every
category-9 ledger object is lifted 3000 u for 3 frames from a restored savestate and the rendered frame is diffed
against the untouched one; the diff bbox centre is where that object is drawn. Least squares on 2/3 of the
correspondences, accuracy reported on the held-out 1/3. Writes projection.json (used by overlay_v4.py).
    python re/obs_v4/calibrate_projection.py        (from linux_port/, PYTHONPATH=../sdlarch-rl:.)
"""
import json
import os
import random
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import obs_v4_reader as V  # noqa: E402
import test_obs_v4 as T  # noqa: E402

CAM_BACK, CAM_EYE = 0x8C541194, 0x8C5411A4


def f3(ram, a):
    return np.array(struct.unpack_from("<3f", ram, a - V.RAM_BASE), np.float64)


def cam_coords(ram, P):
    """world points [N,3] -> camera coords (right, up, forward)."""
    back = f3(ram, CAM_BACK)
    eye = f3(ram, CAM_EYE)
    fwd = -back / np.linalg.norm(back)
    r = np.cross(fwd, [0.0, 1.0, 0.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, fwd)
    d = np.atleast_2d(P) - eye
    return np.stack([d @ r, d @ u, d @ fwd], 1)


def project(ram, P, K):
    c = cam_coords(ram, P)
    z = np.maximum(c[:, 2], 1.0)
    return np.stack([K["cx"] + K["fx"] * c[:, 0] / z, K["cy"] - K["fy"] * c[:, 1] / z], 1), c[:, 2] > 1.0


def frame(br):
    h, w = br.emu.get_shape()
    arr = np.zeros((h, w, 3), np.uint8)
    br.emu.get_frame(arr, w, h)
    return arr[::-1].copy()


def collect(br, slot, frames_at, rng):
    T.load(br, slot)
    ram = br.ram
    lo = V.LEDGER_LO - V.RAM_BASE
    out, f = [], 0
    for F in frames_at:
        while f < F:
            br.press(rng.choice(T.MOVES), 6, player=1)
            f += 6
        br.clear_inputs()
        st = br.emu.get_state()
        br.emu.set_state(st); br.run_frames(3)
        base = frame(br)
        back, eye = f3(ram, CAM_BACK), f3(ram, CAM_EYE)
        L = ram[lo:lo + V.LEDGER_N * V.LEDGER_STRIDE].reshape(V.LEDGER_N, V.LEDGER_STRIDE)
        cand = []
        for k in range(V.LEDGER_N):
            if L[k, 4] != 9:
                continue
            t, s_ = int(L[k, 0x420]), int(L[k, 0x421])
            if s_ in (5, 7) or not (t in (0xC2, 0xC3, 0xC8) or 1 <= t <= 0x77):
                continue
            x, y, z = struct.unpack_from("<3f", L[k], 0x2C)
            if x == 0 and y == 0 and z == 0:
                continue
            cand.append((k, t, (x, y, z)))
        for k, t, pos in cand:
            br.emu.set_state(st)
            a = lo + k * V.LEDGER_STRIDE
            y0 = {o: struct.unpack_from("<f", ram, a + o)[0] for o in (0x30, 0x9C)}
            for _ in range(3):
                for o in (0x30, 0x9C):
                    struct.pack_into("<f", ram, a + o, y0[o] + 3000.0)
                br.run_frames(1)
            d = np.abs(frame(br).astype(int) - base.astype(int)).sum(2) > 40
            if d.sum() < 12:
                continue
            ys, xs = np.nonzero(d)
            if xs.max() - xs.min() > 300:          # object plus something else changed: skip
                continue
            out.append(dict(slot=slot, F=F, type=t, pos=pos, back=back.tolist(), eye=eye.tolist(),
                            uv=((xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0),
                            bottom=float(ys.max()), px=int(d.sum())))
        br.emu.set_state(st)
    return out


def fit(rows, h_by_type):
    A, b = [], []
    for r in rows:
        P = np.array(r["pos"]) + [0, h_by_type.get(r["type"], h_by_type["item"]), 0]
        back, eye = np.array(r["back"]), np.array(r["eye"])
        fwd = -back / np.linalg.norm(back); rr = np.cross(fwd, [0, 1, 0]); rr /= np.linalg.norm(rr)
        uu = np.cross(rr, fwd); d = P - eye
        c = np.array([d @ rr, d @ uu, d @ fwd])
        A.append([c[0] / c[2], 0, 1, 0]); b.append(r["uv"][0])
        A.append([0, -c[1] / c[2], 0, 1]); b.append(r["uv"][1])
    sol, *_ = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)
    return dict(fx=sol[0], fy=sol[1], cx=sol[2], cy=sol[3])


def residuals(rows, K, h_by_type):
    e = []
    for r in rows:
        P = np.array(r["pos"]) + [0, h_by_type.get(r["type"], h_by_type["item"]), 0]
        back, eye = np.array(r["back"]), np.array(r["eye"])
        fwd = -back / np.linalg.norm(back); rr = np.cross(fwd, [0, 1, 0]); rr /= np.linalg.norm(rr)
        uu = np.cross(rr, fwd); d = P - eye
        c = np.array([d @ rr, d @ uu, d @ fwd])
        u, v = K["cx"] + K["fx"] * c[0] / c[2], K["cy"] - K["fy"] * c[1] / c[2]
        e.append(np.hypot(u - r["uv"][0], v - r["uv"][1]))
    return np.array(e)


def main():
    br = T.boot()
    rng = random.Random(11)
    rows = []
    for slot in (2, 3, 1):
        rows += collect(br, slot, (420, 1500, 2700), rng)
    keyt = lambda t: "chest" if t == 0xC2 else "cactus" if t == 0xC3 else "saguaro" if t == 0xC8 else "item"  # noqa
    for r in rows:
        r["kind"] = keyt(r["type"])
    rnd = random.Random(0)
    rnd.shuffle(rows)
    n_tr = (2 * len(rows)) // 3
    tr, te = rows[:n_tr], rows[n_tr:]
    best = None
    grid = range(0, 401, 25)
    for hc in grid:                       # visual-centre height above the object's position, per kind
        for hs in range(0, 801, 50):
            for hi in (0, 15, 30, 45, 60):
                for hch in (0, 20, 40, 60):
                    H = {0xC3: hc, 0xC8: hs, 0xC2: hch, "item": hi}
                    K = fit(tr, H)
                    e = residuals(tr, K, H).mean()
                    if best is None or e < best[0]:
                        best = (e, H, K)
    _, H, K = best
    e_tr, e_te = residuals(tr, K, H), residuals(te, K, H)
    per = {}
    for r, e in zip(te, e_te):
        per.setdefault(r["kind"], []).append(e)
    res = dict(method="RAM camera (eye 0x8C5411A4, back 0x8C541194) + ablation-fitted intrinsics",
               K={k: float(v) for k, v in K.items()}, h_by_type={str(k): v for k, v in H.items()},
               n_train=len(tr), n_test=len(te),
               train_px=dict(median=float(np.median(e_tr)), p90=float(np.percentile(e_tr, 90))),
               test_px=dict(median=float(np.median(e_te)), p90=float(np.percentile(e_te, 90)),
                            max=float(e_te.max())),
               test_by_kind={k: dict(n=len(v), median=float(np.median(v))) for k, v in per.items()})
    with open(os.path.join(HERE, "projection.json"), "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
