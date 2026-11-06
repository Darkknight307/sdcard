# Task 09: Multi-Component Workload Partitioning

**Given** (fractions of total **parallel** execution time):

| Phase | Description | Share of parallel time | Execution mode |
|---|---|---|---|
| A | Initial disk I/O and parameter broadcast | 2% | Serial: one root process reads, the others wait |
| B | Boundary message-passing synchronisation | 6% | Serialised: no useful computation overlaps it |
| C | Core domain flux computation | 92% | Perfectly parallel |

## Step 1: Aggregate serial fraction

Under Gustafson's model, any time in which the machine does not do scalable work
counts toward α. The I/O and the synchronisation phases both run "outside" the
scalable computation, so:

```
α = α_A + α_B = 0.02 + 0.06 = 0.08
p = α_C       = 0.92
check: α + p  = 1.00 ✔
```

## Step 2: Scaled speedup

```
S(P) = P − α(P − 1)

S(512)  = 512  − 0.08 × 511  = 512  − 40.88  = 471.12
S(2048) = 2048 − 0.08 × 2047 = 2048 − 163.76 = 1884.24
```

| P | S(P) | E(P) = S/P | Amdahl with s = 0.08 (contrast) |
|---|---|---|---|
| 512 | **471.12** | 0.9202 | 12.23 |
| 2048 | **1884.24** | 0.9200 | 12.43 |

## Step 3: Phase-wise breakdown of the scaled workload

The equivalent single-processor time for the scaled problem is `α + pP`. Each
phase's share of it is:

| P | Phase A (I/O) | Phase B (sync) | Phase C (compute) | Total T₁ |
|---|---|---|---|---|
| 512 | 0.02 | 0.06 | 0.92 × 512 = 471.04 | 471.12 |
| 2048 | 0.02 | 0.06 | 0.92 × 2048 = 1884.16 | 1884.24 |

Seen from a uniprocessor, the serial phases shrink to `0.08/471.12 = 0.017%`
(P = 512) and `0.0042%` (P = 2048) of the scaled work. This is why the speedup
keeps growing.

## Step 4: Composite analysis and sensitivity

* **Dominant overhead:** synchronisation (6%) costs three times as much as I/O
  (2%). Optimising the halo exchange, for example by overlapping communication
  with computation, would raise S far more than parallel I/O would.
* **If synchronisation were fully overlapped** (α = 0.02):
  `S(2048) = 2048 − 0.02 × 2047 = 2007.06`, which is **+6.5%** over 1884.24.
* **A more realistic model:** boundary synchronisation contains collectives whose
  cost grows like `log₂ P`. Suppose the 6% was measured at P = 512 and is scaled by
  `log₂ 2048 / log₂ 512 = 11/9`:

  ```
  sync(2048) = 0.06 × 11/9 = 0.0733
  T_par      = 0.02 + 0.0733 + 0.92 = 1.0133
  α_eff      = (0.02 + 0.0733)/1.0133 = 0.0921
  S(2048)    = (0.02 + 0.0733 + 0.92 × 2048)/1.0133 = 1859.46   (E = 0.908)
  ```

  Speedup is then about 1.3% lower than the constant-α prediction. This is why
  Task 12 extends the model with a communication term `C(P)`.

## Conclusion

The aggregate serial fraction is **α = 0.08**, which gives scaled speedups of
**471.12 (P = 512)** and **1884.24 (P = 2048)** at about 92% efficiency.
