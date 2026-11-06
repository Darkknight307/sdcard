/*
 * weak_scale_bench.c - OpenMP weak-scaling benchmark (Gustafson's law).
 *
 * Workload: midpoint-rule integration of f(x) = 4 / (1 + x^2) on [0, 1]
 * (exact value pi). Each thread integrates its own K-point sub-interval, so the
 * total problem size is N(P) = P * K and the work per thread is constant.
 *
 * Build:   gcc -O2 -fopenmp -o weak_scale_bench weak_scale_bench.c -lm
 *          (macOS / Apple clang: brew install libomp, then
 *           clang -O2 -Xpreprocessor -fopenmp -I$(brew --prefix libomp)/include \
 *                 -L$(brew --prefix libomp)/lib -lomp -o weak_scale_bench weak_scale_bench.c)
 * Run:     ./weak_scale_bench [K_per_thread] [runs] [threads...] > ../results.csv
 *          e.g. ./weak_scale_bench 200000000 5 1 2 3 4 6 8
 *
 * Output (CSV on stdout): P,run,time_s,points_per_thread,total_points,pi_estimate,abs_error
 */
#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

static double integrate_slice(long long start, long long count, double h) {
    double sum = 0.0;
    for (long long i = start; i < start + count; i++) {
        double x = (i + 0.5) * h;
        sum += 4.0 / (1.0 + x * x);
    }
    return sum;
}

static double run_once(int p, long long k, double *pi_out) {
    long long n = (long long)p * k;
    double h = 1.0 / (double)n;
    double total = 0.0;
    omp_set_num_threads(p);
    double t0 = omp_get_wtime();
#pragma omp parallel reduction(+ : total)
    {
        int id = omp_get_thread_num();
        total += integrate_slice((long long)id * k, k, h);
    }
    double t1 = omp_get_wtime();
    *pi_out = total * h;
    return t1 - t0;
}

int main(int argc, char **argv) {
    long long k = argc > 1 ? atoll(argv[1]) : 200000000LL;
    int runs = argc > 2 ? atoi(argv[2]) : 5;
    int maxp = omp_get_num_procs();
    int counts[64], nc = 0;
    if (argc > 3) {
        for (int i = 3; i < argc && nc < 64; i++) counts[nc++] = atoi(argv[i]);
    } else {
        for (int p = 1; p <= maxp && nc < 64; p++) counts[nc++] = p;
    }
    fprintf(stderr, "# hardware concurrency = %d, K = %lld points/thread, %d runs\n",
            maxp, k, runs);
    printf("P,run,time_s,points_per_thread,total_points,pi_estimate,abs_error\n");
    double pi;
    run_once(1, k / 10 > 0 ? k / 10 : 1, &pi); /* warm-up: page in, spin up clocks */
    for (int c = 0; c < nc; c++) {
        int p = counts[c];
        for (int r = 1; r <= runs; r++) {
            double t = run_once(p, k, &pi);
            printf("%d,%d,%.6f,%lld,%lld,%.12f,%.3e\n", p, r, t, k, (long long)p * k, pi,
                   fabs(pi - M_PI));
            fflush(stdout);
            fprintf(stderr, "P=%2d run=%d  T=%.4f s  pi=%.10f\n", p, r, t, pi);
        }
    }
    return 0;
}
