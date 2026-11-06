# Task 14: Isoefficiency Relation with Gustafson Scaling

## 1. Isoefficiency (Kumar, Grama, Gupta, Karypis)

Let `W` be the problem size measured as serial work (time on one processor), and
`T_o(W, P) = P·T_P − W` the **total overhead**: all processor-time not spent on
useful work. Efficiency is:

```
E = W / (W + T_o(W, P)) = 1 / (1 + T_o/W)
```

Holding `E` constant requires

```
W = K · T_o(W, P),         K = E/(1 − E)
```

The **isoefficiency function** is the growth rate of W, as a function of P, that
satisfies this equation. A small (e.g. linear) function means a highly scalable
system.

## 2. A Gustafson-compliant program

Gustafson's model on P processors (Task 02, parallel run time normalised to 1):

* Serial time `α` (one processor busy, `P − 1` idle).
* Parallel time `1 − α` (all P processors busy).
* Useful work `W(P) = α + (1 − α)P`.
* Total processor-time `P · T_P = P · 1 = P`.

**Total overhead:**

```
T_o(P) = P·T_P − W = P − α − (1 − α)P = α(P − 1)
```

This is exactly the idle time of the `P − 1` processors during the serial phase.
It **does not depend on W**. It depends only on P and the absolute serial time α.

## 3. Deriving the isoefficiency function

**Theorem.** For a program whose overhead is a constant absolute serial time per
processor count, `T_o(W, P) = t_s(P − 1)`, the isoefficiency function is
`W(P) = Θ(P)`.

**Proof.** Impose constant efficiency `E`:

```
W = K · T_o = K · t_s · (P − 1)
⇒ W(P) = (E/(1 − E)) · t_s · (P − 1) = Θ(P)                   ∎
```

**Consistency with Gustafson's scaling.** Gustafson grows the workload as
`W(P) = α + (1 − α)P = Θ(P)`, which is the same order as the isoefficiency
function. Substituting gives

```
E(P) = W/(W + T_o) = (α + (1 − α)P)/P = 1 − α(P − 1)/P
```

which is Gustafson's efficiency (Task 04). E is not exactly constant: it falls
from 1 towards `1 − α`. Gustafson's linear growth of W uses the constant
`K_G = (1 − α)/α`, which corresponds to the asymptotic efficiency
`E_∞ = K_G/(1 + K_G) = 1 − α`. Since `E(P) ≥ 1 − α` for all P, **any Gustafson
weak-scaling program is isoefficient at the level `1 − α`**, with isoefficiency
function

```
f_iso(P) = Θ(P)       (optimal: linear)
```

Linear isoefficiency is the best possible order. W must grow at least linearly
in P just to give every processor a non-zero share of work (the "degree of
concurrency" bound).

## 4. Critique

1. **Gustafson assumes the best case.** `T_o = α(P − 1)` assumes the only overhead
   is the serial phase. Real programs have communication overhead, and the
   isoefficiency function rises accordingly:

   | Overhead `T_o(W, P)` | Isoefficiency `W(P)` | Example |
   |---|---|---|
   | `t_s P` | `Θ(P)` | Gustafson ideal, Monte Carlo |
   | `P log P` | `Θ(P log P)` | Tree reductions, parallel prefix |
   | `P^{3/2}` | `Θ(P^{3/2})` | Cannon's GEMM, 2D FFT |
   | `P²` | `Θ(P²)` | Naive all-to-all |

   If you scale W only linearly (Gustafson) while `f_iso` is superlinear,
   efficiency decays. This is the formal version of Task 12.
2. **Isoefficiency is the more general and more honest tool.** It derives the
   required growth rate from the actual overhead, instead of assuming linear
   growth. Gustafson's law is the special case `T_o = Θ(P)`.
3. **Memory feasibility.** Isoefficiency `W(P)` must also fit the memory growth
   `M(P) = cP`. For GEMM with `f_iso = Θ(P^{3/2})` and memory `N² ∝ W^{2/3} ∝ P`,
   memory is just sufficient. Algorithms whose isoefficiency demands memory
   growth faster than `P` are not scalable on real machines.
4. **The degree of concurrency matters too.** Some programs cannot use P
   processors at all without W growing faster than isoefficiency requires.
   Gustafson's model ignores this limit.
