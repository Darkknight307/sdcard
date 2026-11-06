# Task 01: Strong Scaling vs. Weak Scaling Foundations

## 1. Two questions, two laws

| | Amdahl (1967) | Gustafson (1988) |
|---|---|---|
| Question asked | *How much faster can I solve **this** problem?* | *How much **bigger** a problem can I solve in the same time?* |
| Held constant | Total problem size `W` | Wall-clock time `T` (per-processor work) |
| Serial fraction measured on | A uniprocessor run of the fixed problem | The parallel machine, during the scaled run |
| Speedup formula | `S_A(P) = 1 / (s + (1 - s)/P)` | `S_G(P) = s + (1 - s)P = P - α(P - 1)` |
| Limit as `P → ∞` | `1/s` (bounded) | `∞` (grows linearly, slope `1 - α`) |
| Name | Fixed-size scaling / strong scaling | Fixed-time scaling / weak scaling / scaled speedup |

## 2. Foundational assumptions

### Amdahl
1. The problem is fixed: `W = W_s + W_p` does not depend on `P`.
2. A fraction `s = W_s / W` of the work is inherently sequential. The remaining
   `1 - s` is perfectly divisible.
3. Adding processors shrinks only the parallel part:
   `T(P) = s·T(1) + (1 - s)·T(1)/P`.
4. Implicitly, the user wants the *same answer sooner*: latency is the objective.

### Gustafson
1. The run time is fixed. The user has a time budget (overnight, one simulation
   step per second) and fills it with as much work as the machine can do.
2. On the parallel machine the time splits into a serial part `s` and a parallel
   part `p`, with `s + p = 1`.
3. The serial part (I/O, set-up, control) does **not** grow with the problem. The
   parallel part grows with `P`, because each processor gets the same amount of
   work.
4. Implicitly, the user wants a *better answer in the same time*: finer
   resolution, more particles, more Monte-Carlo samples. Throughput and fidelity
   are the objective.

## 3. How the problem dimension behaves as P → ∞

Write the work as `W(P) = W_s + W_p(P)`.

* **Amdahl:** `W(P) = W(1)` for all `P`. As `P → ∞` the problem is cut into ever
  finer pieces of size `W_p/P → 0`. Eventually every processor holds a vanishing
  sliver of work, and run time tends to the irreducible floor `s·T(1)`. The
  problem dimension is **constant** and the *per-processor* dimension tends to
  zero.
* **Gustafson:** `W_p(P) = P · W_p(1)`, so `W(P) = W_s + P·W_p(1) → ∞` linearly.
  The per-processor dimension is **constant**, and the global dimension grows
  without bound. For a `d`-dimensional grid with `N^d` points this means
  `N(P) = N(1)·P^{1/d}`.

## 4. Why "fixed-size" vs. "fixed-time"

* Amdahl fixes the **size** and lets time fall. Speedup is
  `T(1, W) / T(P, W)`: both runs solve the same problem.
* Gustafson fixes the **time** and lets size grow. Speedup is
  `T(1, W(P)) / T(P, W(P))`: the hypothetical time one processor would need for
  the scaled problem, divided by the actual (constant) parallel time. Because the
  denominator is constant, speedup is directly proportional to how much work was
  done in that time.

## 5. Philosophical divergence

* **Pessimism vs. optimism:** Amdahl treats the serial fraction as a property of
  the *algorithm*. Gustafson treats it as a property of the *run*, which shrinks
  in relative terms as the problem grows. Amdahl concludes that massive
  parallelism is futile beyond `1/s` processors. Gustafson concludes that it is
  worthwhile so long as the problem can grow.
* **Users' behaviour:** Gustafson's key empirical observation is that scientists
  do not run the same small problem on a bigger machine. They raise the
  resolution until the run time is again "as long as they are willing to wait".
  Amdahl's model describes a latency-bound user (interactive response, real-time
  control). Gustafson's describes a capability user (simulation, analytics).
* **Same mathematics, different frame:** both are exact for their own
  assumptions. Task 03 shows they are algebraically equivalent once the serial
  fraction is measured in the same frame of reference.

## 6. Physical divergence

* **Memory:** strong scaling keeps total memory constant, so per-node memory
  shrinks and data eventually fits in cache. This can even cause superlinear
  speedup. Weak scaling keeps per-node memory constant, so total memory grows
  with `P` (`M(P) = c·P`). Real machines grow memory with node count, which
  makes weak scaling physically natural.
* **Communication:** in strong scaling the surface-to-volume ratio of each
  subdomain *worsens* as `P` grows, because subdomains shrink. In weak scaling it
  stays constant (see Task 17).
* **Energy and time budgets:** weak scaling matches machines procured for a fixed
  time-to-solution per run. Strong scaling matches latency-critical workloads.

## 7. Summary

Amdahl answers *"how fast"* with a ceiling of `1/s`. Gustafson answers *"how
much"* with a line of slope `1 - α`. The divergence is not a contradiction. It is
a choice of which quantity, size or time, is held fixed as the machine grows.
