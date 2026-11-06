# Gustafson's Law & Weak Scaling: Practice Repository

Comprehensive practice for *Parallel & Distributed Computing Architecture*
(Gustafson's Law & Weak Scaling task sheet, Tasks 01–25). This README is the
executive technical guide: core rules, design guidelines, how to reproduce the
experiments, and an index of every artifact.

## Contents

1. [Core mathematical rules](#1-core-mathematical-rules)
2. [Key findings (Tasks 01–24)](#2-key-findings-tasks-0124)
3. [When to design around weak scaling](#3-when-to-design-software-around-gustafson-weak-scaling)
4. [Execution commands](#4-execution-commands)
5. [Artifact index](#5-artifact-index)
6. [Repository layout](#6-repository-layout)

---

## 1. Core mathematical rules

| Rule | Formula | Use it when |
|---|---|---|
| Amdahl (fixed size, strong scaling) | `S_A(P) = 1 / (s + (1 − s)/P)`, `S_A → 1/s` | Problem size is fixed; you want the same answer sooner |
| Gustafson (fixed time, weak scaling) | `S_G(P) = s + pP = P − α(P − 1)` | Problem grows with the machine; time per run is fixed |
| Weak-scaling efficiency | `E(P) = 1 − α(P − 1)/P → 1 − α` | Bounded loss, never below `1 − α` |
| Frame conversion | `s(P) = α / (α + (1 − α)P) → 0` | Turns a parallel-frame α into a uniprocessor s. Both laws then agree |
| Tolerable serial fraction | `α_max = (P − S_req)/(P − 1)` | Budget for serial code given a speedup target |
| With communication | `S_C(P) = (α + (1 − α)P)/(1 + C(P))` | `C = c log P`, `c√P` or `cP` (all-to-all saturates) |
| Sun–Ni (memory-bounded) | `S = (s + pG(P))/(s + pG(P)/P)` | `G = 1` gives Amdahl, `G = P` gives Gustafson; `G = P^{3/2}` for GEMM |
| Isoefficiency | `W = K·T_o(W, P)`, `K = E/(1 − E)` | Gustafson-compliant programs: `T_o = α(P − 1)`, so `W = Θ(P)` |
| Karp-Flatt (experimental α) | `e = (1/S − 1/P)/(1 − 1/P)` | Constant e means a genuine serial fraction; rising e means parallel overhead |
| Energy per work | `e_P/e_1 = 1 + (P_idle/(P_idle + P_active))(1/E − 1)` | Weak scaling always costs ≥ the 1-core energy per unit of work, but bounded |

## 2. Key findings (Tasks 01–24)

* **Laws are frames, not rivals.** Amdahl measures `s` on one processor for a
  fixed problem. Gustafson measures `α` on the parallel machine for a scaled one.
  Converted to the same frame they give identical speedups (Task 03). The 1988
  nCUBE result (1,016–1,021× on 1,024 processors at about 0.4% serial, against
  Amdahl's 201×) is the historical proof (Task 05).
* **Asymptotics.** `E_G → 1 − α` while `E_A → 0` (Task 04). With α = 0.04,
  efficiency stays ≥ 0.96 from 16 to 16,384 cores (Task 06). Meeting
  `S ≥ 7,500` on 8,192 cores tolerates `α ≤ 8.45%` (Task 07). At P = 128 and an
  8% serial fraction, Gustafson predicts 117.84× against Amdahl's 11.47×, a
  927% gap (Task 08). A 2% I/O + 6% sync workload reaches 471.12× at P = 512 and
  1,884.24× at P = 2,048 (Task 09).
* **Problem growth rates under fixed time.** A 3D grid with 32 GB per node:
  `N_max ∝ P^{1/3}`, 6,501³ at 64 nodes and 13,003³ at 512 nodes for 8 B per cell
  (Task 10). GEMM: `N ∝ P^{1/3}`, total memory `∝ P^{2/3}` (Task 16). 3D stencil
  with block decomposition: the communication-to-computation ratio `6/n` stays
  constant (Task 17). N-body: `N ∝ √P` for direct summation and `≈ P/log P` for
  Barnes–Hut (Task 18).
* **Where Gustafson breaks.** Iteration counts that grow with N (CG/Jacobi),
  all-to-all (FFT), serialised shared resources and memory-superlinear work
  (Task 13). Communication overhead `C(P)` makes efficiency decay
  (Task 12). Sun–Ni shows Gustafson under- or over-estimates when work grows
  faster or slower than memory (Task 11). Isoefficiency is linear only in the
  ideal case (Task 14). Graph analytics violates every assumption: hubs,
  random access, all-to-all, per-level barriers (Task 20).
* **Near-ideal workloads.** Monte Carlo with counter-based PRNGs and tree
  reductions keeps E ≈ 0.995 up to 10⁶ ranks. A linear reduction or root-side
  seeding destroys that (Task 19).
* **Energy.** Weak scaling multiplies total energy by about the work factor. The
  per-work penalty is `(1/E − 1)` times the static power share, about 1.7% at
  α = 0.04 (Task 15).
* **Empirical (Tasks 22–24).** OpenMP integration on a 4-vCPU Xeon gave
  `α_observed = 0.0558 ± 0.0089` (R² = 0.9993) for P = 1–4. Speedups of 1.90,
  2.87 and 3.86 fit Gustafson far better than Amdahl. The residual α is a
  constant multicore penalty (turbo or VM scheduling), shown by a falling
  Karp-Flatt e. Oversubscription beyond 4 threads caps S at about 3.8.

## 3. When to design software around Gustafson weak scaling

**Design for weak scaling when:**

1. Users want **more fidelity in the same time**: resolution, particles, samples,
   ensemble members. Most simulation and analytics workloads behave this way.
2. Work per node can be kept constant with **local, nearest-neighbour
   communication** (stencils, particles with cutoff forces, Monte Carlo, ensemble
   runs).
3. Memory grows with nodes and the algorithm's work grows about linearly with
   memory (`G(P) ≈ P`).

**Engineering rules:**

* Keep α **constant in absolute time**: parallel I/O (MPI-IO/HDF5), decentralised
  set-up, counter-based RNG, no root-centred loops.
* Replace every `O(P)` pattern by `O(log P)` (tree collectives) or `O(1)` (local
  exchange). Use 3D block decompositions for 3D grids.
* Overlap communication with computation (non-blocking halos) to shrink `C(P)`.
* Choose the per-node problem as large as memory allows. This amortises every
  fixed cost (Task 17, Task 19).
* Choose optimal-complexity algorithms (multigrid, FMM, Barnes–Hut), whose
  iteration count or work per element does not grow with N (Task 13).
* **Measure, don't assume:** run weak-scaling sweeps, fit α (Task 23) and track
  the Karp-Flatt metric. Rising e means communication or contention, not serial
  code.

**Prefer strong-scaling (Amdahl) thinking when** the problem is fixed by the
application: real-time control, interactive latency, a fixed-size inference
batch, or a time-to-solution SLA for one dataset.

## 4. Execution commands

Requirements: Python ≥ 3.9 with `numpy` and `matplotlib`, and a C compiler with
OpenMP (GCC, or Apple clang + `libomp`).

```bash
pip install numpy matplotlib

# Task 21: parametric simulator (CSV + overlay plots)
cd benchmarks
python simulator.py                                  # α ∈ {0.001,…,0.20}, P = 1 … 65,536
python simulator.py --alphas 0.04 --cores 16 64 256 1024 4096 16384   # Task 06 table

# Task 22: weak-scaling benchmark (OpenMP)
cd weak_scale_bench
make                                                 # Linux; macOS: see weak_scale_bench/README.md
./weak_scale_bench 500000000 5 1 2 3 4 6 8 > ../results.csv
#   alternative: python weak_scale_bench.py --k 40000000 --runs 5 --threads 1 2 3 4 6 8

# Tasks 23–24: statistics, least-squares α, plots
cd ..
python fit_gustafson.py --hw $(nproc)                # macOS: --hw $(sysctl -n hw.logicalcpu)
```

## 5. Artifact index

### Part I: Theory (`theory/`)

| Task | Artifact | Topic |
|---|---|---|
| 01 | [task01_scaling_models.md](theory/task01_scaling_models.md) | Amdahl vs. Gustafson assumptions; fixed-size vs. fixed-time |
| 02 | [task02_derivation.md](theory/task02_derivation.md) | First-principles derivation of `S = P − α(P − 1)` |
| 03 | [task03_serial_invariance.md](theory/task03_serial_invariance.md) | Frame of reference for the serial fraction; equivalence proof |
| 04 | [task04_asymptotic_limits.md](theory/task04_asymptotic_limits.md) | `lim E_G = 1 − α`, `lim E_A = 0` |
| 05 | [task05_historical_ncube.md](theory/task05_historical_ncube.md) | 1988 nCUBE 10 reconstruction |
| 11 | [task11_sun_ni_comparison.md](theory/task11_sun_ni_comparison.md) | Memory-bounded speedup vs. Gustafson |
| 12 | [task12_communication_penalty.md](theory/task12_communication_penalty.md) | Gustafson with `C(P)` = log P, √P, P |
| 13 | [task13_failure_cases.md](theory/task13_failure_cases.md) | CG/Jacobi, contention/FFT failure modes |
| 14 | [task14_isoefficiency.md](theory/task14_isoefficiency.md) | Isoefficiency `Θ(P)` proof and critique |
| 15 | [task15_energy_scaling.md](theory/task15_energy_scaling.md) | Energy model for 1 vs. P cores |

### Part II and Part IV: Calculations (`calculations/`)

| Task | Artifact | Result |
|---|---|---|
| 06 | [task06_parametric_table.md](calculations/task06_parametric_table.md) | S and E for P = 16 … 16,384 at α = 0.04 |
| 07 | [task07_tolerable_serial.md](calculations/task07_tolerable_serial.md) | `α_max = 692/8191 = 0.08448` |
| 08 | [task08_cross_divergence.md](calculations/task08_cross_divergence.md) | 11.47 vs. 117.84, +927.4% |
| 09 | [task09_multicomponent.md](calculations/task09_multicomponent.md) | α = 0.08: S = 471.12 (512), 1884.24 (2048) |
| 10 | [task10_memory_growth.md](calculations/task10_memory_growth.md) | N_max = 6,501 (64 nodes), 13,003 (512 nodes) at 8 B/cell |
| 16 | [task16_gemm_scaling.md](calculations/task16_gemm_scaling.md) | `N ∝ P^{1/3}`, scaling targets table |
| 17 | [task17_stencil_scaling.md](calculations/task17_stencil_scaling.md) | Surface-to-volume `6/n` constant under weak scaling |

### Part IV: Analysis (`analysis/`)

| Task | Artifact | Topic |
|---|---|---|
| 18 | [task18_nbody_scaling.md](analysis/task18_nbody_scaling.md) | Direct O(N²) vs. Barnes–Hut O(N log N) |
| 19 | [task19_monte_carlo.md](analysis/task19_monte_carlo.md) | PRNG seeding, tree vs. linear reductions |
| 20 | [task20_graph_processing.md](analysis/task20_graph_processing.md) | BFS/PageRank on power-law graphs |
| 24 | [task24_hardware_audit.md](analysis/task24_hardware_audit.md) | Hardware audit; thermal and NUMA discussion |

### Part V: Benchmarks, data and plots

| Task | Artifact | Description |
|---|---|---|
| 21 | [benchmarks/simulator.py](benchmarks/simulator.py) | Amdahl/Gustafson simulator (1 ≤ P ≤ 65,536, 0.001 ≤ α ≤ 0.20) |
| 21 | [benchmarks/simulator_results.csv](benchmarks/simulator_results.csv), [plots/simulator_overlay.png](plots/simulator_overlay.png) | CSV export and overlay plots |
| 22 | [benchmarks/weak_scale_bench/](benchmarks/weak_scale_bench/) | OpenMP (C) + multiprocessing (Python) weak-scaling suite, Makefile, README |
| 23 | [benchmarks/results.csv](benchmarks/results.csv) | Raw data: 6 thread counts × 5 runs |
| 23 | [benchmarks/fit_gustafson.py](benchmarks/fit_gustafson.py) | Mean/std, least-squares α, Karp-Flatt |
| 23 | [benchmarks/results_summary.csv](benchmarks/results_summary.csv), [benchmarks/fit_results.json](benchmarks/fit_results.json) | Statistics and fitted α |
| 24 | [plots/scaling_comparison.png](plots/scaling_comparison.png) / [.pdf](plots/scaling_comparison.pdf) | Ideal, fitted Gustafson, measured ± SE, Amdahl |
| 25 | README.md | This guide |

## 6. Repository layout

```
gustafson-law-practice/
├── README.md
├── theory/          Tasks 01–05, 11–15  (derivations and proofs)
├── calculations/    Tasks 06–10, 16–17  (worked numeric solutions)
├── analysis/        Tasks 18–20, 24     (comparative reflections)
├── benchmarks/      Tasks 21–23         (simulator, benchmark suite, data, fitting)
│   └── weak_scale_bench/
└── plots/           Tasks 21, 24        (PNG + vector PDF)
```
