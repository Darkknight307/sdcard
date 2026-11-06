# Task 24: Hardware Audit and Empirical vs. Theoretical Discrepancy

Figure: [`plots/scaling_comparison.png`](../plots/scaling_comparison.png) (vector
version: [`plots/scaling_comparison.pdf`](../plots/scaling_comparison.pdf)).

The figure contains (1) ideal linear speedup, (2) the Gustafson curve from the
least-squares fit, (3) the measured points with standard-error bars (5 runs each)
and (4) Amdahl's curve with the same serial fraction.

## 1. Hardware architecture of the benchmark host

| Item | Value | Source |
|---|---|---|
| Platform | Linux 6.18 (x86_64), KVM virtual machine (cloud container) | `uname`, `lscpu` (Hypervisor vendor: KVM) |
| CPU model | Intel Xeon Processor @ 2.30 GHz (family 6, model 207 / 0xCF, stepping 2: 5th-gen Xeon Scalable "Emerald Rapids" class) | `lscpu` |
| ISA features | AVX2, AVX-512 (F/DQ/BW/VL/FP16/BF16/VNNI), AMX | `lscpu` flags |
| Cores / threads exposed | 4 vCPUs: 1 socket × 4 cores × 1 thread per core (SMT not exposed) | `lscpu` |
| L1d / L1i | 48 KiB / 64 KiB per core (192 KiB / 256 KiB total) | `lscpu` |
| L2 | 2 MiB per core (8 MiB total) | `lscpu` |
| L3 (LLC) | Shared, reported as 504 MiB to the guest (host-level value) | `lscpu` |
| Memory | 15.7 GiB RAM visible to the guest. Channel count is not visible inside the VM (no SMBIOS/`dmidecode` access). The host platform class provides 8 DDR5 channels per socket. | `/proc/meminfo` |
| NUMA | 1 NUMA node (`node0 CPUs 0-3`) | `lscpu` |
| Compiler | GCC 13.3, `-O2 -fopenmp` | `gcc --version` |

**Workload:** OpenMP midpoint integration of `4/(1+x²)`, `K = 5×10⁸` points per
thread, 5 runs per thread count, thread counts 1, 2, 3, 4, 6, 8.

The loop is a scalar, compute-bound division chain: one `divsd` per point plus
an add, about 1 ns per point. Its working set is a few registers, so **memory
bandwidth and cache size play no role**. Any deviation from linear speedup comes
from the CPU and scheduler, not from the memory system.

## 2. Measured results (from `benchmarks/results_summary.csv`)

| P | Mean T (s) | Std (s) | CV | S(P) = P·T₁/T_P | ±SE | E(P) | Karp-Flatt e |
|---|---|---|---|---|---|---|---|
| 1 | 0.5229 | 0.0065 | 1.2% | 1.000 | – | 1.000 | – |
| 2 | 0.5505 | 0.0093 | 1.7% | 1.900 | 0.018 | 0.950 | 0.0528 |
| 3 | 0.5473 | 0.0105 | 1.9% | 2.866 | 0.029 | 0.955 | 0.0233 |
| 4 | 0.5416 | 0.0091 | 1.7% | 3.862 | 0.036 | 0.966 | 0.0119 |
| 6* | 0.8660 | 0.0384 | 4.4% | 3.623 | 0.075 | 0.604 | 0.1312 |
| 8* | 1.0883 | 0.0315 | 2.9% | 3.844 | 0.054 | 0.480 | 0.1545 |

\* Oversubscribed (more threads than the 4 vCPUs). Excluded from the fit.

**Least-squares fit** of `S = P − α(P − 1)` over `P = 1…4`:

```
α_observed = 0.0558 ± 0.0089      R² = 0.9993
```

## 3. Empirical vs. theoretical discrepancy

1. **Up to 4 threads the Gustafson curve fits very well** (R² = 0.9993). The
   measured speedups 1.90, 2.87 and 3.86 lie within about 2.5% of the fit. Amdahl
   with the same s (red dash-dot) would predict only 3.43 at P = 4. The measured
   3.86 is clearly far above it, so this workload is in the weak-scaling regime.
2. **The overhead is a step, not a slope.** `T(P)` jumps from 0.523 s (P = 1) to
   about 0.545 s for P = 2–4, then stays flat. The Karp-Flatt metric *decreases*
   with P (0.053 → 0.023 → 0.012). A one-off cost that appears as soon as more
   than one core is busy is spread over more threads. This is the signature of
   Gustafson's constant α, not of growing communication (Task 12). The fit
   absorbs the step into α ≈ 0.056.
3. **Likely physical causes of the step:**
   * **Turbo / frequency behaviour:** a lone busy vCPU can run at a higher
     effective clock than when several are loaded. Single-core turbo versus
     all-core turbo on the host typically differs by about 5–10%, matching the
     roughly 5% step. Even inside a VM, the host's power control unit decides the
     frequency based on how many physical cores are active.
   * **Hypervisor scheduling:** with more busy vCPUs, the chance that a vCPU is
     descheduled or shares a physical core with another tenant (noisy neighbour,
     SMT sibling on the host) rises. The coefficient of variation also rises, from
     1.2% to 1.7–1.9%.
   * **OpenMP fork/join and reduction:** a few µs per run, which is negligible
     (< 0.01%) against 0.5 s.
4. **Oversubscription is the dominant failure.** At 6 and 8 threads on 4 vCPUs,
   T grows almost in proportion to P/4: 0.866 s (expected 0.78) and 1.088 s
   (expected 1.05). Speedup saturates at about 3.6–3.8 ≈ 4. The extra threads
   time-share the cores and add context switches, and at P = 6 the last two
   threads share cores with two others, so the run waits for the slowest pair.
   CV doubles to 4.4%. This is a hardware-concurrency ceiling, not a serial
   fraction. Gustafson's law does not apply past the core count, because
   "per-thread work constant" no longer means "per-core work constant".

## 4. Thermal throttling

* Each configuration ran for about 3–5 s in total (5 × ~0.55 s). That is too short
  for sustained thermal throttling on a data-centre server. Run-to-run times show
  no drift within a block (for example, P = 4 ranged 0.536–0.557 s with no
  monotonic trend).
* On a **laptop** (e.g. a fanless MacBook Air) the picture changes. After tens of
  seconds of all-core load, package power limits (PL1/PL2) and skin temperature
  limits lower the clock by 10–30%. Then `T(P)` rises with run index and with P,
  α_observed increases, and the measured points fall below the Gustafson line at
  high P. Mitigations: let the machine cool between configurations, randomise the
  order of P, report the median, and log frequency with `powermetrics`
  (macOS) or `turbostat` (Linux).

## 5. NUMA boundaries

* This host is a single NUMA node, so no NUMA effects are present.
* On multi-socket or chiplet systems (dual-socket Xeon, AMD EPYC with several
  CCDs per NUMA domain), crossing a NUMA boundary causes:
  * memory-bound workloads to lose locality when pages are first-touched by the
    wrong thread, with remote access costing about 1.5–2× the latency and less
    bandwidth;
  * shared data (reduction variables, locks) to bounce cache lines across the
    inter-socket link.

  The speedup curve would then show a **knee at the socket boundary**, for
  example at P = 32 on a 2 × 32-core machine. This compute-bound kernel would be
  largely immune, but a stencil or streaming kernel would not. Mitigations:
  `OMP_PROC_BIND=spread/close`, `OMP_PLACES=cores`, first-touch initialisation,
  `numactl --interleave` or per-socket MPI ranks.

## 6. Conclusion

Within the hardware concurrency the benchmark follows Gustafson's law closely,
with `α_obs = 0.056 ± 0.009`. The residual "serial fraction" is not serial code.
It is a constant multicore penalty (frequency or turbo, VM scheduling) that
appears once more than one core is active. Beyond the 4 vCPUs, oversubscription
caps the speedup at about 4. To reproduce on another machine, run the commands in
`benchmarks/weak_scale_bench/README.md` and regenerate this figure.
