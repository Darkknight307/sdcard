#!/usr/bin/env python3
"""Parametric speedup simulator: Amdahl (strong scaling) vs. Gustafson (weak scaling).

Models both laws across arbitrary core counts (1 <= P <= 65,536) and serial
fractions (0.001 <= alpha <= 0.20), writes a tidy CSV and draws overlay plots.

Examples
--------
    python simulator.py                                  # default sweep
    python simulator.py --alphas 0.04 --cores 16 64 256 1024 4096 16384
    python simulator.py --pmax 65536 --alphas 0.001 0.01 0.05 0.1 0.2 \
                        --csv sim.csv --plot sim.png
"""

import argparse
import csv
import os
import sys

P_MIN, P_MAX = 1, 65_536
ALPHA_MIN, ALPHA_MAX = 0.001, 0.20
HERE = os.path.dirname(os.path.abspath(__file__))


def amdahl(p, s):
    """Fixed-size speedup: S = 1 / (s + (1 - s)/P)."""
    return 1.0 / (s + (1.0 - s) / p)


def gustafson(p, alpha):
    """Fixed-time (scaled) speedup: S = P - alpha (P - 1)."""
    return p - alpha * (p - 1)


def power_of_two_cores(pmax):
    cores, p = [], 1
    while p <= pmax:
        cores.append(p)
        p *= 2
    if cores[-1] != pmax:
        cores.append(pmax)
    return cores


def simulate(cores, alphas):
    rows = []
    for a in alphas:
        for p in cores:
            sa, sg = amdahl(p, a), gustafson(p, a)
            rows.append({
                "alpha": a,
                "P": p,
                "amdahl_speedup": round(sa, 6),
                "amdahl_efficiency": round(sa / p, 6),
                "gustafson_speedup": round(sg, 6),
                "gustafson_efficiency": round(sg / p, 6),
                "ratio_gustafson_over_amdahl": round(sg / sa, 6),
            })
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def plot(rows, alphas, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed - skipping plot (pip install matplotlib)")
        return
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))
    cmap = plt.get_cmap("viridis")
    cores = sorted({r["P"] for r in rows})
    ax1.plot(cores, cores, "k--", lw=1, label="Ideal (S = P)")
    for i, a in enumerate(alphas):
        c = cmap(i / max(1, len(alphas) - 1))
        sub = [r for r in rows if r["alpha"] == a]
        ps = [r["P"] for r in sub]
        ax1.plot(ps, [r["gustafson_speedup"] for r in sub], "-", color=c,
                 label=f"Gustafson α={a}")
        ax1.plot(ps, [r["amdahl_speedup"] for r in sub], ":", color=c, lw=2,
                 label=f"Amdahl s={a}")
        ax2.plot(ps, [r["gustafson_efficiency"] for r in sub], "-", color=c)
        ax2.plot(ps, [r["amdahl_efficiency"] for r in sub], ":", color=c, lw=2)
    for ax in (ax1, ax2):
        ax.set_xscale("log", base=2)
        ax.set_xlabel("Processors P")
        ax.grid(True, which="both", alpha=0.3)
    ax1.set_yscale("log", base=2)
    ax1.set_ylabel("Speedup S(P)")
    ax1.set_title("Strong (dotted) vs. weak (solid) scaling: speedup")
    ax1.legend(fontsize=7, ncol=2)
    ax2.set_ylabel("Efficiency E(P) = S/P")
    ax2.set_ylim(0, 1.05)
    ax2.set_title("Parallel efficiency")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    if path.endswith(".png"):
        fig.savefig(path[:-4] + ".pdf")
    print(f"Saved plot   {path}")


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alphas", type=float, nargs="+",
                    default=[0.001, 0.01, 0.04, 0.08, 0.20],
                    help="serial fractions to model (0.001-0.20)")
    ap.add_argument("--cores", type=int, nargs="+",
                    help="explicit core counts; default = powers of two up to --pmax")
    ap.add_argument("--pmax", type=int, default=P_MAX, help="largest P (<= 65536)")
    ap.add_argument("--csv", default=os.path.join(HERE, "simulator_results.csv"))
    ap.add_argument("--plot", default=os.path.join(HERE, "..", "plots", "simulator_overlay.png"))
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args(argv)
    for a in args.alphas:
        if not ALPHA_MIN <= a <= ALPHA_MAX:
            ap.error(f"alpha {a} outside [{ALPHA_MIN}, {ALPHA_MAX}]")
    if not P_MIN <= args.pmax <= P_MAX:
        ap.error(f"--pmax must be in [{P_MIN}, {P_MAX}]")
    if args.cores and any(not P_MIN <= p <= P_MAX for p in args.cores):
        ap.error(f"core counts must be in [{P_MIN}, {P_MAX}]")
    return args


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    cores = sorted(set(args.cores)) if args.cores else power_of_two_cores(args.pmax)
    rows = simulate(cores, args.alphas)
    write_csv(rows, args.csv)
    print(f"Saved CSV    {args.csv}  ({len(rows)} rows)")
    print(f"\n{'alpha':>6} {'P':>6} {'S_Amdahl':>10} {'S_Gustafson':>12} {'E_Gustafson':>12}")
    for r in rows:
        if r["P"] in (cores[0], cores[len(cores) // 2], cores[-1]):
            print(f"{r['alpha']:>6} {r['P']:>6} {r['amdahl_speedup']:>10.3f} "
                  f"{r['gustafson_speedup']:>12.3f} {r['gustafson_efficiency']:>12.5f}")
    if not args.no_plot:
        os.makedirs(os.path.dirname(os.path.abspath(args.plot)), exist_ok=True)
        plot(rows, args.alphas, args.plot)


if __name__ == "__main__":
    main()
