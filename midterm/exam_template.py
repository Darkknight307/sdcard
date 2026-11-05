# ==============================================================================
# MIDTERM PRACTICAL EXAMINATION: PARALLEL COMPUTING
# Topic: Karp–Flatt Metric & Empirical Overhead Profiling
# Total Marks: 50
# Instructor: Sufyan bin Uzayr
#
# SUBMISSION INSTRUCTIONS:
# 1. Enter your integer Student ID in PART 0.
# 2. Complete the required implementations in PART 1 and PART 2.
# 3. Execute this file on your local machine to collect empirical benchmarking data.
# 4. Fill in your diagnostic answers directly in the multiline strings in PART 4.
# 5. Submit ONLY this completed .py file to Moodle: <YourStudentID>_exam.py
# ==============================================================================



import os
import sys
import time
import platform
import json
import multiprocessing as mp
import numpy as np


# ==============================================================================
# PART 0: STUDENT IDENTITY & DETERMINISTIC SEED INITIALIZATION (Pass/Fail Gate)
# ==============================================================================
# Enter your student ID as a pure integer (e.g., 2493129439, 210103042, etc.)
STUDENT_ID = 0  # TODO: Replace with your actual Student ID

def compute_seeds(student_id: int):
    """
    Computes deterministic seeds using direct integer modulo arithmetic.
    Do NOT modify these formulas.
    """
    if student_id <= 0:
        raise ValueError("Please set STUDENT_ID to your valid student ID number.")
    
    k1 = (student_id % 8) + 2                     # Range: [2, 9]
    k2 = ((student_id // 10) % 6) + 3             # Range: [3, 8]
    n0 = 1_800_000 + (student_id % 25) * 60_000   # Range: [1,800,000 - 3,240,000]
    return k1, k2, n0


# ==============================================================================
# PART 1: KERNEL IMPLEMENTATION (15 Marks)
# ==============================================================================
# Kernel: Chebyshev Polynomial Transformation with Exponential Damping
# For slice index range [start_idx, start_idx + count):
# Compute: sum( (2.0 * x^2 - 1.0 + K1 * x^3) * exp(-abs(x) / K2) ) * dx
# where dx = 1.0 / total_elements, x = i * dx

def worker_kernel(start_idx: int, count: int, total_elements: int, k1: int, k2: int) -> float:
    """
    TODO: Implement the numeric worker kernel.
    Requirements:
    1. Allocate coordinate array x using np.float64 precision.
    2. Compute the element-wise Chebyshev-damped polynomial:
       values = (2.0 * (x ** 2) - 1.0 + k1 * (x ** 3)) * np.exp(-np.abs(x) / k2)
    3. Return the sum of values multiplied by dx (as a float).
    """
    # --- YOUR CODE STARTS HERE (approx. 4-6 lines) ---
    dx = 1.0 / total_elements
    indices = np.arange(start_idx, start_idx + count, dtype=np.float64)
    x = indices * dx
    values = (2.0 * (x ** 2) - 1.0 + k1 * (x ** 3)) * np.exp(-np.abs(x) / k2)
    return float(np.sum(values) * dx)
    # --- YOUR CODE ENDS HERE ---


# ==============================================================================
# PART 2: PARALLEL HARNESS & KARP-FLATT ENGINE (15 Marks)
# ==============================================================================
# The Karp-Flatt Metric evaluates the experimentally observed parallel overhead:
#
#     e = ( (1 / S) - (1 / p) ) / ( 1 - (1 / p) )
#
# where:
#     p = number of concurrent worker processes (p >= 2)
#     S = speedup = T_serial / T_parallel(p)
#
# Under strong scaling (fixed total work N0), if e remains constant as p grows,
# parallel efficiency loss is strictly caused by the serial portion of the code.
# If e increases as p grows, efficiency loss is driven by parallel overheads
# (process contention, IPC, cache thrashing, memory bus saturation).

def calculate_karp_flatt(speedup: float, p: int) -> float:
    """
    TODO: Compute the Karp-Flatt metric e for a given speedup S and process count p.
    For p == 1, return 0.0 (by definition).
    For p >= 2, return ((1.0 / speedup) - (1.0 / p)) / (1.0 - (1.0 / p)).
    """
    if p <= 1:
        return 0.0
    return ((1.0 / speedup) - (1.0 / p)) / (1.0 - (1.0 / p))


def run_benchmark():
    """
    Runs the empirical benchmark across core allocations and computes metrics.
    """
    k1, k2, n0 = compute_seeds(STUDENT_ID)
    
    # Target thread counts: 1, 2, 4, physical cores, and logical cores
    logical_cores = os.cpu_count() or 4
    phys_cores = max(1, logical_cores // 2)
    
    p_candidates = sorted(list(set([1, 2, 4, phys_cores, logical_cores])))
    p_levels = [p for p in p_candidates if p <= 16]
    
    print(f"==================================================================")
    print(f"Executing Karp-Flatt Benchmark | Student ID: {STUDENT_ID}")
    print(f"Seeds: K1={k1}, K2={k2}, Fixed Workload N0={n0:,}")
    print(f"Host Hardware: {platform.processor()} | Logical Cores: {logical_cores}")
    print(f"==================================================================")
    
    # 1. Establish Baseline Serial Execution Time (P=1)
    print("[*] Timing single-process baseline T(1)...")
    t0 = time.perf_counter()
    res_base = worker_kernel(0, n0, n0, k1, k2)
    t1 = time.perf_counter() - t0
    print(f"    T(1) baseline = {t1:.4f} seconds | Integral check = {res_base:.6f}\n")
    
    results = []
    
    for p in p_levels:
        # Divide fixed workload N0 into p non-overlapping chunks
        chunk_size = n0 // p
        remainder = n0 % p
        
        tasks = []
        curr_start = 0
        for i in range(p):
            allocated = chunk_size + (1 if i < remainder else 0)
            tasks.append((curr_start, allocated, n0, k1, k2))
            curr_start += allocated
            
        # Benchmark Parallel Execution Time T(p)
        t_start = time.perf_counter()
        with mp.Pool(processes=p) as pool:
            partial_results = pool.starmap(worker_kernel, tasks)
            total_sum = sum(partial_results)
        t_p = time.perf_counter() - t_start
        
        # Verify numeric consistency (avoid broken implementations)
        assert abs(total_sum - res_base) < 1e-4, f"Integrity error at P={p}: partial sums do not match."
        
        speedup = t1 / t_p
        e_metric = calculate_karp_flatt(speedup, p)
        
        results.append({
            "p": p,
            "t_p_sec": round(t_p, 4),
            "speedup": round(speedup, 4),
            "karp_flatt_e": round(e_metric, 4)
        })
        
        print(f"P = {p:2d} | T(P) = {t_p:7.4f}s | Speedup = {speedup:6.3f}x | Karp-Flatt e = {e_metric:8.4f}")
        
    return results


# ==============================================================================
# PART 3: HARDWARE DIAGNOSTICS & SYSTEM TELEMETRY (Pass/Fail Gate)
# ==============================================================================
def collect_telemetry():
    """Captures execution environment metadata to cross-verify physical runs."""
    return {
        "student_id": STUDENT_ID,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": sys.version.split()[0],
        "cpu_count_logical": os.cpu_count(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }


# ==============================================================================
# PART 4: TECHNICAL DIAGNOSTICS & ANALYSIS (20 Marks: 4 x 5 Marks)
# ==============================================================================
# Read your printed benchmark results table and answer the following 4 questions.
# Write your analysis directly inside the multiline strings below.
# Be concrete and refer to your measured numbers (P, T(P), Speedup, and e).

ANALYSIS_Q1 = """
[Problem 4.1: Karp-Flatt Metric Growth vs Fixed Serial Bottleneck - 5 Marks]
In Amdahl's ideal model, the serial fraction s is assumed strictly invariant with respect to P.
- In your experimental data, how does e change as P increases from 2 to your maximum core count?
- If e increases with P, what does this mathematically prove regarding whether execution time 
  loss is caused by a fixed serial code section or by growing inter-process coordination 
  and scheduling overhead? Cite your measured e values to support your conclusion.

YOUR ANSWER:

"""

ANALYSIS_Q2 = """
[Problem 4.2: FPU Contention on Simultaneous Multithreading (SMT) - 5 Marks]
Examine the transition when P increases from physical core count to logical core count (SMT):
- What happens to measured Speedup S and the Karp-Flatt metric e at this boundary?
- Why do CPU hyperthreads (logical cores sharing one physical core) provide substantial throughput 
  gains for branch-heavy integer code, but stall or degrade on vectorized NumPy floating-point 
  arithmetic? Identify the physical hardware units that are duplicated vs shared on an SMT core.

YOUR ANSWER:

"""

ANALYSIS_Q3 = """
[Problem 4.3: Memory Bus Saturation & Working Set Dynamics - 5 Marks]
Calculate your per-worker and aggregate memory allocation:
- Each worker allocates array slices in float64 (8 bytes per element). Compute the total memory 
  footprint across all active workers when P = physical cores.
- Does this aggregate footprint fit within your CPU's L3 cache, or does it spill into main DDR RAM?
- How does memory controller bus bandwidth contention distort the apparent Karp-Flatt metric e?

YOUR ANSWER:

"""

ANALYSIS_Q4 = """
[Problem 4.4: Superlinear Speedup and Negative Karp-Flatt Metrics - 5 Marks]
- If an experimental run yields a negative Karp-Flatt metric (e < 0), what does that imply about 
  the observed speedup S relative to P? 
- Under what specific hardware cache-hierarchy condition can a real parallel program exhibit e < 0?
- In Python's multiprocessing architecture, why is e almost always strictly positive (e > 0) 
  at high core counts even if the mathematical kernel itself has zero serial code?

YOUR ANSWER:

"""


# ==============================================================================
# SELF-VALIDATION & SUBMISSION BUNDLE
# ==============================================================================
def run_all():
    if STUDENT_ID == 0:
        print("[!] ERROR: Set your STUDENT_ID in Part 0 before running.")
        return
        
    # Check that student answered the questions
    questions = [("Q1", ANALYSIS_Q1), ("Q2", ANALYSIS_Q2), ("Q3", ANALYSIS_Q3), ("Q4", ANALYSIS_Q4)]
    unanswered = [q_name for q_name, text in questions if len(text.strip().splitlines()) <= 8]
    
    telemetry = collect_telemetry()
    benchmark_data = run_benchmark()
    
    print("\n==================================================================")
    print("SUBMISSION STATUS CHECK:")
    print(f"Student ID       : {STUDENT_ID}")
    print(f"Telemetry Status : Captured successfully.")
    print(f"Benchmark Status : {len(benchmark_data)} data points collected.")
    if unanswered:
        print(f"Diagnostic Status: [WARNING] The following sections appear uncompleted: {unanswered}")
    else:
        print(f"Diagnostic Status: All 4 diagnostic sections populated.")
    print("==================================================================")
    print("[+] When finished, save this file and submit directly to Moodle.")

if __name__ == "__main__":
    run_all()
