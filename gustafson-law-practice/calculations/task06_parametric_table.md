# Task 06: Parametric Speedup Across Processor Densities

**Given:** parallel-frame serial fraction α = 0.04.

**Formulas:**

```
S(P) = P − α(P − 1)
E(P) = S(P)/P = 1 − α(P − 1)/P
```

## Results

| P | Scaled speedup S(P) | Efficiency E(P) | Efficiency loss 1 − E | Amdahl S (same 0.04, for contrast) | Amdahl E |
|---|---|---|---|---|---|
| 16 | 16 − 0.04·15 = 15.40 | 0.962500 | 3.7500% | 10.00 | 0.625000 |
| 64 | 64 − 0.04·63 = 61.48 | 0.960625 | 3.9375% | 18.18 | 0.284091 |
| 256 | 256 − 0.04·255 = 245.80 | 0.960156 | 3.9844% | 22.86 | 0.089286 |
| 1,024 | 1024 − 0.04·1023 = 983.08 | 0.960039 | 3.9961% | 24.43 | 0.023855 |
| 4,096 | 4096 − 0.04·4095 = 3,932.20 | 0.960010 | 3.9990% | 24.85 | 0.006068 |
| 16,384 | 16384 − 0.04·16383 = 15,728.68 | 0.960002 | 3.9998% | 24.96 | 0.001524 |

## Numeric log (worked example for P = 1024)

```
S(1024) = 1024 − 0.04 × 1023 = 1024 − 40.92 = 983.08
E(1024) = 983.08 / 1024 = 0.960039
```

## Evaluation

1. **Speedup grows linearly.** Each ×4 in P multiplies S by about 4, with slope
   `1 − α = 0.96`. From 16 to 16,384 cores (×1024), S grows from 15.40 to 15,728.68
   (×1021).
2. **Efficiency barely degrades.** E falls from 0.9625 at P = 16 to 0.960002 at
   P = 16,384. The total drop across three orders of magnitude of P is only
   0.0025. E converges to the asymptote `1 − α = 0.96` (Task 04).
   `E − 0.96 = α/P`, so each ×4 in P cuts the remaining gap by 4.
3. **Exponential growth in P causes no exponential loss.** Under Gustafson the
   loss is bounded by α regardless of P. In the Amdahl column, by contrast,
   speedup saturates at `1/0.04 = 25`, and efficiency falls to 0.0015 at
   P = 16,384.
4. **Practical caveat.** These are ideal numbers. At thousands of cores,
   communication overhead that grows with P (Task 12) normally makes measured
   efficiency fall below 0.96.

The table is reproducible with `python benchmarks/simulator.py --alphas 0.04 --cores 16 64 256 1024 4096 16384`.
