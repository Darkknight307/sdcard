# Task 16: Dense Matrix Multiplication Scaling (GEMM)

**Given:** `C = A × B` with `N × N` matrices. Work `W(N) = 2N³` flops, i.e.
`Θ(N³)`. Memory `M(N) = 3N²` words, i.e. `Θ(N²)`.

## 1. Fixed-time (Gustafson) dimension growth

Let one processor handle size `N₁` in time `T`, at a per-processor rate of `r`
flops/s:

```
T = 2N₁³ / r
```

On P processors, with ideal parallel work and the serial part ignored, the
fixed-time condition is

```
T = 2N_P³ / (P·r)
```

Equating the two:

```
2N_P³ / (P r) = 2N₁³ / r   ⇒   N_P³ = P N₁³   ⇒   N_P = N₁ · P^{1/3}
```

**Proof that this is necessary and sufficient:** run time is
`T(N, P) = 2N³/(Pr)`, which is strictly increasing in N for fixed P. So
`T(N, P) = T` has the unique solution `N = (P r T/2)^{1/3} = N₁P^{1/3}`. ∎

With a serial fraction α (Gustafson), `N_P³ = N₁³ (α + (1 − α)P)`, so
`N_P = N₁(α + (1 − α)P)^{1/3}`, which is still `Θ(P^{1/3})`.

## 2. Consequences for memory

```
M(N_P) = 3N_P² = 3N₁² · P^{2/3}
memory per processor = M(N_P)/P = 3N₁² · P^{−1/3}
```

Under fixed-time scaling, **total memory grows only as P^{2/3}** and per-processor
memory **falls** as `P^{−1/3}`. Memory-bounded scaling (Sun–Ni) would instead use
all memory, `N ∝ P^{1/2}`. That gives work `∝ P^{3/2}` and run time `∝ P^{1/2}`,
which violates fixed time (Task 13).

## 3. Scaling targets

Baseline: `N₁ = 4096` in float64 on one processor. Memory for A, B and C is
`3 × 8 × 4096² B = 384 MiB`.

| P | Growth factor P^{1/3} | N_P | Work relative to P=1 (= P) | Total memory (MiB) | Memory per processor (MiB) |
|---|---|---|---|---|---|
| 1 | 1 | 4,096 | 1 | 384 | 384 |
| 8 | 2 | 8,192 | 8 | 1,536 | 192 |
| 64 | 4 | 16,384 | 64 | 6,144 | 96 |
| 512 | 8 | 32,768 | 512 | 24,576 | 48 |
| 4,096 | 16 | 65,536 | 4,096 | 98,304 | 24 |

## 4. Communication-to-computation ratio

For a 2D block distribution (Cannon / SUMMA) on a `√P × √P` grid:

* Each processor owns `(N/√P)²` elements of each matrix.
* Computation per processor: `2N³/P`. Constant under fixed-time scaling.
* Communication per processor: `Θ(N²/√P)` words. With `N = N₁P^{1/3}` this is
  `N₁² P^{2/3}/P^{1/2} = N₁² P^{1/6}`, which **grows slowly**.
* Ratio of communication to computation: `Θ(P^{1/6}/N₁)`. It degrades mildly with
  P. This is why GEMM weak-scales very well in practice, though not perfectly.

## 5. Summary

| Quantity | Growth under fixed-time scaling |
|---|---|
| Matrix dimension N | `P^{1/3}` |
| Work | `P` |
| Total memory | `P^{2/3}` |
| Memory per processor | `P^{−1/3}` |
| Communication volume per processor (2D) | `P^{1/6}` |
