# Task 05: Deconstructing "Amdahl's Pessimism" (the 1988 nCUBE Case)

## 1. Historical context

In the 1980s, Amdahl's 1967 argument was widely cited as proof that massively
parallel computers were a dead end. A typical serial fraction of a few tenths of
a percent seemed to cap useful speedup at a few hundred, whatever the number of
processors. Alan Karp of IBM publicly offered a prize for a demonstrated speedup
of 200× on a real scientific application. Many considered that target
unreachable.

In 1988 John Gustafson, Gary Montry and Robert Benner at Sandia National
Laboratories published *"Development of Parallel Methods for a 1024-Processor
Hypercube"* (SIAM J. Sci. Stat. Comput. 9(4)). In the same year Gustafson
published the companion essay *"Reevaluating Amdahl's Law"* (Communications of the
ACM 31(5)).

## 2. The experimental system

* **Machine:** nCUBE 10, a distributed-memory hypercube with 1,024 nodes
  (a 10-dimensional hypercube). Each node had its own processor and local memory,
  and nodes communicated only by message passing along hypercube links.
* **Applications** (all production-style scientific codes):
  1. Beam stress analysis using a finite-element conjugate-gradient solver.
  2. Baffled surface-wave simulation using explicit finite differences.
  3. Unstable fluid flow using flux-corrected transport.
* **Reported scaled speedups on 1,024 processors:** about **1021, 1020 and
  1016** respectively, all over 1,000×.
* **Measured serial fraction (parallel frame):** roughly **0.4%–0.8%**.

## 3. Why this looked impossible under Amdahl

With `s = 0.004` and `P = 1024`:

```
S_Amdahl = 1 / (0.004 + 0.996/1024) = 1 / (0.004 + 0.000973) ≈ 201
```

The asymptotic ceiling is `1/s = 250`. Amdahl's law therefore predicts about
**201×**, five times less than what was observed.

## 4. Reconstruction with Gustafson's law

Treat the 0.4% as the serial fraction **observed on the parallel run**:

```
S_G = P - α(P - 1) = 1024 - 0.004·1023 ≈ 1019.9
```

This matches the measured 1016–1021 almost exactly. Inverting the measurements
gives the implied parallel-frame serial fractions:

```
α = (P - S)/(P - 1)
S = 1021 → α = 3/1023 ≈ 0.0029
S = 1016 → α = 8/1023 ≈ 0.0078
```

These are consistent with the reported 0.4–0.8% range.

## 5. How problem expansion dismantled the ceiling

1. **The problem was scaled with the machine.** Each node kept a fixed-size
   subdomain (fixed memory per node). Going from 1 to 1,024 nodes multiplied the
   global grid or mesh by 1,024. The parallel run time stayed roughly constant.
2. **The serial part did not grow.** Set-up, host I/O and global control took
   about the same absolute time whether the mesh was small or 1,024× larger.
3. **Uniprocessor time was inferred, not measured.** The scaled problem did not
   fit in one node's memory, so `T(1)` was computed as the sum of the serial time
   and 1,024 times the per-node parallel time. This is exactly the Task 02
   construction.
4. **The relevant serial fraction collapsed.** Seen from a single processor
   working on the scaled problem, the serial fraction is
   `s(1024) = α/(α + (1 - α)·1024) ≈ 0.004/1020 ≈ 3.9×10⁻⁶`, so the Amdahl
   ceiling for *that* problem is about 255,000×. The 1,000× speedup is far below
   it.
5. **Engineering mattered too.** The team minimised communication by
   exploiting nearest-neighbour hypercube links. They overlapped communication
   with computation and kept host-node I/O out of the timed loop. This kept `α`
   both small and constant with `P`.

## 6. Fixed-size results for honesty

The paper also reported *fixed-size* (Amdahl-style) speedups for problems small
enough to fit on one node. These were much lower (hundreds rather than over a
thousand). The authors' point was not that Amdahl was wrong. It was that
fixed-size speedup answers a question practitioners rarely ask.

## 7. Lessons

* The "ceiling" `1/s` is a property of a **fixed** problem. Users of large
  machines do not run fixed problems.
* The parallel-frame serial fraction is the right engineering metric. If it
  stays constant, scaled speedup grows linearly.
* This result reframed the debate and launched weak scaling as the standard
  benchmark methodology for supercomputers.
