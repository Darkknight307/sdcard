# Task 02: Formal Derivation of Gustafson's Scaled Speedup

## Set-up and notation

* `P`: number of processors.
* Measure time **on the parallel machine** and normalise the total parallel run
  time to one unit:

  ```
  T_par(P) = s + p = 1                                  (1)
  ```

  where `s` is the time the machine spends in serial code (one processor busy, the
  others idle) and `p` is the time spent in perfectly parallel code (all `P`
  processors busy).
* `α`: the serial fraction *observed on the parallel machine*. Because of (1),
  `α = s / (s + p) = s`.

## Step 1: Work done during the parallel run

* During the serial phase one processor works for time `s`, so serial work is
  `W_s = s` (processor-time units).
* During the parallel phase each of the `P` processors works for time `p`, so
  parallel work is `W_p = P · p`.
* Total work performed by the parallel run:

  ```
  W(P) = s + P·p                                         (2)
  ```

## Step 2: Equivalent serial workload

Ask how long one processor would take to perform the **same** work `W(P)`. A
single processor can do only one unit of work per unit of time, so it must
execute the serial part (`s`) and all `P` copies of the parallel part (`P·p`)
one after another:

```
T_serial(P) = s + P·p                                    (3)
```

This is the hypothetical uniprocessor time for the *scaled* problem. It is never
measured directly, because the scaled problem is usually too large for one node.

## Step 3: Scaled speedup

Speedup is serial time divided by parallel time for the same work:

```
S(P) = T_serial(P) / T_par(P) = (s + P·p) / (s + p)      (4)
     = (s + P·p) / 1                                     using (1)
     = s + p·P                                           (5)
```

This is Gustafson's law, `S(P) = s + p·P`.

## Step 4: Express in terms of the serial fraction α

From (1), `p = 1 - s`, and `α = s`. Substitute into (5):

```
S(P) = α + (1 - α)·P                                     (6)
     = α + P - α·P
     = P - α·P + α
     = P - α(P - 1)                                      (7)
```

which proves `S(P) = P − α(P − 1)`. ∎

## Step 5: Checks

| Case | Result | Meaning |
|---|---|---|
| `α = 0` | `S = P` | Perfectly parallel: linear speedup |
| `α = 1` | `S = 1` | Entirely serial: no speedup |
| `P = 1` | `S = 1` | Consistent with one processor |
| `dS/dP` | `1 - α` | Speedup grows linearly, with slope `1 - α` |

## Step 6: Corresponding efficiency

```
E(P) = S(P)/P = 1 - α(P - 1)/P                           (8)
```

`E(P)` falls only from `1` (at `P = 1`) to `1 - α` (as `P → ∞`). See Task 04.

## Remark: why the normalisation matters

Normalising the *parallel* time to `s + p = 1` is what makes `α` a property of
the parallel run. If instead the *serial* time were normalised, we would be back
in Amdahl's frame. Task 03 converts between the two frames explicitly.
