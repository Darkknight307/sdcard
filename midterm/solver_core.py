
def ask_student_id():
    if len(sys.argv) > 1 and sys.argv[1].strip().isdigit():
        return int(sys.argv[1].strip())
    while True:
        s = input("Student ID: ").strip()
        if s.isdigit() and int(s) > 0:
            return int(s)
        print("Please type the Student ID as digits only.")


def ensure(pkg, module):
    if importlib.util.find_spec(module) is None:
        print(f"Installing {pkg} ...")
        subprocess.call([sys.executable, "-m", "pip", "install", "-q", pkg])


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def hardware_info():
    """Extra facts for the answers (physical cores, SMT, last-level cache)."""
    info = {"logical": os.cpu_count() or 1, "physical": None, "cpu": platform.processor(),
            "llc_bytes": None, "llc_name": None, "l2_bytes": None}
    system = platform.system()
    try:
        import psutil
        info["physical"] = psutil.cpu_count(logical=False)
    except Exception:
        pass
    try:
        import cpuinfo
        ci = cpuinfo.get_cpu_info()
        info["cpu"] = ci.get("brand_raw") or info["cpu"]
        for key, name in (("l3_cache_size", "L3"), ("l2_cache_size", "L2")):
            v = ci.get(key)
            if isinstance(v, int) and v > 0:
                if name == "L3":
                    info["llc_bytes"], info["llc_name"] = v, "L3"
                else:
                    info["l2_bytes"] = v
    except Exception:
        pass
    if system == "Darwin":
        brand = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if brand:
            info["cpu"] = brand
        if not info["physical"]:
            v = _run(["sysctl", "-n", "hw.physicalcpu"])
            info["physical"] = int(v) if v.isdigit() else None
        pcores = _run(["sysctl", "-n", "hw.perflevel0.physicalcpu"])
        ecores = _run(["sysctl", "-n", "hw.perflevel1.physicalcpu"])
        info["p_cores"] = int(pcores) if pcores.isdigit() else None
        info["e_cores"] = int(ecores) if ecores.isdigit() else None
        l3 = _run(["sysctl", "-n", "hw.l3cachesize"])
        if l3.isdigit() and int(l3) > 0:
            info["llc_bytes"], info["llc_name"] = int(l3), "L3"
        l2 = _run(["sysctl", "-n", "hw.perflevel0.l2cachesize"]) or _run(["sysctl", "-n", "hw.l2cachesize"])
        if l2.isdigit() and int(l2) > 0:
            info["l2_bytes"] = int(l2)
    elif system == "Linux":
        base = "/sys/devices/system/cpu/cpu0/cache"
        try:
            for idx in os.listdir(base):
                d = os.path.join(base, idx)
                lvl = open(os.path.join(d, "level")).read().strip()
                size = open(os.path.join(d, "size")).read().strip().upper()
                mult = 1024 * 1024 if size.endswith("M") else 1024
                b = int(size.rstrip("KM")) * mult
                if lvl == "3":
                    info["llc_bytes"], info["llc_name"] = b, "L3"
                elif lvl == "2":
                    info["l2_bytes"] = b
        except Exception:
            pass
        if not info["physical"]:
            cores = set()
            try:
                phys = None
                for line in open("/proc/cpuinfo"):
                    if line.startswith("physical id"):
                        phys = line.split(":")[1].strip()
                    elif line.startswith("core id"):
                        cores.add((phys, line.split(":")[1].strip()))
            except Exception:
                pass
            info["physical"] = len(cores) or None
    elif system == "Windows":
        v = _run(["powershell", "-NoProfile", "-Command",
                  "$c = Get-CimInstance Win32_Processor | Select-Object -First 1; "
                  "\"$($c.NumberOfCores) $($c.L2CacheSize) $($c.L3CacheSize) $($c.Name)\""])
        parts = v.split(None, 3)
        if len(parts) >= 3 and all(x.isdigit() for x in parts[:3]):
            info["physical"] = info["physical"] or int(parts[0])
            info["l2_bytes"] = info["l2_bytes"] or int(parts[1]) * 1024
            if int(parts[2]) > 0 and not info["llc_bytes"]:
                info["llc_bytes"], info["llc_name"] = int(parts[2]) * 1024, "L3"
            if len(parts) == 4:
                info["cpu"] = parts[3].strip()
    if not info["physical"]:
        info["physical"] = info["logical"]
    info["apple"] = "apple" in (info["cpu"] or "").lower() or (
        system == "Darwin" and platform.machine() == "arm64")
    if info["apple"] and not info["llc_bytes"]:
        # Apple Silicon has no classic L3; the shared L2 of the P-cluster is the
        # largest cache the CPU cores own (plus an SoC-wide system level cache).
        info["llc_bytes"], info["llc_name"] = info["l2_bytes"], "shared L2 (no L3 on Apple Silicon)"
    info["smt"] = info["logical"] > info["physical"]
    return info


def parse_output(text):
    t1 = float(re.search(r"T\(1\) baseline = ([0-9.]+) seconds", text).group(1))
    rows = []
    for m in re.finditer(r"P =\s*(\d+) \| T\(P\) =\s*([0-9.]+)s \| Speedup =\s*([0-9.]+)x "
                         r"\| Karp-Flatt e =\s*(-?[0-9.]+)", text):
        rows.append({"p": int(m.group(1)), "t": float(m.group(2)),
                     "s": float(m.group(3)), "e": float(m.group(4))})
    return t1, rows


def mb(b):
    return b / 1024 ** 2


def wrap(text):
    out = []
    for para in text.strip().split("\n"):
        if para.startswith("  ") or para.startswith("P ") or para.startswith("--"):
            out.append(para)
        else:
            out.extend(textwrap.wrap(para, 92) or [""])
    return "\n".join(out)


def answers(sid, t1, rows, hw):
    k1 = (sid % 8) + 2
    k2 = ((sid // 10) % 6) + 3
    n0 = 1_800_000 + (sid % 25) * 60_000
    by_p = {r["p"]: r for r in rows}
    logical = hw["logical"]
    phys_h = max(1, logical // 2)            # value used by the harness
    phys = hw["physical"]
    multi = [r for r in rows if r["p"] >= 2]
    pmax = max(r["p"] for r in rows)
    overhead = {r["p"]: r["t"] - t1 / r["p"] for r in rows}
    table = ["  P   T(P) [s]   Speedup S   Karp-Flatt e   overhead T(P)-T(1)/P [s]",
             "  --  ---------  ----------  -------------  -------------------------"]
    for r in rows:
        table.append(f"  {r['p']:<3} {r['t']:9.4f}  {r['s']:9.3f}x  {r['e']:13.4f}  "
                     f"{overhead[r['p']]:25.4f}")
    table_txt = "\n".join(table)

    # ------------------------------------------------------------------ Q1
    es = [r["e"] for r in multi]
    e_first, e_last = es[0], es[-1]
    rising = e_last > e_first + 0.02
    if rising:
        trend = (f"e rises from {e_first:.4f} at P = 2 to {e_last:.4f} at P = {pmax}, an increase "
                 f"of {e_last - e_first:+.4f}.")
    elif abs(e_last - e_first) <= 0.02:
        trend = (f"e stays almost flat, going from {e_first:.4f} at P = 2 to {e_last:.4f} at "
                 f"P = {pmax}.")
    else:
        trend = (f"e falls from {e_first:.4f} at P = 2 to {e_last:.4f} at P = {pmax}. That would "
                 "mean a fixed one-off cost is being amortised over more workers.")
    steps = ", ".join(f"e({r['p']}) = {r['e']:.4f}" for r in multi)
    slower = [r["p"] for r in rows if r["s"] < 1.0]
    q1 = f"""
Measured on {hw['cpu']} ({phys} physical / {logical} logical cores), Student ID {sid}:
K1 = {k1}, K2 = {k2}, N0 = {n0:,} (strong scaling: the total work is fixed).
Serial baseline T(1) = {t1:.4f} s (the kernel run in-process without a Pool).

{table_txt}

{steps}. {trend}
If the loss came only from a fixed serial code fraction s (Amdahl), then T(p) = T(1)(s + (1-s)/p)
and solving the Karp-Flatt formula would return the same e = s for every p. A value of e that
changes with p cannot be a constant serial fraction. In the measurement it grows, so the lost
time is a term that grows with p. Writing T(p) = T(1)/p + O(p), the extra time O(p) (last
column) is {overhead[2]:.4f} s at P = 2 and {overhead[pmax]:.4f} s at P = {pmax}. That rise
comes from the harness starting a new Pool inside the timed region: every run must create p
worker processes (fork/spawn plus re-importing NumPy), pickle p task tuples, pass them over
IPC pipes, schedule the workers and gather and sum the results. The kernel itself has no
serial part except the final sum of p floats, so the growing e proves the efficiency loss is
inter-process coordination and scheduling overhead, not a fixed serial code section.
""".strip()
    if slower:
        q1 += (f"\nFor P = {', '.join(map(str, slower))} the speedup is even below 1 "
               "(e > 1 for p >= 2): the overhead is larger than the whole computation it saves, "
               f"since T(1) is only {t1:.4f} s.")

    # ------------------------------------------------------------------ Q2
    rp, rl = by_p.get(phys_h), by_p.get(logical)
    if hw["smt"]:
        hw_line = (f"This CPU has SMT: {phys} physical cores expose {logical} logical CPUs "
                   f"({logical // phys} hardware threads per core).")
    elif hw["apple"]:
        pc, ec = hw.get("p_cores"), hw.get("e_cores")
        mix = f" ({pc} performance + {ec} efficiency cores)" if pc and ec else ""
        hw_line = (f"This Apple Silicon CPU has no SMT: {logical} logical CPUs = {phys} physical "
                   f"cores{mix}. The harness assumes phys = logical // 2 = {phys_h}, so the "
                   f"'physical to logical' step P = {phys_h} -> {logical} doesn't move onto "
                   "hyperthreads. It only adds more real cores, mostly the slower efficiency "
                   "cores, plus more process overhead.")
    else:
        hw_line = (f"This CPU reports {phys} physical and {logical} logical cores (no SMT). The "
                   f"harness assumes phys = logical // 2 = {phys_h}, so P = {logical} still "
                   "uses one real core per process.")
    if rp and rl and rp["p"] != rl["p"]:
        ds = rl["s"] - rp["s"]
        move = "rises only slightly" if 0 < ds < 0.15 * rp["s"] else ("drops" if ds <= 0 else "rises")
        edir = "increases" if rl["e"] > rp["e"] else "decreases"
        boundary = (f"At the boundary P = {rp['p']} -> {rl['p']} the speedup goes from "
                    f"{rp['s']:.3f}x to {rl['s']:.3f}x ({move}, change {ds:+.3f}). Karp-Flatt e "
                    f"{edir} from {rp['e']:.4f} to {rl['e']:.4f}, and T(P) goes from "
                    f"{rp['t']:.4f} s to {rl['t']:.4f} s. Doubling the process count does not "
                    "double the useful compute capacity, so S does not double, and the extra "
                    "start-up/IPC cost of the additional workers shows up as a higher e.")
    else:
        boundary = ("On this machine the physical and logical core counts give the same P, so "
                    "the boundary could not be measured separately.")
    q2 = f"""
{hw_line}
{boundary}
Why SMT helps integer code but not NumPy FP: two hardware threads on one core share almost all
of the execution resources. Only the architectural state is duplicated per thread: the
register file (general and vector registers), program counter, flags, return-stack buffer,
interrupt state (APIC) and part of the reorder buffer and load/store queues, which are
partitioned between the threads. Shared are the decoders and micro-op cache, the out-of-order
scheduler, the integer ALUs, the floating-point/SIMD FMA units and their issue ports, the
load/store units, the L1/L2 caches, the TLBs, the branch predictor and the path to memory.
Branch-heavy integer code (parsing, pointer chasing, dictionary lookups) leaves many issue
slots empty while waiting on branch mispredictions and cache misses, so a second thread can
fill those bubbles and gain 20-30% throughput. The vectorised NumPy kernel here (x**2, x**3,
np.exp, multiplies and the sum) is a long branch-free stream of SIMD floating-point
operations. One thread already keeps the core's FMA/vector ports and L1 load bandwidth busy,
so the sibling thread finds no idle unit and has to compete for the same FPU ports, L1/L2
capacity and memory bandwidth. Throughput per core stays flat or drops, S stalls and e rises.
""".strip()

    # ------------------------------------------------------------------ Q3
    p_use = phys if phys in by_p else phys_h
    per_worker_elems = n0 / p_use
    arr_worker = per_worker_elems * 8
    live = 5
    agg_one = n0 * 8
    agg_live = agg_one * live
    llc = hw.get("llc_bytes")
    llc_name = hw.get("llc_name") or "L3"
    if llc:
        fit_agg = agg_live <= llc
        cache_line = (f"The largest cache of this CPU is the {llc_name} = {mb(llc):.1f} MB. "
                      f"The aggregate footprint of about {mb(agg_live):.1f} MB is "
                      + (f"smaller, so most of it can stay on-chip." if fit_agg else
                         f"{agg_live / llc:.1f}x larger. Even a single array set "
                         f"({mb(agg_one):.1f} MB) "
                         + ("fits" if agg_one <= llc else "does not fit")
                         + ", so the working set spills into main DDR/LPDDR RAM and every "
                           "pass over x, x**2, x**3 and exp(...) streams through the memory "
                           "controller."))
    else:
        cache_line = (f"The OS did not report an L3 size. Laptop CPUs typically have 8-36 MB "
                      f"of last-level cache, so an aggregate footprint of about "
                      f"{mb(agg_live):.1f} MB spills into main RAM.")
    rpp = by_p.get(p_use)
    q3 = f"""
Strong scaling: the total N0 = {n0:,} elements is split, so each of the P = {p_use} workers
(physical cores) gets N0/P = {per_worker_elems:,.0f} elements.
One float64 slice per worker = {per_worker_elems:,.0f} x 8 B = {mb(arr_worker):.2f} MB.
All workers together, for one array = N0 x 8 B = {agg_one:,} B = {mb(agg_one):.2f} MB.
The kernel does not hold just one array. indices and x stay alive, and NumPy creates
temporaries for x**2, 2*x**2-1, x**3, k1*x**3, abs(x)/k2 and exp(...), so about {live} arrays
are live at the peak. Per worker that is about {live} x {mb(arr_worker):.2f} = {mb(arr_worker * live):.2f} MB,
and the aggregate is {live} x {mb(agg_one):.2f} MB = about {mb(agg_live):.1f} MB across the
{p_use} workers.
{cache_line}
How bandwidth contention distorts e: all cores share one memory controller with a fixed
bandwidth B. With one process the kernel gets the whole of B. With P processes each one gets
about B/P once their combined demand exceeds B, so every worker's slice takes longer than
T(1)/P, even though nothing serial was added. The Karp-Flatt formula attributes every second
of lost speedup to a 'serial fraction', so bus stalls are counted as serial code and e is
inflated. It grows with P because more cores fight for the same bandwidth.
""".strip()
    if rpp:
        q3 += (f" In my run e = {rpp['e']:.4f} at P = {p_use}. Part of that value is memory "
               "stall time, not serial work.")
    q3 += (" (The exp() call adds some arithmetic per element, so the kernel is not purely "
           "bandwidth-bound. This makes the distortion milder than for a pure copy loop, but "
           "it does not remove it.)")

    # ------------------------------------------------------------------ Q4
    neg = [r for r in multi if r["e"] < 0]
    if neg:
        meas = ("In my data e < 0 does occur at " +
                ", ".join(f"P = {r['p']} (S = {r['s']:.3f} > {r['p']})" for r in neg) +
                ". That is a genuine superlinear point (or timing noise of the same size).")
    else:
        meas = ("In my data every e is positive (" +
                ", ".join(f"{r['e']:.4f}" for r in multi) +
                "), so no superlinear speedup was observed.")
    q4 = f"""
e = (1/S - 1/p) / (1 - 1/p). The denominator is positive for p >= 2, so e < 0 exactly when
1/S < 1/p, that is S > p: superlinear speedup. The p workers together finished more than p
times faster than one core, so per core they were faster than the serial run.
Hardware condition: superlinear speedup happens when the working set does not fit in one
core's cache but each worker's slice does. When the data is split p ways, every slice can fit
in that core's private L1/L2 (or in the aggregate L3), so the cores hit in cache while the
serial run keeps missing to DRAM. The total cache capacity grows with p while the problem is
fixed. Here one array slice per worker is {mb(n0 * 8 / pmax):.2f} MB at P = {pmax}, so splitting
far enough can bring a slice down to private L2 size{f' ({mb(hw["l2_bytes"]):.1f} MB here)' if hw.get('l2_bytes') else ''}.
{meas}
Why e > 0 is almost guaranteed with Python multiprocessing, even with a kernel that has zero
serial code:
  1) Process creation is inside the timed region. mp.Pool(p) must fork/spawn p interpreters
     (spawn on macOS and Windows also re-imports NumPy), and that cost grows with p.
  2) Every task tuple and every result is pickled, sent through OS pipes, unpickled and
     handed over by the Pool's feeder and result-handler threads.
  3) The OS must schedule and context-switch the workers. When p exceeds the number of fast
     cores they share cores, and closing the pool joins and terminates every worker.
  4) The serial baseline T(1) runs in-process with none of these costs, so the comparison
     is not like for like.
  5) The memory controller and the all-core turbo frequency are shared, so per-core speed
     drops as p grows.
All of these add a positive time O(p) that grows with p. With T(p) = T(1)/p + O(p), any
O(p) > 0 gives S < p and therefore e > 0. Here O(p) went from {overhead[2]:.4f} s (P = 2) to
{overhead[pmax]:.4f} s (P = {pmax}), compared with only T(1) = {t1:.4f} s of real work.
""".strip()
    return [wrap(q1), wrap(q2), wrap(q3), wrap(q4)]


def fill(src, texts):
    parts = src.split("YOUR ANSWER:\n\n\"\"\"")
    assert len(parts) == 5, "template markers not found"
    out = parts[0]
    for i, t in enumerate(texts):
        t = t.replace('"""', "'''").replace("\\", "/")
        out += "YOUR ANSWER:\n" + t + "\n\"\"\"" + parts[i + 1]
    return out


def main():
    ensure("numpy", "numpy")
    ensure("psutil", "psutil")
    ensure("py-cpuinfo", "cpuinfo")
    sid = ask_student_id()
    out_dir = os.path.join(os.path.expanduser("~"), f"midterm_{sid}")
    os.makedirs(out_dir, exist_ok=True)
    exam_path = os.path.join(out_dir, f"{sid}_exam.py")
    src = TEMPLATE.replace("STUDENT_ID = 0  # TODO: Replace with your actual Student ID",
                           f"STUDENT_ID = {sid}  # Student ID")
    with open(exam_path, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"\n=== Running {sid}_exam.py on this machine ===\n")
    proc = subprocess.run([sys.executable, exam_path], cwd=out_dir,
                          capture_output=True, text=True)
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr)
        sys.exit("The benchmark failed - see the error above.")
    t1, rows = parse_output(proc.stdout)
    hw = hardware_info()

    final = fill(src, answers(sid, t1, rows, hw))
    with open(exam_path, "w", encoding="utf-8") as f:
        f.write(final)
    with open(os.path.join(out_dir, "benchmark_output.txt"), "w", encoding="utf-8") as f:
        f.write(proc.stdout)

    # sanity check: the completed file must compile and pass the self-check
    compile(final, exam_path, "exec")
    ns = {}
    exec(compile(final.split("if __name__ ==")[0], exam_path, "exec"), ns)
    empty = [q for q in ("ANALYSIS_Q1", "ANALYSIS_Q2", "ANALYSIS_Q3", "ANALYSIS_Q4")
             if len(ns[q].strip().splitlines()) <= 8]
    print("==================================================================")
    print(f"DONE. Answers written from the numbers above "
          f"({'all 4 sections populated' if not empty else 'MISSING: ' + str(empty)}).")
    print(f"Submit this single file to Moodle:\n  {exam_path}")
    print("==================================================================")
    try:
        if platform.system() == "Darwin":
            subprocess.call(["open", out_dir])
        elif platform.system() == "Windows":
            os.startfile(out_dir)
    except Exception:
        pass


if __name__ == "__main__":
    main()
