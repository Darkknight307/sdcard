# Task 11: Sun–Ni Memory-Bounded Speedup vs. Gustafson's Law

## 1. Three scaling questions

| Model | Constraint held fixed | Workload on P processors |
|---|---|---|
| Amdahl (1967) | Problem size | `W = s + p` (unchanged) |
| Gustafson (1988) | Execution time | `W = s + p·P` |
| Sun & Ni (1990/1993) | **Memory per processor** (use all available memory) | `W = s + p·G(P)` |

Xian-He Sun and Lionel Ni observed that what limits problem growth on a real
machine is usually **memory capacity**, not a time budget. With `P` nodes the
available memory is `P·M`. The user grows the problem until memory is full, and
the parallel workload then grows by a factor `G(P)` determined by the
**algorithm's work-to-memory relation**.

## 2. Formulation

Normalise the one-processor run to `s + p = 1`. With `P` processors and memory
scaled by `P`, the parallel workload grows by `G(P)`:

```
S_SN(P) = (s + p·G(P)) / (s + p·G(P)/P)
```

If an algorithm with work `W(N)` and memory `M(N)` has `W = g(M)`, then
`G(P) = g(P·M)/g(M)`. For a power law `g(M) ∝ M^β` this gives `G(P) = P^β`.

## 3. Sun–Ni generalises both laws

* **`G(P) = 1`** (workload does not grow):
  `S_SN = (s + p)/(s + p/P) = 1/(s + (1 − s)/P)`, which is **Amdahl**.
* **`G(P) = P`** (workload grows linearly with memory):
  `S_SN = (s + pP)/(s + p) = s + pP`, which is **Gustafson**.
* **`G(P) > P`** (workload grows faster than memory): Sun–Ni speedup is larger
  than Gustafson's, but the parallel run time grows by `s + p·G(P)/P`, so the run
  is no longer fixed-time.
* **`G(P) < P`** (workload grows more slowly than memory): Sun–Ni speedup is
  smaller than Gustafson's.

## 4. Algorithm examples

| Algorithm | W(N) | M(N) | W as a function of M | G(P) |
|---|---|---|---|---|
| Vector ops, explicit stencil, Monte Carlo | N | N | W ∝ M | P (Gustafson) |
| Dense matrix multiply (GEMM), LU | N³ | N² | W ∝ M^{3/2} | P^{3/2} |
| FFT | N log N | N | ≈ M log M | ≈ P·(1 + log P/log M) |
| Dense matrix-vector product | N² | N² | W ∝ M | P |
| Sorting of keys with large payloads, sparse lookups | ~N | ≫N | W ∝ M^{β}, β < 1 | P^β < P |

Numerical comparison with `s = 0.05`:

| P | Amdahl (G=1) | Gustafson (G=P) | Sun–Ni G = P^{1.5} (GEMM) | Sun–Ni G = P^{0.5} |
|---|---|---|---|---|
| 64 | 15.42 | 60.85 | 63.59 | 45.33 |
| 1024 | 19.64 | 972.85 | 1022.32 | 382.12 |

## 5. When Gustafson underestimates or overestimates

### Gustafson **underestimates** achievable throughput when

1. **Work grows superlinearly with memory** (`G(P) > P`), as in GEMM, LU and
   N-body all-pairs. Filling memory creates more work than the fixed-time
   assumption allows, and the serial part becomes even more diluted. For GEMM
   with P = 1024, Sun–Ni gives 1022 against Gustafson's 973.
2. **The serial fraction depends on memory, not time.** If serial work scales with
   data size more slowly than the parallel work does, the observed α shrinks with
   P instead of staying constant.

Caveat: the extra throughput costs **longer wall-clock time**, since
`T_par ∝ G(P)/P = P^{1/2}` for GEMM. If the user's real constraint is time,
Gustafson is the right model.

### Gustafson **overestimates** achievable throughput when

1. **Work grows sublinearly with memory** (`G(P) < P`). Memory runs out before
   the fixed-time workload is reached, for example with replicated
   data structures (lookup tables, a global mesh copy on every rank), large
   per-element metadata, or high-order methods with large storage per useful
   flop.
2. **Per-node memory shrinks in effect as P grows.** MPI buffers, ghost layers and
   communication tables grow with the number of neighbours or ranks and leave
   less room for scaled work.
3. **The memory hierarchy, not capacity, is the bottleneck.** If bandwidth per
   node is fixed but the algorithm's data reuse falls as the problem grows,
   per-node time rises, and the "fixed time" cannot be kept.
4. **Overheads grow with P** (communication, synchronisation; Task 12). Neither
   pure model captures this, but Gustafson's constant α hides it.

## 6. Critical assessment

* Gustafson's law is the special case `G(P) = P` of Sun–Ni. It is exact for
  "embarrassingly linear" kernels (stencils, particles with local forces, Monte
  Carlo), which is why it fits many weak-scaling benchmarks well.
* Sun–Ni is the more general **engineering** model. It ties scaling to the one
  resource that does grow with node count (memory). It also makes explicit that
  time-to-solution may grow.
* In practice one should pick the model by the real constraint: deadline
  (Gustafson), memory capacity (Sun–Ni) or fixed problem (Amdahl). The model
  should then be calibrated with a measured serial fraction (Karp-Flatt `e`) and
  a measured `G(P)` for the algorithm.
