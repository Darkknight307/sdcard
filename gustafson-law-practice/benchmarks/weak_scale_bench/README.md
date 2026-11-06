# weak_scale_bench: Empirical Weak-Scaling Benchmark Suite (Task 22)

A synthetic numerical workload, run under a **weak-scaling harness**: the problem
size per thread `K` stays constant while the thread count `P` varies from 1 up to
(and beyond) the host's hardware concurrency.

**Workload:** midpoint-rule integration of `f(x) = 4/(1 + x²)` on `[0, 1]`, whose
exact value is π. With P threads the interval is split into `P·K` points and
thread `i` integrates points `[iK, (i+1)K)`. The total problem `N(P) = P·K` grows
linearly with P, as Gustafson's law requires, and the answer gets more accurate.
Each run checks its own correctness by printing `|π_est − π|`.

There are two equivalent implementations:

| File | Model | Notes |
|---|---|---|
| `weak_scale_bench.c` | **OpenMP threads** (primary) | Scalar compute-bound loop, `omp parallel reduction(+)`, timed with `omp_get_wtime()` |
| `weak_scale_bench.py` | Python `multiprocessing` | NumPy blocks of 2M points per worker, persistent `Pool` (start-up not timed) |

## Build and run: C / OpenMP

### Linux (GCC)

```bash
cd benchmarks/weak_scale_bench
make                                   # gcc -O2 -fopenmp -o weak_scale_bench weak_scale_bench.c -lm
./weak_scale_bench 500000000 5 1 2 3 4 6 8 > ../results.csv
# or: make run K=500000000 RUNS=5 THREADS="1 2 3 4 6 8"
```

### macOS (Apple clang + Homebrew libomp)

```bash
brew install libomp
clang -O2 -Xpreprocessor -fopenmp -I"$(brew --prefix libomp)/include" \
      -L"$(brew --prefix libomp)/lib" -lomp -o weak_scale_bench weak_scale_bench.c
./weak_scale_bench 500000000 5 1 2 3 4 5 6 7 8 > ../results.csv
```

### Arguments

`./weak_scale_bench [K_per_thread] [runs] [thread counts...]`

* Defaults: `K = 2×10⁸`, `runs = 5`, threads `1 … omp_get_num_procs()`.
* Progress goes to stderr and the CSV to stdout.

## Run: Python multiprocessing

```bash
pip install numpy
python weak_scale_bench.py --k 40000000 --runs 5 --threads 1 2 3 4 6 8 --out ../results.csv
```

## Output schema (`benchmarks/results.csv`)

`P, run, time_s, points_per_thread, total_points, pi_estimate, abs_error`.
One row per run, with 5 runs per thread count.

## Analyse

```bash
cd benchmarks
python fit_gustafson.py --hw $(nproc)      # macOS: --hw $(sysctl -n hw.logicalcpu)
```

This produces `results_summary.csv` (mean, std, SE, S, E and Karp-Flatt per P),
`fit_results.json` (α_observed) and `plots/scaling_comparison.png/.pdf`.

## Methodology notes

* One untimed warm-up run is done first to page in memory and let clocks ramp up.
* `K = 5×10⁸` gives about 0.5 s per run, which is long enough to amortise thread
  wake-up (~µs) and short enough to avoid long thermal drift.
* Thread counts beyond the hardware concurrency are **oversubscribed**. They are
  recorded so the knee is visible, but they are excluded from the α fit.
* Pin threads for reproducible numbers: `OMP_PROC_BIND=close OMP_PLACES=cores`.
