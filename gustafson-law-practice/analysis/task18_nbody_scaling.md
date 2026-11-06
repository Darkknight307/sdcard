# Task 18: N-Body Gravitational Problem Scaling

We compare the **direct all-pairs** method (`O(N²)` per step) with the
**Barnes–Hut** tree code (`O(N log N)` per step). The particle count N is scaled
with P so that the **time per iteration stays constant**.

## 1. How N must scale for constant time per iteration

Let one processor handle `N₁` particles in time `T`.

### Direct all-pairs

```
W(N) = c N²,    T = c N_P²/P = c N₁²   ⇒   N_P = N₁ · √P
```

### Barnes–Hut

```
W(N) = c N log N,    N_P log N_P = P · N₁ log N₁
⇒   N_P ≈ P N₁ · log N₁ / log(P N₁) = P N₁ / (1 + log P / log N₁)
```

Up to logarithmic factors, Barnes–Hut lets N grow almost linearly with P, while
the direct method grows only as `√P`.

| P | Direct N_P (N₁ = 10⁴) | Barnes–Hut N_P (N₁ = 10⁴), solved numerically |
|---|---|---|
| 1 | 1.0 × 10⁴ | 1.0 × 10⁴ |
| 64 | 8.0 × 10⁴ | ≈ 4.5 × 10⁵ |
| 1,024 | 3.2 × 10⁵ | ≈ 6.0 × 10⁶ |
| 16,384 | 1.28 × 10⁶ | ≈ 8.3 × 10⁷ |

## 2. Serial and parallel components per iteration

| Component | Direct | Barnes–Hut |
|---|---|---|
| Force computation (parallel) | `N²/P` | `(N log N)/P` |
| Particle position update (parallel) | `N/P` | `N/P` |
| Gathering or broadcasting all positions | `O(N)` data per rank (allgather) | Only locally essential tree: `O((N/P)^{2/3}·log P)` |
| Tree construction (top levels) | n/a | Top `log P` levels are global: `O(P log P)` or `O(log P)` with a global sync |
| Global reductions (energy, timestep) | `O(log P)` | `O(log P)` |
| Load balancing (cost zones / ORB) | Trivial (uniform) | `O(N/P + P)` per rebalance, data dependent |

## 3. How the serial/parallel ratio shifts

Define the serial (non-scalable) to parallel ratio as
`ρ(P) = T_nonscalable / T_parallel`.

### Direct method

The allgather of positions is the main non-scalable term. Each rank must receive
all N positions:

```
T_comm ∝ N = N₁√P,   T_par ∝ N²/P = N₁²  (constant)
ρ_direct(P) ∝ N₁√P / N₁² = √P / N₁
```

**The ratio grows as √P.** The direct method has a huge arithmetic intensity, so
`ρ` starts tiny (for example `1/N₁ = 10⁻⁴`). Even at P = 16,384 it is only
`128 × 10⁻⁴ ≈ 1.3%` of a step. Weak scaling is excellent in practice, even
though the time-per-iteration premise forces N to grow only as √P.

### Barnes–Hut

The parallel part is constant by construction, while the global tree levels and
load imbalance grow:

```
ρ_BH(P) ∝ (P log P + (N/P)^{2/3} log P) / (N₁ log N₁)
```

The `P log P` top-tree term eventually dominates. **The ratio grows roughly
linearly** in P for large P, faster than in the direct method. Barnes–Hut also
has irregular data-dependent costs: clustered particles cause load imbalance
that a static Gustafson α cannot capture.

## 4. Implications

1. **Algorithmic efficiency vs. parallel efficiency trade-off.** Barnes–Hut does
   far less total work: `N log N ≪ N²`. It simulates orders of magnitude more
   particles in the same time (8.3 × 10⁷ against 1.3 × 10⁶ at P = 16,384). However,
   its serial fraction grows faster, so its scaled speedup curve bends earlier.
2. **The direct method is a near-ideal Gustafson workload** in terms of serial
   fraction. Its problem size grows only as √P, so the *science per processor*
   grows slowly.
3. **Practical codes** (e.g. GADGET, PKDGRAV, Bonsai) use hybrid tree or
   fast-multipole methods with space-filling-curve domain decomposition. They keep
   `ρ` small by caching remote tree nodes and by overlapping the top-tree
   exchange with local force work.

## 5. Summary table

| Property | Direct O(N²) | Barnes–Hut O(N log N) |
|---|---|---|
| N growth for constant time | `√P` | `≈ P / log P` |
| Non-scalable term | Allgather `O(N)` | Global tree + imbalance `O(P log P)` |
| Serial/parallel ratio ρ(P) | `∝ √P / N₁` (small, slow) | `∝ P log P / (N₁ log N₁)` (faster growth) |
| Gustafson fit | Excellent | Good up to moderate P, then degrades |
