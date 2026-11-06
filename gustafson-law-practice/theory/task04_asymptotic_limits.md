# Task 04: Asymptotic Analysis of Parallel Efficiency

## 1. Gustafson efficiency

```
S_G(P) = P - α(P - 1)
E_G(P) = S_G(P)/P = 1 - α(P - 1)/P = (1 - α) + α/P
```

### Limit

```
lim_{P→∞} E_G(P) = lim [(1 - α) + α/P] = 1 - α
```

**Proof (ε-N):** let `ε > 0`. Then
`|E_G(P) - (1 - α)| = α/P < ε` whenever `P > α/ε`. Hence `E_G(P) → 1 - α`. ∎

### Properties

* `E_G` is monotonically decreasing: `dE_G/dP = -α/P² < 0`.
* It is bounded below by `1 - α`, so efficiency never falls below the parallel
  fraction.
* The total loss over the whole range `P = 1 … ∞` is exactly `α`.
* `S_G(P) ~ (1 - α)P`: the speedup grows linearly, with asymptotic slope `1 - α`.

## 2. Amdahl efficiency

```
S_A(P) = 1 / (s + (1 - s)/P) = P / (sP + 1 - s)
E_A(P) = S_A(P)/P = 1 / (sP + 1 - s)
```

### Limit

```
lim_{P→∞} E_A(P) = lim 1/(sP + 1 - s) = 0        (for s > 0)
```

**Proof:** for `s > 0` the denominator `sP + 1 - s → ∞`, so `E_A → 0`.
Asymptotically `E_A(P) ~ 1/(sP)`, so efficiency decays like `1/P`, and
`S_A(P) → 1/s`. ∎

### Properties

* `S_A` saturates at `1/s`. Every extra processor beyond about `1/s` adds almost
  nothing, so efficiency collapses.
* The "half-efficiency" point, where `E_A = 1/2`, is `P_{1/2} = 1 + 1/s`.

## 3. Side-by-side

| Quantity | Gustafson | Amdahl |
|---|---|---|
| `S(P)` as `P → ∞` | `→ ∞`, `~ (1 - α)P` | `→ 1/s` |
| `E(P)` as `P → ∞` | `→ 1 - α` | `→ 0`, `~ 1/(sP)` |
| Rate of approach | `O(1/P)` towards `1 - α` | `O(1/P)` towards 0 |
| `E = 1/2` reached at | Never (for `α < 1/2`) | `P = 1 + 1/s` |

### Numerical check (α = s = 0.04)

| P | E_G | E_A |
|---|---|---|
| 16 | 0.9625 | 0.6250 |
| 256 | 0.9602 | 0.0893 |
| 16384 | 0.9600 | 0.0015 |
| ∞ | 0.9600 | 0 |

## 4. Explanatory deductions

1. Under weak scaling the serial work is a constant **absolute** amount spread
   over a constant time. Its share of the total does not grow, so efficiency
   converges to a positive constant.
2. Under strong scaling the parallel work per processor shrinks as `1/P`, while
   the serial time stays put. The serial part therefore comes to dominate the
   run time, and efficiency must go to zero.
3. Gustafson's limit `1 - α` is an **upper bound** in practice. Real
   communication overhead grows with `P` (Task 12), which makes efficiency
   eventually decay below `1 - α` as well.
4. Design rule: if the application can scale its problem, the only budget that
   matters is the parallel-frame serial fraction `α`. To keep efficiency above
   90% at any scale, you need `α ≤ 0.1`.
