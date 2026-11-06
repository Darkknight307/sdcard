#!/usr/bin/env python3
"""fit_gustafson.py - statistics, least-squares fit and plots for the weak-scaling runs.

Reads the raw benchmark data (benchmarks/results.csv, 5 runs per thread count),
computes mean / standard deviation / standard error per thread count, derives the
scaled speedup S(P) = P * T(1) / T(P), and fits Gustafson's law

    S(P) = P - alpha (P - 1)   <=>   (P - S) = alpha (P - 1)

by least squares through the origin. Only P <= hardware concurrency is fitted
(oversubscribed points are reported and plotted separately).

Outputs:
    benchmarks/results_summary.csv   per-P statistics
    benchmarks/fit_results.json      alpha_observed, its standard error, R^2
    plots/scaling_comparison.png/.pdf   Task 24 figure

Usage:  python fit_gustafson.py [--csv results.csv] [--hw N]
"""

import argparse
import csv
import json
import math
import os
import statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(path):
    times = defaultdict(list)
    with open(path) as f:
        for row in csv.DictReader(f):
            times[int(row["P"])].append(float(row["time_s"]))
    return dict(sorted(times.items()))


def summarise(times):
    t1 = statistics.mean(times[1])
    se1 = statistics.stdev(times[1]) / math.sqrt(len(times[1])) if len(times[1]) > 1 else 0.0
    out = []
    for p, ts in times.items():
        n = len(ts)
        mean = statistics.mean(ts)
        sd = statistics.stdev(ts) if n > 1 else 0.0
        se = sd / math.sqrt(n)
        s = p * t1 / mean
        # error propagation for S = P * T1 / TP (independent errors)
        s_se = s * math.sqrt((se1 / t1) ** 2 + (se / mean) ** 2) if p > 1 else 0.0
        kf = ((1 / s - 1 / p) / (1 - 1 / p)) if p > 1 else None
        out.append({"P": p, "runs": n, "mean_time_s": mean, "std_time_s": sd,
                    "se_time_s": se, "cv_percent": 100 * sd / mean,
                    "scaled_speedup": s, "speedup_se": s_se, "efficiency": s / p,
                    "karp_flatt_e": kf})
    return out


def fit_alpha(rows):
    """Least squares through the origin of y = P - S on x = P - 1."""
    xs = [r["P"] - 1 for r in rows]
    ys = [r["P"] - r["scaled_speedup"] for r in rows]
    sxx = sum(x * x for x in xs)
    if sxx == 0:
        raise SystemExit("need at least one P > 1 to fit alpha")
    alpha = sum(x * y for x, y in zip(xs, ys)) / sxx
    resid = [y - alpha * x for x, y in zip(xs, ys)]
    dof = max(1, len(xs) - 1)
    se = math.sqrt(sum(e * e for e in resid) / dof / sxx)
    s_obs = [r["scaled_speedup"] for r in rows]
    s_fit = [r["P"] - alpha * (r["P"] - 1) for r in rows]
    mean_s = statistics.mean(s_obs)
    ss_tot = sum((s - mean_s) ** 2 for s in s_obs)
    ss_res = sum((a - b) ** 2 for a, b in zip(s_obs, s_fit))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return alpha, se, r2


def plot(summary, fitted, alpha, alpha_se, hw, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pmax = max(r["P"] for r in summary)
    grid = [1 + i * (pmax - 1) / 200 for i in range(201)]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.5, 5), gridspec_kw={"width_ratios": [3, 2]})
    ax.plot(grid, grid, "k--", lw=1.2, label="(1) Ideal linear S = P")
    ax.plot(grid, [p - alpha * (p - 1) for p in grid], "-", color="#1f77b4", lw=2,
            label=f"(2) Gustafson fit, α = {alpha:.4f} ± {alpha_se:.4f}")
    ax.plot(grid, [1 / (alpha + (1 - alpha) / p) for p in grid], "-.", color="#d62728", lw=2,
            label=f"(4) Amdahl, same s = {alpha:.4f}")
    inside = [r for r in summary if r["P"] <= hw]
    over = [r for r in summary if r["P"] > hw]
    ax.errorbar([r["P"] for r in inside], [r["scaled_speedup"] for r in inside],
                yerr=[r["speedup_se"] for r in inside], fmt="o", color="#2ca02c", ms=7,
                capsize=5, label="(3) Measured (mean ± SE, 5 runs)")
    if over:
        ax.errorbar([r["P"] for r in over], [r["scaled_speedup"] for r in over],
                    yerr=[r["speedup_se"] for r in over], fmt="s", mfc="none",
                    color="#ff7f0e", ms=7, capsize=5,
                    label=f"Measured, oversubscribed (P > {hw} HW threads)")
    ax.axvline(hw, color="grey", lw=0.8, ls=":")
    ax.text(hw, ax.get_ylim()[1] * 0.97 if ax.get_ylim()[1] else pmax, f" HW threads = {hw}",
            va="top", fontsize=8, color="grey")
    ax.set_xlabel("Threads P")
    ax.set_ylabel("Scaled speedup S(P) = P·T(1)/T(P)")
    ax.set_title("Weak scaling: measured vs. Gustafson vs. Amdahl")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")

    ax2.errorbar([r["P"] for r in summary], [r["efficiency"] for r in summary],
                 yerr=[r["speedup_se"] / r["P"] for r in summary], fmt="o-", capsize=4,
                 color="#2ca02c", label="Measured E(P)")
    ax2.plot(grid, [(p - alpha * (p - 1)) / p for p in grid], "-", color="#1f77b4",
             label="Gustafson fit E(P)")
    ax2.axvline(hw, color="grey", lw=0.8, ls=":")
    ax2.set_ylim(0, 1.1)
    ax2.set_xlabel("Threads P")
    ax2.set_ylabel("Efficiency E(P) = S/P")
    ax2.set_title("Weak-scaling efficiency")
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=300)
    fig.savefig(os.path.splitext(path)[0] + ".pdf")
    print("Saved plots", path, "and .pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=os.path.join(HERE, "results.csv"))
    ap.add_argument("--hw", type=int, default=os.cpu_count(),
                    help="hardware concurrency; only P <= hw is fitted")
    ap.add_argument("--plot", default=os.path.join(ROOT, "plots", "scaling_comparison.png"))
    ap.add_argument("--no-plot", action="store_true")
    a = ap.parse_args()

    summary = summarise(load(a.csv))
    fitted = [r for r in summary if r["P"] <= a.hw]
    alpha, alpha_se, r2 = fit_alpha(fitted)

    with open(os.path.join(HERE, "results_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()) + ["gustafson_fit_speedup"])
        w.writeheader()
        for r in summary:
            row = {k: (round(v, 6) if isinstance(v, float) else ("N/A" if v is None else v))
                   for k, v in r.items()}
            row["gustafson_fit_speedup"] = round(r["P"] - alpha * (r["P"] - 1), 6)
            w.writerow(row)
    fit = {"alpha_observed": alpha, "alpha_standard_error": alpha_se, "r_squared": r2,
           "fitted_thread_counts": [r["P"] for r in fitted],
           "hardware_concurrency": a.hw,
           "model": "S(P) = P - alpha (P - 1), least squares through origin on (P-1, P-S)"}
    with open(os.path.join(HERE, "fit_results.json"), "w") as f:
        json.dump(fit, f, indent=2)

    print(f"{'P':>3} {'mean T':>9} {'std':>8} {'CV%':>6} {'S(P)':>8} {'±SE':>7} {'E(P)':>7} {'K-F e':>8}")
    for r in summary:
        kf = "N/A" if r["karp_flatt_e"] is None else f"{r['karp_flatt_e']:.4f}"
        flag = "  (oversubscribed)" if r["P"] > a.hw else ""
        print(f"{r['P']:>3} {r['mean_time_s']:>9.4f} {r['std_time_s']:>8.4f} {r['cv_percent']:>6.2f} "
              f"{r['scaled_speedup']:>8.3f} {r['speedup_se']:>7.3f} {r['efficiency']:>7.4f} {kf:>8}{flag}")
    print(f"\nalpha_observed = {alpha:.5f} ± {alpha_se:.5f}   (R² = {r2:.5f}, "
          f"fitted on P = {fit['fitted_thread_counts']})")
    if not a.no_plot:
        plot(summary, fitted, alpha, alpha_se, a.hw, a.plot)


if __name__ == "__main__":
    main()
