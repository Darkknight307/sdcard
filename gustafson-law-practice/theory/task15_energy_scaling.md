# Task 15: Energy and Power Proportionality under Scaled Speedup

## 1. Power model

Each node (core) has:

* static (idle/leakage) power `P_idle`, drawn whenever the node is powered on,
  busy or not;
* dynamic power `P_active`, drawn **in addition** to `P_idle` while it computes.

A node that is busy for time `t_b` out of a wall-clock time `T` consumes

```
E_node = P_idle · T + P_active · t_b
```

## 2. Gustafson weak-scaling run on P nodes

Normalise the wall-clock time to `T` with fractions `α` (serial) and `1 − α`
(parallel):

* Serial phase `αT`: 1 node busy, `P − 1` idle.
* Parallel phase `(1 − α)T`: all `P` nodes busy.

Total busy node-time: `αT + P(1 − α)T = T(α + (1 − α)P) = T·S(P)`.

```
E_P = P · P_idle · T  +  P_active · T · (α + (1 − α)P)
    = T [ P·P_idle + P_active · S(P) ]                              (1)
```

**Work done:** `W_P = S(P)` units, where one unit is what one node does in time T.

**Energy per unit of work:**

```
e_P = E_P / W_P = T [ P·P_idle / S(P) + P_active ]
    = T [ P_idle / E(P) + P_active ]                                (2)
```

where `E(P) = S(P)/P` is the parallel efficiency.

## 3. Single node, same wall-clock time T

```
E_1 = T (P_idle + P_active),      W_1 = 1
e_1 = T (P_idle + P_active)                                         (3)
```

## 4. Comparison for identical wall-clock runtime

**Total energy ratio** (P nodes do `S(P)` times more work):

```
E_P / E_1 = [P·P_idle + S(P)·P_active] / (P_idle + P_active)
```

**Energy per unit of work ratio:**

```
e_P / e_1 = (P_idle/E(P) + P_active) / (P_idle + P_active)
          = 1 + (P_idle/(P_idle + P_active)) · (1/E(P) − 1)              (4)
```

**Key result:** since `E(P) ≤ 1`, `e_P ≥ e_1`. The weak-scaling run always costs
**at least as much energy per unit of work**. The penalty is the static power
burned by nodes waiting during the serial phase, and it is proportional to
`(1/E − 1)` times the static share of power. With `E → 1 − α` as `P → ∞`:

```
e_∞ / e_1 = 1 + (P_idle/(P_idle + P_active)) · α/(1 − α)
```

**Energy is bounded:** under Gustafson the per-work energy penalty converges to a
constant and does not grow with P.

## 5. Numerical example

Per node `P_idle = 40 W`, `P_active = 60 W`, `T = 1 h`, and `α = 0.04`:

| P | S(P) | E(P) | Total energy E_P (kWh) | Work (node-hours) | Energy/work (kWh) | e_P/e_1 |
|---|---|---|---|---|---|---|
| 1 | 1.00 | 1.000 | 0.100 | 1.00 | 0.1000 | 1.000 |
| 64 | 61.48 | 0.961 | 6.249 | 61.48 | 0.1016 | 1.016 |
| 1024 | 983.08 | 0.960 | 99.945 | 983.08 | 0.1017 | 1.017 |

Calculation for P = 64: `E_P = 1 h × (64 × 40 W + 61.48 × 60 W) = 6,249 Wh`.

The 1.6–1.7% energy-per-work penalty equals `0.4 × (1/0.96 − 1) ≈ 1.7%`, matching
equation (4).

## 6. Extensions and discussion

1. **Communication overhead (Task 12)** lowers E further, and communication
   hardware has its own power, so the energy per work grows with P. Energy-optimal
   P can then be smaller than time-optimal P.
2. **DVFS:** dynamic power scales as about `C V² f`, roughly `f³`. During the
   serial phase, idle nodes can drop into deep sleep (cutting `P_idle`), and the
   serial node can turbo. Both reduce the penalty in (4). Gustafson-style codes
   with small, predictable α are well suited to race-to-idle.
3. **Uncore and system power:** shared static power (network, storage, cooling;
   PUE) is paid per node regardless of utilisation. It effectively raises
   `P_idle`, which makes high efficiency even more important.
4. **Energy proportionality:** if `P_idle → 0` (ideal energy-proportional
   hardware), then `e_P = e_1`. Weak scaling would be free in energy per unit of
   work, and only the total energy would grow, in proportion to the extra work.
