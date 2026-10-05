import numpy as np
D = np.load("data_e18.npz"); ARR = D["arr"]; RUNS = [r.split("|") for r in D["runs"]]; LENS = D["lens"]
def idx(o): return o // 4 if o < 0x200 else 128 + (o - 0x3710) // 4
def W(i, k, o): return ARR[i, :LENS[i], k, idx(o)]
def F(i, k, o): return W(i, k, o).astype(np.uint32).view("<f4")
def B(i, k, o):  # byte
    w = W(i, k, o & ~3); return (w >> (8 * (o & 3))) & 0xFF
