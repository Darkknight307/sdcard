# Task 12: Communication Overhead Penalty Integration

## 1. Motivation

Classic Gustafson assumes the parallel run time is `s + p = 1` for every P. In a
distributed system each step also pays for communication whose cost depends on P:

* Tree-based collectives (broadcast, allreduce, barrier): `O(log P)` latency
  terms.
* Communication on a 2D process grid (row/column broadcasts in SUMMA, 2D domain
  transposes) or nearest-neighbour exchange on a mesh network whose diameter
  grows: `O(√P)`.
* All-to-all (FFT transposes, sample sort): `O(P)` in the latency term.

## 2. Proposed model

Let the parallel run time on P processors be:

```
T_par(P) = s + p + C(P),       with  s + p = 1,  C(1) = 0
```

`C(P)` is communication time that **cannot be overlapped** with computation. The
useful work done is still `s + p·P`, so the uniprocessor equivalent time is
`T_1 = s + p·P`, since one processor needs no communication.

**Modified scaled speedup:**

```
S_C(P) = (s + p·P) / (1 + C(P)) = (α + (1 − α)P) / (1 + C(P))
```

**Modified efficiency:**

```
E_C(P) = [α + (1 − α)P] / [P (1 + C(P))]  →  (1 − α) / (1 + C(P))   as P → ∞
```

**Effective serial fraction (what a profiler or the Karp-Flatt metric would
report):**

```
α_eff(P) = (α + C(P)) / (1 + C(P))
```

This grows with P, which matches the empirical signature of communication
overhead: a Karp-Flatt metric that increases with P.

## 3. Common forms of C(P)

| Communication pattern | C(P) | Asymptotic S_C(P) | Asymptotic E_C(P) |
|---|---|---|---|
| None (classic Gustafson) | 0 | `(1 − α)P` | `1 − α` |
| Tree collectives | `c·log₂ P` | `(1 − α)P / (c log₂ P)` | `→ 0` like `1/log P` |
| 2D mesh / grid broadcasts | `c·√P` | `(1 − α)√P / c` | `→ 0` like `1/√P` |
| All-to-all | `c·(P − 1)` | `→ (1 − α)/c` (bounded) | `→ 0` like `1/P` |

**Consequences:**

* With `log P` overhead, speedup still grows without bound, but sublinearly.
* With `√P` overhead, speedup grows only as `√P`.
* With all-to-all (linear) overhead, scaled speedup **saturates** at `(1 − α)/c`.
  Weak scaling then behaves like Amdahl's law.

## 4. Derivation of the saturation and optimal-P results

For `C(P) = cP` (all-to-all):

```
S_C(P) = (α + (1 − α)P) / (1 + cP)

dS_C/dP = [(1 − α)(1 + cP) − c(α + (1 − α)P)] / (1 + cP)²
        = [(1 − α) − cα] / (1 + cP)²
```

So `S_C` increases monotonically iff `c < (1 − α)/α`. Its limit is
`lim S_C = (1 − α)/c`.

For `C(P) = c√P`, the efficiency hits a target `E*` when

```
(1 − α)/(1 + c√P) ≈ E*  ⇒  P_max ≈ ((1 − α − E*)/(c E*))²
```

## 5. Numerical example

Take `α = 0.04` and `c = 0.005` (each doubling of P adds 0.5% of the step time
to communication in the log model):

| P | S, C = 0.005 log₂P | E | S, C = 0.005 √P | E |
|---|---|---|---|---|
| 16 | 15.1 | 0.944 | 15.1 | 0.944 |
| 256 | 236.3 | 0.923 | 227.6 | 0.889 |
| 1,024 | 936.3 | 0.914 | 847.5 | 0.828 |
| 4,096 | 3,709.6 | 0.906 | 2,978.9 | 0.727 |
| 16,384 | 14,699.7 | 0.897 | 9,590.7 | 0.585 |
| 65,536 | 58,254.3 | 0.889 | 27,594.1 | 0.421 |

Classic Gustafson would predict `E = 0.96` for all of these.

## 6. Overlap extension

If a fraction `φ` of communication can be hidden behind computation, replace
`C(P)` by `(1 − φ)·max(0, C(P) − overlap capacity)`. To first order this is
`C_eff(P) = (1 − φ)C(P)`. For example, non-blocking halo exchange overlapped
with interior updates gives `φ → 1` for nearest-neighbour patterns. Collectives
on the critical path keep `φ ≈ 0`.

## 7. Calibration procedure

1. Measure `T_par(P)` for several P with the per-node work fixed.
2. Compute `C(P) = T_par(P)/T_par(1) − 1`.
3. Fit `C(P)` against `log₂ P`, `√P` and `P` by least squares, and choose the
   model with the lowest residual.
4. Use the fitted model to predict the largest P that still meets an
   efficiency target.
