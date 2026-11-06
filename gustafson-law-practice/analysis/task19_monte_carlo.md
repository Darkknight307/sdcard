# Task 19: Monte Carlo Path Simulation, the Ideal Weak-Scaling Model

## 1. Why Monte Carlo is the textbook Gustafson workload

Each rank simulates `M` independent paths (option prices, photon transport,
neutron histories, Bayesian samples). Weak scaling keeps `M` per rank constant,
so `P` ranks produce `P·M` samples in the same wall-clock time. That cuts the
statistical error by `√P`. Paths share no data, so the parallel part needs **no
communication at all**. Every non-zero α comes from the "glue" around it.

## 2. Sources of non-zero serial fraction α

| Source | Where it occurs | Cost model | Scales with P? |
|---|---|---|---|
| **PRNG seed management** | Generating independent streams per rank | Root generates and scatters `P` seeds: `t_s·P`. Counter-based or skip-ahead: `O(1)` per rank, done locally | **Yes**, if centralised; no if decentralised |
| **Initial set-up / broadcast** | Model parameters, payoff tables, geometry | `t_b·log₂P` (tree broadcast) | Weakly |
| **Reduction of estimators** | Sum of results, sum of squares (for variance), histograms | Tree: `t_r·⌈log₂P⌉`. Linear (root gathers): `t_r·(P−1)` | Log or linear |
| **Output serialisation** | Writing results, checkpoints, sample dumps | Single writer: `t_o` (constant) or `t_o·P` if per-rank data is funnelled through the root | Constant to linear |
| **Load imbalance** | Variable path lengths (absorption, early exercise) | `max_i T_i − mean T_i`, grows like `σ√(2 ln P)` for random path times | Slowly (`√log P`) |
| **Process start-up** | MPI_Init, job launch | `O(log P)` with tree launchers | Weakly |

### PRNG stream independence

Naive seeding (`seed = rank`) with an LCG gives correlated streams. Proper
designs use:

* **Skip-ahead / leapfrog** (e.g. MRG32k3a, PCG `advance`): each rank jumps to an
  offset `rank·2^k` in `O(log n)` time locally. α contribution is about 0.
* **Counter-based generators** (Philox, Threefry; Random123): `x = f(key, counter)`
  with `key = (job, rank)`. These need no state exchange. α contribution is 0.
* **Centralised seeding** (root draws P seeds and scatters them): an `O(P)` serial
  cost to avoid at scale.

## 3. Quantifying how reduction trees affect S(P)

Parallel time on P ranks for one batch:

```
T(P) = T_c + t_seed(P) + t_red(P) + t_out
```

The scaled speedup relative to pure computation per rank is
`S(P) = P·T_c / T(P)`.

Reduction strategies:

* **Binary tree / recursive doubling (MPI_Reduce):** `t_red = t_r·⌈log₂P⌉`.
* **Linear (root receives P − 1 messages):** `t_red = t_r·(P − 1)`.

Representative values: `T_c = 10 s`, `t_r = 20 µs` per message hop,
`t_out = 50 ms`, `t_seed = 1 ms` (decentralised) or `1 ms · P` (centralised):

| P | ⌈log₂P⌉ | Tree reduction S | E | Linear reduction S | E | Tree + centralised seeds S | E |
|---|---|---|---|---|---|---|---|
| 1,024 | 10 | 1,018.8 | 0.9949 | 1,016.7 | 0.9929 | 924.7 | 0.9030 |
| 16,384 | 14 | 16,300.4 | 0.9949 | 15,786.2 | 0.9635 | 6,198.0 | 0.3783 |
| 131,072 | 17 | 130,402.5 | 0.9949 | 103,430.9 | 0.7891 | 9,287.8 | 0.0709 |
| 1,048,576 | 20 | 1,043,213.9 | 0.9949 | 338,005.0 | 0.3223 | 9,905.1 | 0.0094 |

**Observations:**

1. **A tree reduction keeps Gustafson's law effectively exact.** With
   `t_r⌈log₂P⌉` = 0.4 ms at P ≈ 10⁶, against a 10 s compute phase, efficiency
   stays at 0.9949. The residual α is about 0.005, set by the constant output
   cost `t_out`.
2. **A linear reduction turns weak scaling into Amdahl-like saturation.** The
   overhead `t_r(P − 1)` grows linearly. Speedup tends to `T_c/t_r = 500,000`,
   and E falls to 0.32 at P ≈ 10⁶.
3. **Centralised seeding is even worse.** A 1 ms per-rank serial cost caps speedup
   near `T_c/t_s = 10,000`, whatever P is.
4. **Effective serial fraction with a tree:**
   `α_eff(P) = (t_seed + t_r log₂P + t_out)/T(P)`. It grows only logarithmically,
   matching the `C(P) = c·log₂P` model of Task 12.

## 4. Analytic form

With a tree reduction and decentralised seeds:

```
S(P) = P·T_c / (T_c + a + b·log₂P)     a = t_seed + t_out,  b = t_r
E(P) = 1 / (1 + (a + b log₂P)/T_c)
```

E decays like `1 − (b/T_c)log₂P`, which is extremely slow. Keeping `E ≥ 0.99`
needs `a + b log₂P ≤ 0.0101·T_c`.

## 5. Engineering recommendations

1. Use counter-based or skip-ahead PRNGs. Never seed from the root.
2. Reduce with `MPI_Reduce` or `MPI_Allreduce` (tree), not a manual gather. For
   variance use Welford or pairwise combining to stay numerically stable.
3. Write output in parallel (MPI-IO, HDF5 collective), or reduce first and write
   once.
4. Increase `T_c` (more paths per batch) to amortise every fixed cost. This is
   the Gustafson lever.
5. Balance variable-length paths dynamically, for example with work stealing
   across batches.
