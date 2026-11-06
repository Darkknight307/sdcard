#!/usr/bin/env python3
"""weak_scale_bench.py - Python multiprocessing weak-scaling benchmark.

Same workload as weak_scale_bench.c: midpoint integration of 4/(1+x^2) on [0,1].
Each worker integrates K points (in NumPy blocks), so N(P) = P*K.

Run:  python weak_scale_bench.py --k 40000000 --runs 5 --threads 1 2 3 4 6 8 \
          --out ../results.csv
"""
import argparse
import csv
import math
import multiprocessing as mp
import os
import time

import numpy as np

BLOCK = 2_000_000


def integrate_slice(start, count, h):
    total = 0.0
    for b in range(start, start + count, BLOCK):
        m = min(BLOCK, start + count - b)
        x = (np.arange(b, b + m, dtype=np.float64) + 0.5) * h
        total += float(np.sum(4.0 / (1.0 + x * x)))
    return total


def run_once(pool, p, k):
    h = 1.0 / (p * k)
    tasks = [(i * k, k, h) for i in range(p)]
    t0 = time.perf_counter()
    total = sum(pool.starmap(integrate_slice, tasks, chunksize=1))
    return time.perf_counter() - t0, total * h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=40_000_000, help="points per worker")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--threads", type=int, nargs="+",
                    default=list(range(1, (os.cpu_count() or 1) + 1)))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "..", "results.csv"))
    a = ap.parse_args()
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["P", "run", "time_s", "points_per_thread", "total_points",
                    "pi_estimate", "abs_error"])
        for p in a.threads:
            with mp.Pool(p) as pool:          # pool start-up is not timed
                run_once(pool, p, max(1, a.k // 20))  # warm-up
                for r in range(1, a.runs + 1):
                    t, pi = run_once(pool, p, a.k)
                    w.writerow([p, r, f"{t:.6f}", a.k, p * a.k, f"{pi:.12f}",
                                f"{abs(pi - math.pi):.3e}"])
                    print(f"P={p:2d} run={r}  T={t:.4f} s  pi={pi:.10f}")
    print("Saved", os.path.abspath(a.out))


if __name__ == "__main__":
    mp.freeze_support()
    main()
