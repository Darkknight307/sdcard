# Task 03: The Serial Fraction Invariance Paradox

**Memo: Which "serial fraction" are we talking about?**

## 1. The apparent contradiction

* Amdahl: with a serial fraction of `s = 0.04`, no machine can ever exceed
  `1/s = 25×` speedup.
* Gustafson: with a serial fraction of `α = 0.04`, a 1,024-processor machine
  achieves `S = 1024 - 0.04·1023 ≈ 983×`.

Both claim to use "4% serial". They cannot both be right unless the two 4% figures
describe *different quantities*. They do: they are measured in **different frames
of reference**.

## 2. Two frames of reference

| Frame | Where measured | Definition |
|---|---|---|
| Amdahl's `s` | Uniprocessor run of the problem | `s = T_serial_code / T_total(1 processor)` |
| Gustafson's `α` | Parallel run on `P` processors | `α = T_serial_code / T_total(P processors)` |

The serial code does the same absolute work in both. What differs is the
denominator: in Amdahl's frame it is the *whole* work done by one processor; in
Gustafson's frame it is the *wall-clock* time of the parallel run.

## 3. Converting α (parallel frame) into s (uniprocessor frame)

Take a scaled run normalised as in Task 02: serial time `α`, parallel time `1 - α`
on each of `P` processors. Run **that same scaled problem** on one processor:

```
T_1 = α + (1 - α)·P
```

The fraction of *this* uniprocessor time spent in serial code is Amdahl's `s` for
the scaled problem:

```
s(P) = α / (α + (1 - α)P)                                    (1)
```

**Key result:** for fixed `α > 0`,

```
lim_{P→∞} s(P) = lim α / (α + (1 - α)P) = 0.
```

The serial fraction a uniprocessor would see **shrinks towards zero** as the
problem grows. The serial code is not slower or faster; it is simply diluted by an
ever larger parallel workload.

## 4. Proof that the two laws then agree

Plug `s(P)` from (1) into Amdahl's formula:

```
S_A = 1 / (s + (1 - s)/P)

1 - s = (1 - α)P / (α + (1 - α)P)

S_A = 1 / [ α/(α + (1 - α)P) + (1 - α)/(α + (1 - α)P) ]
    = (α + (1 - α)P) / (α + 1 - α)
    = α + (1 - α)P
    = P - α(P - 1) = S_G                                        ∎
```

Amdahl's and Gustafson's laws give the **same speedup for the same run** once both
are expressed in the same frame. The "paradox" is purely a change of reference.

## 5. Numerical illustration (α = 0.04)

| P | Gustafson S | Equivalent uniprocessor s(P) | Amdahl ceiling 1/s(P) |
|---|---|---|---|
| 1 | 1.00 | 0.0400 | 25 |
| 16 | 15.40 | 0.0026 | 385 |
| 256 | 245.80 | 0.000163 | 6,145 |
| 1024 | 983.08 | 0.0000407 | 24,577 |

As `P` grows, the uniprocessor-frame serial fraction of the *scaled* problem
falls, and the Amdahl ceiling rises in step. Gustafson's speedup never hits the
ceiling because the ceiling moves with the problem.

## 6. Why the parallel frame is the right one for overhead

1. **It is measurable.** For a scaled problem that only fits in the memory of
   `P` nodes, the uniprocessor run cannot be executed. The parallel run can be
   instrumented directly: time in serial regions over total wall time.
2. **It is what is invariant.** For many applications (I/O, set-up, global
   control) the serial time is roughly constant in absolute seconds, so `α`
   measured on the parallel machine is stable as `P` grows. Amdahl's `s` is not
   stable, because it depends on the problem size.
3. **It is how overheads are profiled in practice.** Profilers report wall-clock
   shares on the running machine. The Karp-Flatt metric
   `e = (1/S - 1/P)/(1 - 1/P)` is this kind of measurement. If `e` stays constant
   with `P` the overhead is genuinely serial. If `e` grows, the overhead is
   parallel (communication, contention) and neither law's constant fraction
   describes it (see Task 12).

## 7. Conclusion

Serial overhead does not throttle massive scaling because, *measured where it
happens*, on the parallel machine, it is a constant slice of a constant time. In
uniprocessor terms it is an ever smaller slice of an ever larger problem.
Amdahl's pessimism comes from freezing `s` at the value of a problem size the user
no longer runs.
