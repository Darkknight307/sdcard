# Task 13: Boundary Cases — When Gustafson Fails

Gustafson's premise is that if per-processor work stays constant, parallel run
time stays constant. This breaks whenever **scaling the problem changes the
algorithm's cost per processor**, or when it **adds contention that grows with
P**. Two concrete failure cases are analysed below, followed by two shorter
ones.

---

## Case 1: Iterative linear solvers (Jacobi / Conjugate Gradient for the Poisson equation)

### Set-up

Solve `−∇²u = f` on a 3D grid with `N³` unknowns using a 7-point stencil. The
grid is weak-scaled so that each processor owns `n³` points: `N = n·P^{1/3}`.

### Why constant runtime breaks

* **The work per iteration is constant per processor.** This part honours
  Gustafson.
* **The number of iterations grows with N.** The condition number of the
  discrete Laplacian is `κ ∝ N² = n²P^{2/3}`.
  * Jacobi needs `O(κ) = O(N²)` iterations, which is `O(P^{2/3})`.
  * Unpreconditioned CG needs `O(√κ) = O(N)` iterations, which is `O(P^{1/3})`.
* **Every CG iteration has two global dot products** (allreduce), costing
  `O(log P)` latency each.

Time to solution on P processors therefore grows as:

```
T_CG(P) ∝ iterations × (local work + allreduce)
        ∝ P^{1/3} · (n³ + c log P)
```

At `P = 4096` (`P^{1/3} = 16`), the solver needs about 16× more iterations than
on one processor. Wall-clock time grows about 16× even though the per-processor
problem never changed. Scaled speedup measured by time-to-solution is
`S ≈ P / P^{1/3} = P^{2/3}`, not `≈ P`.

### Mitigation

Use optimal-complexity methods such as multigrid, whose iteration count is
`O(1)` in N. Even then, the coarse levels of multigrid have too little work per
processor. They are effectively serial and add an `O(log P)` term.

---

## Case 2: Global synchronisation and contention (shared counters, locks, all-to-all)

### Example A: Parallel hash-join or histogram with a shared, globally contended structure

Each processor contributes items at a fixed rate. Updates to the shared counter,
hash bucket or lock are serialised. Under weak scaling the number of updates
grows like `P`, while the contended resource has a fixed throughput `μ`.

```
T(P) ≥ (total updates)/μ = P·k/μ      → grows linearly with P
```

The contended section is a serial fraction that grows with the problem. In
Gustafson's frame, `α(P)` rises towards 1, and scaled speedup saturates at
`μ/(k·rate)`.

### Example B: Distributed 3D FFT (pencil/slab decomposition)

The FFT needs global transposes (all-to-all). Under weak scaling with `n³`
points per rank:

* Computation per rank: `O(n³ log N)`. This grows slowly through `log N`.
* All-to-all communication: each rank sends `n³` data split into `P − 1` messages
  (slab) or `√P` messages (pencil). The latency term is `O(P)` or `O(√P)`, and
  bisection bandwidth on a fat tree or torus usually grows more slowly than P.

The `log N` factor *and* the all-to-all latency both grow with P, so the time per
FFT increases. This is why spectral codes typically lose weak-scaling efficiency
well before stencil codes do.

---

## Shorter cases

* **Dense LU / GEMM under memory-constrained scaling.** If N is grown to fill
  memory (`N ∝ √P`, Sun–Ni), work grows as `N³ ∝ P^{3/2}`, so per-processor time
  grows as `√P`. Constant time requires `N ∝ P^{1/3}` instead (Task 16).
* **Explicit time-stepping to a fixed physical end time.** The CFL condition makes
  `Δt ∝ 1/N`, so the number of steps grows as `P^{1/3}` in 3D. Time per step is
  constant (Gustafson holds per step), but time to solution is not.

## Summary

| Failure mechanism | Example | How T(P) grows under weak scaling |
|---|---|---|
| Iterations grow with problem size | CG, Jacobi, explicit CFL | `P^{1/3}` – `P^{2/3}` |
| Global collectives on the critical path | CG dot products, multigrid coarse grids | `log P` |
| All-to-all communication | FFT, sample sort | `√P` – `P` |
| Serialised shared resource | Locks, global counters, metadata servers | `P` |
| Superlinear work per memory | GEMM/LU filling memory | `√P` |

Gustafson's law assumes the per-processor cost is invariant under scaling. Each of
these algorithms violates that through its complexity or its synchronisation
structure, so the "fixed time" premise is lost.
