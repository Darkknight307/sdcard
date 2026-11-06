# Task 10: Memory Growth Rate vs. Scaled Speedup

## 1. Model

* Pure weak scaling: `W(P) = P · W(1)` and `M(P) = c · P`. Memory per node
  stays constant at `c`.
* Hard cap: `c ≤ M_node = 32 GB = 32 × 2³⁰ B = 34,359,738,368 B` (binary GiB,
  which is how DRAM is sold).
* 3D grid with `N × N × N` cells, each holding `b` bytes of state:
  `M_total(N) = b · N³`.

The memory ceiling across `P` nodes is:

```
b · N³ ≤ P · M_node
N_max(P) = floor( (P · M_node / b)^(1/3) )
```

Since `N_max ∝ P^{1/3}`, doubling the linear resolution needs 8× more nodes.

## 2. Choice of bytes per cell

`b` depends on the solver. Three representative cases:

| Case | Content per cell | b |
|---|---|---|
| (i) Minimal | One float64 scalar field | 8 B |
| (ii) Typical CFD | 5 conserved float64 variables (ρ, ρu, ρv, ρw, E) | 40 B |
| (iii) Realistic solver | 5 variables, double-buffered (old + new) | 80 B |

## 3. Results

### 64 nodes: total memory = 64 × 32 GB = 2,048 GB = 2.199 × 10¹² B

| b | Max cells `P·M/b` | N_max | Grid |
|---|---|---|---|
| 8 B | 2.749 × 10¹¹ | **6,501** | 6,501³ |
| 40 B | 5.498 × 10¹⁰ | **3,802** | 3,802³ |
| 80 B | 2.749 × 10¹⁰ | **3,017** | 3,017³ |

Worked example for (i):

```
N³ ≤ 64 × 34,359,738,368 / 8 = 274,877,906,944
N  ≤ 274,877,906,944^(1/3) = 6,501.99  →  N_max = 6,501
```

### 512 nodes: total memory = 16,384 GB = 1.759 × 10¹³ B

| b | Max cells | N_max | Grid |
|---|---|---|---|
| 8 B | 2.199 × 10¹² | **13,003** | 13,003³ |
| 40 B | 4.398 × 10¹¹ | **7,604** | 7,604³ |
| 80 B | 2.199 × 10¹¹ | **6,035** | 6,035³ |

Check: going from 64 to 512 nodes is ×8, so `N_max` doubles (6,501 → 13,003),
exactly `8^{1/3} = 2` ✔.

## 4. Per-node view

The per-node subdomain is the same at any scale. For case (i), it is a cube of
side `(32 GiB/8 B)^{1/3} = 1,625` cells per node. The global N simply tiles these
cubes: `64 = 4³` nodes give 4 × 1,625 = 6,500; `512 = 8³` nodes give
8 × 1,625 = 13,000.

## 5. Interaction with scaled speedup

* **Memory scales linearly but resolution only as P^{1/3}.** Weak scaling a 3D
  code buys 2× resolution per 8× hardware.
* **Time steps:** explicit solvers have a CFL limit `Δt ∝ 1/N`. Doubling N
  doubles the number of steps, so *time-to-solution* grows like `P^{1/3}` even
  though time per step is constant. The fixed-time premise holds per step, not
  per simulation (see Task 13).
* **Practical ceiling:** not all 32 GB is usable. With the OS, MPI buffers,
  halos and about 10–20% reserved, the usable `M_node` is about 26–28 GB, which
  lowers `N_max` by about 5%.
