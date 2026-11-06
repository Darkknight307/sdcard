# Task 17: 3D Stencil Hydrodynamics Simulation

**Given:** 7-point stencil on an `N × N × N` domain. Interior updates cost
`Θ(N³)` operations and boundary (halo) exchange costs `Θ(N²)` data.

## 1. Per-processor model (3D block decomposition)

Split the domain into `P = q³` cubic subdomains of side `n = N/q = N/P^{1/3}`.

* **Computation per processor per step:** `T_comp = c_f · n³`, with about 8 flops
  per point for a 7-point stencil.
* **Communication per processor per step:** 6 faces of `n²` points:
  `T_comm = 6(t_lat + t_w · n²)`, with latency `t_lat` and per-word time `t_w`.
* **Communication-to-computation ratio** (bandwidth term):

  ```
  R = 6n² / n³ = 6/n
  ```

## 2. Weak scaling (Gustafson): domain volume grows with P

Hold `n` fixed and let `N = n·P^{1/3}`, so the domain volume is `N³ = P n³`.

```
R_weak(P) = 6/n = constant
```

**Proof:** R depends only on the subdomain side n, which is fixed by
construction. Surface `6n²` and volume `n³` per processor are both independent
of P. ∎

There are also 6 messages per step per processor, so the latency term is also
constant on a network with constant-degree nearest-neighbour links. The time per
step `T_comp + T_comm` is therefore **independent of P**, which is exactly
Gustafson's fixed-time premise. In Gustafson's terms, the halo exchange is a
constant α.

**Globally:** total communication `6n²·P` and total computation `n³P` both grow
linearly. The global ratio `6n²P/(n³P) = 6/n` is also constant.

## 3. Strong scaling (Amdahl) for contrast: fixed N

```
n(P) = N/P^{1/3},     R_strong(P) = 6P^{1/3}/N
```

This **degrades** as `P^{1/3}`, because subdomains shrink and surface-to-volume
ratios grow.

Numerical comparison with `N = 512` (strong) and `n = 128` (weak):

| P | Strong: n | Strong: R = 6/n | Weak: n | Weak: R = 6/n |
|---|---|---|---|---|
| 1 | 512 | 0.0117 | 128 | 0.0469 |
| 8 | 256 | 0.0234 | 128 | 0.0469 |
| 64 | 128 | 0.0469 | 128 | 0.0469 |
| 512 | 64 | 0.0938 | 128 | 0.0469 |
| 4,096 | 32 | 0.1875 | 128 | 0.0469 |

## 4. Effect of the subdomain size chosen

| n (per processor) | R = 6/n | Halo per step (6n² × 8 B) |
|---|---|---|
| 64 | 0.0938 | 192 KiB |
| 128 | 0.0469 | 768 KiB |
| 256 | 0.0234 | 3,072 KiB |

Larger per-processor subdomains give a better (lower) ratio. Weak scaling lets the
user choose n once, as large as memory allows, and keep that ratio at any P.

## 5. Decomposition matters

* **1D slabs:** keep the volume per processor fixed at `n³`. The global
  cross-section is then `N² = n²P^{2/3}`, and each processor exchanges 2 faces of
  that size, so `R = 2N²/n³ ∝ P^{2/3}`. This **degrades**.
* **2D pencils:** `R ∝ P^{1/3}`, which also degrades, more slowly.
* **3D blocks:** `R` constant, which is optimal. Only the 3D block decomposition
  achieves perfect Gustafson weak scaling.

## 6. Remaining sources of degradation

1. **Global reductions** (time-step size via a CFL check, residual norms) cost
   `O(log P)` per step (Task 12).
2. **Network contention:** on a torus, nearest-neighbour traffic scales. On a
   tapered fat tree, a bad rank mapping causes contention.
3. **Time to solution:** with an explicit CFL limit, the number of steps grows as
   `N ∝ P^{1/3}` (Task 13). The per-step time is constant, but the full simulation
   time is not.

## Conclusion

Under Gustafson weak scaling with a 3D block decomposition, the
communication-to-computation ratio **stays constant** at `6/n`. It neither
improves nor degrades, because the surface-to-volume ratio of a fixed-size
subdomain is invariant. Under strong scaling it degrades as `P^{1/3}`.
