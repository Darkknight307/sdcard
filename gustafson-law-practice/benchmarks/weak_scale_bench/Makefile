CC      ?= gcc
CFLAGS  ?= -O2 -fopenmp
LDLIBS  ?= -lm
K       ?= 200000000
RUNS    ?= 5
THREADS ?=

weak_scale_bench: weak_scale_bench.c
	$(CC) $(CFLAGS) -o $@ $< $(LDLIBS)

run: weak_scale_bench
	./weak_scale_bench $(K) $(RUNS) $(THREADS) > ../results.csv

clean:
	rm -f weak_scale_bench

.PHONY: run clean
