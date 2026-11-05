# weak_scaling.py
# Weak-scaling (Gustafson-Barsis) benchmark harness for a memory-intensive
# weighted rational kernel reduction, using multiprocessing.Pool.
#
# Outputs (written next to this script):
#   telemetry.json         - hardware / software profile of the machine
#   benchmark_results.csv  - raw timings, speedup, serial fraction per P
#
# Usage:  python weak_scaling.py

import os, sys, time, platform, json, csv
import multiprocessing as mp
import subprocess
import statistics
import numpy as np

STUDENT_ID = 240103177  # Paste your Student ID as a pure integer

N0 = 800000 + (STUDENT_ID % 25) * 40000
K1 = (STUDENT_ID % 8) + 2
K2 = ((STUDENT_ID // 10) % 6) + 3

REPEATS = 10         # timed repetitions per measurement (median is reported)
MAX_PHYS = 16        # P_phys is capped at 16 as required by the specification
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def compute_chunk(seed_offset, chunk_size, k1, k2):
    data = np.linspace(seed_offset, seed_offset + 2.0, chunk_size, dtype=np.float64)
    weights = np.sqrt(np.abs(data * k1) + 1.0)
    kernel_val = 1.0 / (1.0 + (data / k2)**2)
    return float(np.sum(weights * kernel_val))


# --------------------------------------------------------------------------
# 1. Hardware telemetry
# --------------------------------------------------------------------------
def _run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except Exception:
        return ""


def cpu_model_name():
    """Human-readable processor / microarchitecture string for any OS."""
    try:
        import cpuinfo  # optional: pip install py-cpuinfo
        brand = cpuinfo.get_cpu_info().get("brand_raw")
        if brand:
            return brand
    except Exception:
        pass
    system = platform.system()
    if system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    elif system == "Darwin":
        name = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if name:
            return name
    elif system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except Exception:
            pass
    return platform.processor() or "unknown"


def physical_core_count():
    try:
        import psutil  # optional: pip install psutil
        n = psutil.cpu_count(logical=False)
        if n:
            return n
    except Exception:
        pass
    system = platform.system()
    if system == "Linux":
        try:
            cores = set()
            phys = core = None
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("physical id"):
                        phys = line.split(":")[1].strip()
                    elif line.startswith("core id"):
                        core = line.split(":")[1].strip()
                    elif not line.strip():
                        if core is not None:
                            cores.add((phys, core))
                        phys = core = None
            if core is not None:
                cores.add((phys, core))
            if cores:
                return len(cores)
        except OSError:
            pass
    elif system == "Darwin":
        n = _run(["sysctl", "-n", "hw.physicalcpu"])
        if n.isdigit():
            return int(n)
    elif system == "Windows":
        n = _run(["powershell", "-NoProfile", "-Command",
                  "(Get-CimInstance Win32_Processor | "
                  "Measure-Object -Property NumberOfCores -Sum).Sum"])
        if n.isdigit():
            return int(n)
    return os.cpu_count() or 1


def cpu_frequency_mhz():
    try:
        import psutil
        f = psutil.cpu_freq()
        if f:
            return {"current": round(f.current, 1), "min": round(f.min, 1),
                    "max": round(f.max, 1)}
    except Exception:
        pass
    return None


def cache_sizes():
    """L1d / L2 / L3 sizes (best effort, values as reported by the OS)."""
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        caches = {k: info[k] for k in ("l1_data_cache_size", "l2_cache_size",
                                       "l3_cache_size") if info.get(k)}
        if caches:
            return caches
    except Exception:
        pass
    system = platform.system()
    caches = {}
    if system == "Linux":
        base = "/sys/devices/system/cpu/cpu0/cache"
        try:
            for idx in sorted(os.listdir(base)):
                d = os.path.join(base, idx)
                try:
                    with open(os.path.join(d, "level")) as f:
                        level = f.read().strip()
                    with open(os.path.join(d, "type")) as f:
                        ctype = f.read().strip()
                    with open(os.path.join(d, "size")) as f:
                        size = f.read().strip()
                except OSError:
                    continue
                if ctype != "Instruction":
                    caches[f"L{level}{'d' if level == '1' else ''}_per_instance"] = size
        except OSError:
            pass
    elif system == "Darwin":
        for key, name in (("hw.l1dcachesize", "L1d"), ("hw.l2cachesize", "L2"),
                          ("hw.l3cachesize", "L3")):
            v = _run(["sysctl", "-n", key])
            if v.isdigit() and int(v) > 0:
                caches[name] = f"{int(v) // 1024}K"
    elif system == "Windows":
        v = _run(["powershell", "-NoProfile", "-Command",
                  "$c = Get-CimInstance Win32_Processor | Select-Object -First 1; "
                  "\"$($c.L2CacheSize) $($c.L3CacheSize)\""]).split()
        if len(v) == 2 and all(x.isdigit() for x in v):
            caches = {"L2_total": f"{v[0]}K", "L3_total": f"{v[1]}K"}
    return caches or None


def total_ram_gb():
    try:
        import psutil
        return round(psutil.virtual_memory().total / 1024**3, 2)
    except Exception:
        return None


def gather_telemetry():
    return {
        "student_id": STUDENT_ID,
        "os_platform": platform.platform(),
        "os_system": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "machine_architecture": platform.machine(),
        "processor_microarchitecture": cpu_model_name(),
        "processor_id_string": platform.processor(),
        "physical_cores": physical_core_count(),
        "logical_threads": os.cpu_count(),
        "cpu_frequency_mhz": cpu_frequency_mhz(),
        "cache_sizes": cache_sizes(),
        "total_ram_gb": total_ram_gb(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_build": sys.version,
        "numpy_version": np.__version__,
        "multiprocessing_start_method": mp.get_start_method(),
    }


# --------------------------------------------------------------------------
# 2-4. Benchmark: serial baseline vs. weak-scaling parallel pool
# --------------------------------------------------------------------------
def make_tasks(p):
    # task i works on its own N0-element sub-problem (offset i), so the total
    # problem volume grows as N(P) = P * N0 while per-task work stays fixed
    return [(float(i), N0, K1, K2) for i in range(p)]


def timed_run(pool, tasks):
    """Wall-clock time to push all tasks through the pool and gather results."""
    t0 = time.perf_counter()
    results = pool.starmap(compute_chunk, tasks, chunksize=1)
    t1 = time.perf_counter()
    return t1 - t0, sum(results)


def measure(n_procs, tasks):
    """Median wall-clock time of `tasks` executed on a pool of n_procs workers.
    Pool start-up is excluded; one untimed warm-up run is done first so every
    worker has imported NumPy and touched its memory before timing starts."""
    with mp.Pool(processes=n_procs) as pool:
        pool.starmap(compute_chunk, make_tasks(n_procs), chunksize=1)  # warm-up
        times, checksum = [], None
        for _ in range(REPEATS):
            t, checksum = timed_run(pool, tasks)
            times.append(t)
    return statistics.median(times), min(times), checksum


def process_counts(p_phys):
    return sorted({1, 2, 4, p_phys, 2 * p_phys})


def main():
    telemetry = gather_telemetry()
    p_phys = min(telemetry["physical_cores"], MAX_PHYS)
    counts = process_counts(p_phys)
    telemetry["p_phys_used"] = p_phys
    telemetry["process_counts"] = counts
    telemetry["benchmark_parameters"] = {
        "N0": N0, "K1": K1, "K2": K2, "repeats": REPEATS,
        "timing_statistic": "median of repeats (pool start-up excluded)",
        "serial_baseline": "Pool(1) executing all P tasks sequentially",
    }

    print(f"Student ID {STUDENT_ID}:  N0={N0:,}  K1={K1}  K2={K2}")
    print(f"CPU: {telemetry['processor_microarchitecture']}")
    print(f"Physical cores={telemetry['physical_cores']}  "
          f"logical threads={telemetry['logical_threads']}  P = {counts}\n")

    rows = []
    t_par_1 = None
    for p in counts:
        tasks = make_tasks(p)
        t_par, t_par_min, chk_par = measure(p, tasks)
        if p == 1:
            # with P = 1 "one process running all P tasks" is the same
            # experiment as the parallel run, so the same timing is reused
            t_ser, chk_ser = t_par, chk_par
            t_par_1 = t_par
        else:
            t_ser, _, chk_ser = measure(1, tasks)
        speedup = t_ser / t_par
        s_emp = (p - speedup) / (p - 1) if p > 1 else None
        mem_mb = p * N0 * 8 * 3 / 1024**2
        rows.append({
            "P": p,
            "total_elements": p * N0,
            "T_parallel_s": round(t_par, 6),
            "T_serial_s": round(t_ser, 6),
            "speedup": round(speedup, 4),
            "s_emp": "N/A" if s_emp is None else round(s_emp, 4),
            "efficiency": round(speedup / p, 4),
            "memory_MB": round(mem_mb, 2),
            "throughput_GBps": round(mem_mb / 1024 / t_par, 3),
            "T_parallel_min_s": round(t_par_min, 6),
            "T_task_inflation": round(t_par / t_par_1, 4),
            "checksum_match": abs(chk_par - chk_ser) <= 1e-9 * abs(chk_ser),
            "checksum": f"{chk_par:.6f}",
        })
        r = rows[-1]
        print(f"P={p:>2}  N={p * N0:>11,}  T_par={t_par:.4f}s  "
              f"T_ser={t_ser:.4f}s  S={speedup:.3f}  s_emp={r['s_emp']}")

    telemetry["cpu_frequency_mhz_after_run"] = cpu_frequency_mhz()
    telemetry["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # ----------------------------------------------------------------------
    # 5. Export artifacts
    # ----------------------------------------------------------------------
    with open(os.path.join(OUT_DIR, "telemetry.json"), "w") as f:
        json.dump(telemetry, f, indent=2)
    with open(os.path.join(OUT_DIR, "benchmark_results.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("\nSaved telemetry.json and benchmark_results.csv to", OUT_DIR)


if __name__ == "__main__":
    mp.freeze_support()
    main()
