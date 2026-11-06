# Task 07: Reverse Engineering the Maximum Tolerable Serial Overhead

**Given:** `P = 8,192` cores, requirement `S(P) ≥ 7,500`.

## Derivation

Start from Gustafson's law and impose the requirement:

```
S(P) = P − α(P − 1) ≥ S_req
```

Isolate α (note `P − 1 > 0`, so the inequality direction is preserved):

```
P − S_req ≥ α(P − 1)
α ≤ (P − S_req) / (P − 1)
```

Therefore:

```
α_max = (P − S_req) / (P − 1)
```

## Numerical solution

```
α_max = (8192 − 7500) / (8192 − 1)
      = 692 / 8191
      = 0.0844829691…
      ≈ 8.448 %
```

## Verification

```
S = 8192 − 0.0844829691 × 8191
  = 8192 − 692.000
  = 7500.0   ✔
```

## Interpretation

* **Tolerance:** the code may spend at most **8.45% of its parallel wall-clock
  time** in serial (or serialised) regions. In absolute terms that is 0.0845 s of
  every second of run time.
* **Efficiency at the threshold:** `E = 7500/8192 = 0.9155`.
* **The same requirement under Amdahl:** solving
  `1/(s + (1 − s)/8192) ≥ 7500` gives
  `s ≤ (1/7500 − 1/8192)/(1 − 1/8192) ≈ 1.126×10⁻⁵`, which is 7,500 times
  stricter. This shows how much the choice of frame matters (Task 03).
* **Design consequence:** any part of the run that grows with P, such as global
  reductions or all-to-all communication, eats into this 8.45% budget, so it
  should be profiled with the Karp-Flatt metric to make sure it stays constant.
