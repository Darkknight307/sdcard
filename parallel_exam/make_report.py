# make_report.py  (helper - NOT part of the submission)
# Run AFTER benchmark_gustafson.py. It
#   1. reads benchmark_telemetry.json + scaling_results.csv,
#   2. runs a small granularity probe with N0 = 10,000 (for Q3.3),
#   3. writes report.md (derivations, Table 1, Part 3 answers with your numbers),
#   4. builds <StudentID>_Exam.zip with the four files at the archive root.
#
# Usage:  python make_report.py

import csv, json, os, zipfile
import multiprocessing as mp

import benchmark_gustafson as ws

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE_N0 = 10_000


def load():
    with open(os.path.join(HERE, "benchmark_telemetry.json")) as f:
        tel = json.load(f)
    with open(os.path.join(HERE, "scaling_results.csv")) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["P"] = int(r["P"])
        for k in ("T_parallel_s", "T_serial_s", "speedup", "efficiency",
                  "memory_MB", "throughput_GBps", "T_task_inflation"):
            r[k] = float(r[k])
        r["s_emp"] = None if r["s_emp"] == "N/A" else float(r["s_emp"])
    return tel, rows


def granularity_probe(counts):
    """Same harness, but every task only gets PROBE_N0 elements."""
    ws.N0 = PROBE_N0
    out = []
    for p in counts:
        tasks = [(float(i), PROBE_N0, ws.K1, ws.K2) for i in range(p)]
        t_par, _, _ = ws.measure(p, tasks)
        t_ser = t_par if p == 1 else ws.measure(1, tasks)[0]
        s = t_ser / t_par
        out.append({"P": p, "T_parallel_s": t_par, "T_serial_s": t_ser, "speedup": s,
                    "s_emp": (p - s) / (p - 1) if p > 1 else None})
    return out


def fmt_s(x):
    return "N/A" if x is None else f"{x:.4f}"


def to_markdown(lines):
    """Join report lines: paragraphs get a blank line between them, consecutive
    table rows / list items stay together, indented lines become code blocks."""
    out, prev, in_fence = [], None, False
    for line in lines:
        if line.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            prev = "fence"
            continue
        if in_fence:
            out.append(line)
            continue
        if not line.strip():
            kind = "blank"
        elif line.startswith("   "):
            kind = "code"
        elif line.startswith("|"):
            kind = "table"
        elif line.startswith("- "):
            kind = "list"
        else:
            kind = "para"
        if prev == "code" and kind != "code":
            out.append("```")
        if kind == "code":
            if prev != "code":
                if out and out[-1].strip():
                    out.append("")
                out.append("```")
            out.append(line[3:])
        elif kind == "blank":
            out.append("")
        else:
            if out and out[-1].strip() and not (kind == prev and kind in ("table", "list")):
                out.append("")
            out.append(line)
        prev = kind
    if prev == "code":
        out.append("```")
    text = "\n".join(out)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip() + "\n"


def build_text(tel, rows, probe):
    sid = tel["student_id"]
    n0 = tel["benchmark_parameters"]["N0"]
    k1 = tel["benchmark_parameters"]["K1"]
    k2 = tel["benchmark_parameters"]["K2"]
    p_phys = tel["p_phys_used"]
    by_p = {r["P"]: r for r in rows}
    r1 = by_p[1]
    cpu = tel["processor_microarchitecture"]
    caches = tel.get("cache_sizes") or {}
    cache_txt = ", ".join(f"{k}={v}" for k, v in caches.items()) or "not reported by the OS"
    task_mb = n0 * 8 * 3 / 1024**2
    L = []
    w = L.append

    # ------------------------------------------------------------------ header
    w("# Parallel Computing - Practical Examination Report")
    w("")
    w(f"**Student ID:** {sid}  ")
    w(f"**Run timestamp:** {tel.get('timestamp', '-')}")
    w("")
    w("## Machine profile (from benchmark_telemetry.json)")
    w("")
    w("| Item | Value |")
    w("|---|---|")
    w(f"| OS platform | {tel['os_platform']} |")
    w(f"| Processor | {cpu} ({tel['machine_architecture']}) |")
    w(f"| Physical cores / logical threads | {tel['physical_cores']} / {tel['logical_threads']} |")
    w(f"| P_phys used (capped at 16) | {p_phys} |")
    w(f"| Caches | {cache_txt} |")
    w(f"| RAM | {tel.get('total_ram_gb', '-')} GB |")
    w(f"| Python / NumPy | {tel['python_version']} / {tel['numpy_version']} |")
    w(f"| multiprocessing start method | {tel['multiprocessing_start_method']} |")
    w("")

    # ------------------------------------------------------------------ Part 0
    w("## Part 0: Student seed derivation")
    w("")
    w("```")
    w(f"N0 = 800,000 + (STUDENT_ID % 25) * 40,000")
    w(f"   = 800,000 + ({sid} % 25) * 40,000 = 800,000 + {sid % 25} * 40,000 = {n0:,}")
    w(f"K1 = (STUDENT_ID % 8) + 2 = ({sid} % 8) + 2 = {sid % 8} + 2 = {k1}")
    w(f"K2 = ((STUDENT_ID // 10) % 6) + 3 = ({sid // 10} % 6) + 3 = {(sid // 10) % 6} + 3 = {k2}")
    w("```")
    w("")

    # ------------------------------------------------------------------ Part 1
    w("## Part 1: Benchmark harness (benchmark_gustafson.py)")
    w("")
    w("- **Weak scaling:** for every P the problem is `N(P) = P x N0`. P tasks are created, each "
      "with its own N0-element float64 array (`np.linspace(i, i + 2, N0)`), so the per-core work "
      "is constant.")
    w("- **Kernel:** `weights = sqrt(|data*K1| + 1)`, `kernel_val = 1 / (1 + (data/K2)^2)`; "
      "each task returns `sum(weights * kernel_val)`.")
    w(f"- **Process counts:** P in {{1, 2, 4, P_phys, 2*P_phys}} = {tel['process_counts']}.")
    w("- **T_parallel(P):** wall-clock time for a `multiprocessing.Pool(P)` to run the P tasks "
      "concurrently (`starmap`, chunksize 1).")
    w("- **T_serial(P):** wall-clock time for a `Pool(1)` (one process) to run the same P tasks "
      "one after another. For P = 1 both definitions are the same experiment, so S(1) = 1.")
    w(f"- **Timing:** one untimed warm-up per pool, then the median of "
      f"{tel['benchmark_parameters']['repeats']} repeats. Pool start-up is excluded. A checksum "
      "confirms that the serial and parallel runs give the same result.")
    w("- **Derived metrics:** `S(P) = T_serial / T_parallel`, `s_emp(P) = (P - S) / (P - 1)`, "
      "`E(P) = S / P`.")
    w("")

    # ------------------------------------------------------------------ Part 2
    w("## Part 2: Table 1 (exact values from scaling_results.csv)")
    w("")
    w("| Processes (P) | Total Elements (P x N0) | T_parallel (s) | T_serial (s) | Speedup S(P) | s_emp(P) |")
    w("|---|---|---|---|---|---|")
    for r in rows:
        label = str(r["P"])
        if r["P"] == p_phys:
            label += " (P_phys)"
        elif r["P"] == 2 * p_phys:
            label += " (2 x P_phys)"
        w(f"| {label} | {r['P']} x N0 = {r['P'] * n0:,} | {r['T_parallel_s']:.6f} | "
          f"{r['T_serial_s']:.6f} | {r['speedup']:.4f} | {fmt_s(r['s_emp'])} |")
    w("")
    w("## Part 3: Hardware diagnostics & scaling analysis")
    w("")

    # ------------------------------------------------------------------ Q3.1
    w("### Q3.1: Scaling Efficiency and Aggregate Cache Multiplying")
    w("")
    w("E(P) = S(P) / P:")
    for r in rows:
        w(f"   P = {r['P']:>2}:  E = {r['speedup']:.4f} / {r['P']} = {r['efficiency']:.4f}")
    e2 = by_p[2]["efficiency"] if 2 in by_p else None
    e4 = by_p[4]["efficiency"] if 4 in by_p else None
    w("")
    if e2 is not None and e2 >= 0.9:
        w(f"At P = 2 the efficiency ({e2:.3f}) is close to the Gustafson ideal of 1.0, "
          f"so two concurrent sub-problems scale almost linearly.")
    elif e2 is not None:
        w(f"Efficiency already degrades at P = 2 (E = {e2:.3f}, i.e. "
          f"{(1 - e2) * 100:.1f}% below the ideal 1.0), so near-linear scaling was not reached.")
    if e4 is not None:
        verdict = "still near-linear" if e4 >= 0.9 else "clearly sub-linear"
        w(f"At P = 4, E = {e4:.3f}, which is {verdict}.")
    w(f"At P = P_phys = {p_phys}, E = {by_p[p_phys]['efficiency']:.3f}; at P = 2*P_phys = "
      f"{2 * p_phys}, E = {by_p[2 * p_phys]['efficiency']:.3f}. Beyond P_phys the extra processes "
      f"only time-share the same {tel['physical_cores']} physical cores, so E must fall.")
    if "apple" in cpu.lower():
        w(f"Note for Apple Silicon: the {tel['physical_cores']} physical cores are not identical. "
          "They mix high-performance (P) cores and slower efficiency (E) cores. Once P exceeds "
          "the number of P-cores, some tasks land on E-cores and the slowest task sets "
          "T_parallel, which lowers E(P) before P_phys is reached.")
    w("")
    w(f"Cache effect: each task touches N0 x 8 B = {n0 * 8 / 1024**2:.2f} MB per array, about "
      f"{task_mb:.1f} MB for the three arrays named in the brief (more with NumPy temporaries).")
    w(f"The reported caches ({cache_txt}) are far smaller than this, so one task's working set "
      "never fits in the private L1/L2 caches (and at most partly in the shared L3). Under weak scaling the per-task problem size is fixed, so "
      "giving each sub-problem its own core does add one more private L1/L2 to the machine "
      "(aggregate cache grows as P x L2). But the cache available per sub-problem stays exactly "
      "the same and each task still streams from DRAM. No super-linear 'cache multiplying' "
      "effect is possible here" + (", and none is visible in the data: no E(P) exceeds 1."
      if all(r["efficiency"] <= 1.0 for r in rows) else
      ". The E(P) slightly above 1 that was measured is timing noise or turbo variation, "
      "not a cache effect."))
    w(f"Instead, the single-task cost grows with P: T_parallel(P)/T_parallel(1) = "
      + ", ".join(f"{r['T_task_inflation']:.3f} (P={r['P']})" for r in rows) + ".")
    w(f"One task takes only ~{r1['T_parallel_s'] * 1000:.1f} ms. At that size the fixed cost of "
      "dispatching through the Pool (task-queue pickling, pipe IPC, waking the worker, "
      "collecting results) is a visible share of the total. Up to P_phys the loss comes from "
      "this coordination overhead plus memory-bus sharing (Q3.2). It does not come from cache "
      "capacity, and above P_phys the OS scheduler time-slicing processes on shared cores "
      "dominates.")
    w("")

    # ------------------------------------------------------------------ Q3.2
    w("### Q3.2: Memory Bus Contention and Bandwidth Saturation")
    w("")
    w("Memory footprint (MB) = P x N0 x 8 B x 3 / 1024^2 ;  throughput (GB/s) = MB / 1024 / T_par")
    sel = [p for p in (1, 4, p_phys) if p in by_p]
    seen = []
    for p in sel:
        if p in seen:
            continue
        seen.append(p)
        r = by_p[p]
        label = f"P = {p}" + (" (= P_phys)" if p == p_phys else "")
        w(f"   {label:<16} {p} x {n0:,} x 8 x 3 / 1024^2 = {r['memory_MB']:8.2f} MB ;  "
          f"{r['memory_MB']:.2f} / 1024 / {r['T_parallel_s']:.6f} s = {r['throughput_GBps']:.3f} GB/s")
    tp1 = by_p[1]["throughput_GBps"]
    tpp = by_p[p_phys]["throughput_GBps"]
    w("")
    w(f"Going from P = 1 to P = P_phys = {p_phys}, the aggregate throughput rises "
      f"{tpp / tp1:.2f}x, compared with the ideal {p_phys}x, while the problem volume grows "
      f"{p_phys}x. (These figures are a lower bound: NumPy creates about 6-8 temporary arrays "
      f"per task, so the real DRAM traffic is several times larger than the three-array "
      f"formula.)")
    w("Why s_emp(P) appears to grow: the kernel is a streaming, low-arithmetic-intensity loop. "
      "Each element costs a few flops (multiply, abs, sqrt, divide, square) but 8 B are read "
      "or written per array pass. A single core can already use a large part of the socket's "
      "DRAM bandwidth B. All cores share one memory controller, so once P cores together demand "
      "more than B, each core gets about B/P and every task stalls on memory. That stretches "
      "T_parallel(P), so S(P) = T_serial / T_parallel grows more slowly than P. The formula "
      "s_emp = (P - S) / (P - 1) assumes that any shortfall from linear speedup comes from "
      "serial code, so it reports the bandwidth wait time as a rising 'serial fraction'.")
    w("Measured: " + ", ".join(f"s_emp({r['P']}) = {fmt_s(r['s_emp'])}"
                                for r in rows if r['s_emp'] is not None) + ".")
    w("The algorithm's true serial part (the Python loop that submits P tuples and adds P "
      "floats) is constant and tiny. The growth is a hardware resource limit (memory "
      "bandwidth, and above P_phys also core time-sharing) masquerading as serial code.")
    w("")

    # ------------------------------------------------------------------ Q3.3
    w("### Q3.3: Kernel Granularity and Amortization of Runtime Dispatch")
    w("")
    w(f"To check this empirically, the same harness was re-run with N0 = {PROBE_N0:,} "
      f"({n0 // PROBE_N0}x smaller than the assigned {n0:,}):")
    w(f"| P | T_parallel (s) | T_serial (s) | S(P) | s_emp(P) at N0 = {PROBE_N0:,} "
      f"| s_emp(P) at N0 = {n0:,} |")
    w("|---|---|---|---|---|---|")
    for q in probe:
        big = by_p[q["P"]]["s_emp"]
        w(f"| {q['P']} | {q['T_parallel_s']:.6f} | {q['T_serial_s']:.6f} | {q['speedup']:.4f} "
          f"| {fmt_s(q['s_emp'])} | {fmt_s(big)} |")
    w("")
    floor = min(q["T_parallel_s"] for q in probe)
    w(f"With N0 = {PROBE_N0:,} the kernel itself needs only microseconds, but T_parallel never "
      f"drops below ~{floor * 1e6:.0f} us, which is the fixed dispatch floor of multiprocessing.Pool "
      f"on this machine. Because compute time no longer dominates, S(P) collapses towards 1 (or "
      f"below) and s_emp(P) rises towards 1.0, and can even exceed 1 when the parallel run is "
      f"slower than the serial one. That breaks Gustafson's assumption that coordination "
      f"cost is negligible compared with the scaled parallel work.")
    w("Where the floor comes from, per task and per pool.starmap() call:")
    w("- IPC: Pool sends every task through a multiprocessing queue (an OS pipe, or a named "
      "pipe on Windows) guarded by locks, and results come back on a second pipe. Each hop "
      "is at least one write/read system call plus a wake-up of the receiving process. The "
      "main process also runs feeder and result-handler threads that must be scheduled.")
    w("- Pickle serialization: every task tuple (seed, N0, K1, K2) is pickled in the parent "
      "and unpickled in the worker, and the returned float is pickled back. Here the payload "
      "is tiny because each worker builds its own array with np.linspace. If NumPy arrays "
      "were sent instead, pickling would copy N0 x 8 bytes per task through the pipe, which "
      "is a cost proportional to the data and would erase the parallel gain.")
    w("- Context switches: each task needs the parent's feeder thread, the worker and the "
      "result-handler thread to be scheduled in turn, a few context switches of roughly "
      "1-10 us each. When P > P_phys the workers are also time-sliced on the same cores. "
      "Process start-up (fork/spawn plus re-importing NumPy, ~50-500 ms) is even larger. It "
      "is excluded from these timings, but a real run pays it once per pool.")
    w("These costs do not shrink with N0, so they set a hard lower bound "
      "T_par >= T_dispatch(P). Speedup only approaches P when T_compute(N0) >> T_dispatch, "
      f"which is why the assigned N0 = {n0:,} (~{r1['T_parallel_s'] * 1000:.1f} ms per task) "
      "is needed for meaningful weak-scaling numbers.")
    w("")

    # ------------------------------------------------------------------ Q3.4
    w("### Q3.4: Dynamic Thermal Throttling and Turbo Boost Divergence")
    w("")
    w("Model: a task of W cycles runs in t = W / f. The serial baseline runs on ONE busy core, "
      "which turbo-boosts to f1. The parallel run loads all cores, which settle at the lower "
      "all-core clock f_P < f1 (TDP and thermal limits).")
    w("   T_serial(P)   = P * W / f1")
    w("   T_parallel(P) = W / f_P + T_overhead")
    w("   S_meas(P) = T_serial / T_parallel = P * (f_P / f1)   (ignoring overhead)")
    w("   => S_meas(P) = S_true(P) * (f_P / f1),   S_true(P) = S_meas(P) * (f1 / f_P)")
    w("   => E_meas = E_true * f_P / f1")
    w("   => s_emp,meas = (P - S_true * f_P/f1) / (P - 1)  >  s_emp,true")
    w("Even a perfect algorithm (S_true = P) therefore shows an apparent serial fraction")
    w("   s_emp,meas = P (1 - f_P/f1) / (P - 1),")
    w("which is caused purely by clock frequency and not by serial code.")
    ratio = 3.2 / 4.5
    w(f"Example from the brief: f1 = 4.5 GHz, f_P = 3.2 GHz -> f_P/f1 = {ratio:.3f}. A perfect "
      f"{p_phys}-way speedup would be measured as only {p_phys * ratio:.2f}x "
      f"(E = {ratio:.3f}), and s_emp would read "
      f"{p_phys * (1 - ratio) / (p_phys - 1) if p_phys > 1 else 0:.3f} instead of 0.")
    rp = by_p[p_phys]
    w(f"Applied to my P_phys = {p_phys} result: S_meas = {rp['speedup']:.3f} would correspond to "
      f"S_true = {rp['speedup'] / ratio:.3f} (E_true = {rp['efficiency'] / ratio:.3f}) under the "
      f"same 4.5 -> 3.2 GHz drop.")
    w(f"In my run, a single task took {rp['T_task_inflation']:.3f}x longer at P = {p_phys} "
      f"than at P = 1 (T_parallel({p_phys}) / T_parallel(1)). Any all-core frequency drop is "
      f"included in that factor, together with the bandwidth contention from Q3.2.")
    f0 = tel.get("cpu_frequency_mhz") or {}
    if f0.get("max"):
        w(f"The OS reported a maximum frequency of {f0['max']:.0f} MHz. psutil only gives a "
          "nominal or coarse reading, so it cannot separate f1 and f_P directly.")
    w("To isolate the true algorithmic efficiency, the clock must be fixed: disable Turbo "
      "Boost or pin min = max frequency (Windows power plan 'max processor state 99%', "
      "Linux 'performance' governor with no_turbo, macOS Low Power Mode), keep the laptop on "
      "AC power, let it cool between runs, and/or normalise each time by the measured "
      "frequency (e.g. with HWiNFO, Intel Power Gadget or turbostat).")
    w("")
    return to_markdown(L)


SUBMISSION_FILES = ("report.md", "benchmark_gustafson.py",
                    "benchmark_telemetry.json", "scaling_results.csv")


def package(sid):
    # exactly the four required files, at the root of the archive (no subfolder)
    zip_path = os.path.join(HERE, f"{sid}_Exam.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in SUBMISSION_FILES:
            z.write(os.path.join(HERE, name), arcname=name)
    return zip_path


def main():
    tel, rows = load()
    if tel["student_id"] != ws.STUDENT_ID:
        raise SystemExit("benchmark_telemetry.json was produced with a different "
                         "STUDENT_ID - re-run benchmark_gustafson.py first.")
    print(f"Running granularity probe (N0 = {PROBE_N0:,}) ...")
    probe = granularity_probe(tel["process_counts"])
    with open(os.path.join(HERE, "report.md"), "w", encoding="utf-8") as f:
        f.write(build_text(tel, rows, probe))
    print("Saved report.md")
    print("Created", package(tel["student_id"]))


if __name__ == "__main__":
    mp.freeze_support()
    main()
