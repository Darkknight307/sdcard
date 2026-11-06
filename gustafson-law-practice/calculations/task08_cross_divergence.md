# Task 08: Cross-Over Point Determination (Amdahl vs. Gustafson)

**Given:** serial fraction `s = α = 0.08`, `P = 128`.

## Step 1: Amdahl (fixed size)

```
S_A = 1 / (s + (1 − s)/P)
    = 1 / (0.08 + 0.92/128)
    = 1 / (0.08 + 0.0071875)
    = 1 / 0.0871875
    = 11.4695
E_A = 11.4695 / 128 = 0.0896
```

## Step 2: Gustafson (fixed time)

```
S_G = P − α(P − 1)
    = 128 − 0.08 × 127
    = 128 − 10.16
    = 117.84
E_G = 117.84 / 128 = 0.9206
```

## Step 3: Discrepancy

| Metric | Value |
|---|---|
| Absolute difference `S_G − S_A` | 117.84 − 11.4695 = **106.37** |
| Ratio `S_G / S_A` | **10.274** |
| % discrepancy relative to Amdahl `(S_G − S_A)/S_A` | **927.42 %** |
| % discrepancy relative to Gustafson `(S_G − S_A)/S_G` | 90.27 % |

Gustafson predicts about 10.3× more speedup on the same 128 cores with the "same"
8% serial fraction.

## Step 4: Where they agree and why they diverge

* **Cross-over:** the two laws coincide only at `P = 1`, where both give 1.
  Their difference is

  ```
  S_G − S_A = s(1 − s)(P − 1)² / (sP + 1 − s)
  ```

  which is zero at `P = 1` and strictly positive for all `P > 1` when
  `0 < s < 1`. It grows like `(1 − s)P` for large P.
* **Divergence as P scales:**
  * `S_A → 1/s = 12.5`. Amdahl is already at 92% of its ceiling with 128 cores.
  * `S_G ~ 0.92·P`, which keeps growing without bound.
  * Their ratio `S_G/S_A = (P − s(P − 1))(s + (1 − s)/P)` tends to `s(1 − s)P`.
    It grows linearly, so the gap widens in proportion to P.
* **Root cause:** the two 8% figures are measured in different frames (Task 03).
  Amdahl's 8% is the serial share of a **fixed** problem on one processor.
  Gustafson's 8% is the serial share of a **scaled** problem on 128 processors.
  If we convert Gustafson's α to the uniprocessor frame for the scaled problem,
  `s' = 0.08/(0.08 + 0.92 × 128) = 0.08/117.84 = 6.79×10⁻⁴`, then Amdahl with s'
  gives exactly 117.84.

## Step 5: Variance across P (same s = α = 0.08)

| P | S_A | S_G | S_G / S_A |
|---|---|---|---|
| 2 | 1.852 | 1.920 | 1.04 |
| 8 | 5.128 | 7.440 | 1.45 |
| 32 | 9.195 | 29.520 | 3.21 |
| 128 | 11.470 | 117.840 | 10.27 |
| 1024 | 12.361 | 942.160 | 76.22 |
