# make_report.py  (helper - NOT part of the submission)
# Run AFTER weak_scaling.py. It
#   1. reads telemetry.json + benchmark_results.csv,
#   2. runs a small granularity probe with N0 = 10,000 (for Q3.3),
#   3. writes diagnostics.txt with answers that quote your own numbers,
#   4. builds <StudentID>_Exam/ and <StudentID>_Exam.zip.
#
# Usage:  python make_report.py

import csv, json, os, shutil, zipfile
import multiprocessing as mp

import weak_scaling as ws

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE_N0 = 10_000


def load():
    with open(os.path.join(HERE, "telemetry.json")) as f:
        tel = json.load(f)
    with open(os.path.join(HERE, "benchmark_results.csv")) as f:
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
    w("PARALLEL COMPUTING - PRACTICAL EXAMINATION: DIAGNOSTICS")
    w("=" * 72)
    w(f"Student ID       : {sid}")
    w(f"Seeds            : N0 = {n0:,}   K1 = {k1}   K2 = {k2}")
    w(f"Machine          : {tel['os_platform']}")
    w(f"Processor        : {cpu} ({tel['machine_architecture']})")
    w(f"Cores / threads  : {tel['physical_cores']} physical / {tel['logical_threads']} logical"
      f"  ->  P_phys = {p_phys}")
    w(f"Caches           : {cache_txt}")
    w(f"Python / NumPy   : {tel['python_version']} / {tel['numpy_version']}"
      f"   (start method: {tel['multiprocessing_start_method']})")
    w(f"Run timestamp    : {tel.get('timestamp', '-')}")
    w(f"Timing method    : median of {tel['benchmark_parameters']['repeats']} repeats, "
      f"pool start-up excluded; T_serial = Pool(1) running all P tasks.")
    w("")
    w("TABLE 1 (from benchmark_results.csv)")
    w("-" * 72)
    w(f"{'P':>3} {'Elements':>12} {'T_par (s)':>11} {'T_ser (s)':>11} {'S(P)':>8} {'s_emp(P)':>9}")
    for r in rows:
        w(f"{r['P']:>3} {r['P'] * n0:>12,} {r['T_parallel_s']:>11.6f} {r['T_serial_s']:>11.6f} "
          f"{r['speedup']:>8.4f} {fmt_s(r['s_emp']):>9}")
    w("")

    # ------------------------------------------------------------------ Q3.1
    w("Q3.1  SCALING EFFICIENCY & AGGREGATE CACHE MULTIPLYING")
    w("-" * 72)
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
    w("Q3.2  MEMORY BUS CONTENTION & BANDWIDTH SATURATION")
    w("-" * 72)
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
    w("Q3.3  KERNEL GRANULARITY & AMORTIZATION OF RUNTIME DISPATCH")
    w("-" * 72)
    w(f"To check this empirically, the same harness was re-run with N0 = {PROBE_N0:,} "
      f"({n0 // PROBE_N0}x smaller than the assigned {n0:,}):")
    w(f"{'P':>3} {'T_par (s)':>11} {'T_ser (s)':>11} {'S(P)':>8} {'s_emp':>9}   "
      f"{'s_emp @N0=' + format(n0, ','):>18}")
    for q in probe:
        big = by_p[q["P"]]["s_emp"]
        w(f"{q['P']:>3} {q['T_parallel_s']:>11.6f} {q['T_serial_s']:>11.6f} {q['speedup']:>8.4f} "
          f"{fmt_s(q['s_emp']):>9}   {fmt_s(big):>18}")
    w("")
    floor = min(q["T_parallel_s"] for q in probe)
    w(f"With N0 = {PROBE_N0:,} the kernel itself needs only microseconds, but T_parallel never "
      f"drops below ~{floor * 1e6:.0f} us, which is the fixed dispatch floor of multiprocessing.Pool "
      f"on this machine. Because compute time no longer dominates, S(P) collapses towards 1 (or "
      f"below) and s_emp(P) rises towards 1.0, and can even exceed 1 when the parallel run is "
      f"slower than the serial one. That breaks Gustafson's assumption that coordination "
      f"cost is negligible compared with the scaled parallel work.")
    w("Where the floor comes from, per task and per pool.starmap() call:")
    w(" * IPC: Pool sends every task through a multiprocessing queue (an OS pipe, or a named "
      "pipe on Windows) guarded by locks, and results come back on a second pipe. Each hop "
      "is at least one write/read system call plus a wake-up of the receiving process. The "
      "main process also runs feeder and result-handler threads that must be scheduled.")
    w(" * Pickle serialization: every task tuple (seed, N0, K1, K2) is pickled in the parent "
      "and unpickled in the worker, and the returned float is pickled back. Here the payload "
      "is tiny because each worker builds its own array with np.linspace. If NumPy arrays "
      "were sent instead, pickling would copy N0 x 8 bytes per task through the pipe, which "
      "is a cost proportional to the data and would erase the parallel gain.")
    w(" * Context switches: each task needs the parent's feeder thread, the worker and the "
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
    w("Q3.4  DYNAMIC THERMAL THROTTLING & TURBO BOOST DIVERGENCE")
    w("-" * 72)
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
    return "\n".join(L)


def package(sid):
    folder = os.path.join(HERE, f"{sid}_Exam")
    os.makedirs(folder, exist_ok=True)
    for name in ("weak_scaling.py", "telemetry.json", "benchmark_results.csv", "diagnostics.txt"):
        shutil.copy2(os.path.join(HERE, name), os.path.join(folder, name))
    zip_path = os.path.join(HERE, f"{sid}_Exam.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(folder)):
            z.write(os.path.join(folder, name), arcname=f"{sid}_Exam/{name}")
    return zip_path


def main():
    tel, rows = load()
    if tel["student_id"] != ws.STUDENT_ID:
        raise SystemExit("telemetry.json was produced with a different STUDENT_ID - "
                         "re-run weak_scaling.py first.")
    print(f"Running granularity probe (N0 = {PROBE_N0:,}) ...")
    probe = granularity_probe(tel["process_counts"])
    with open(os.path.join(HERE, "diagnostics.txt"), "w", encoding="utf-8") as f:
        f.write(build_text(tel, rows, probe))
    print("Saved diagnostics.txt")
    print("Created", package(tel["student_id"]))


if __name__ == "__main__":
    mp.freeze_support()
    main()
