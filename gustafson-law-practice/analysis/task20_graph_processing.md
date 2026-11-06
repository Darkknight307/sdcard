# Task 20: Parallel Graph Traversal and Irregular Workloads

## 1. Why dense linear algebra weak-scales well

Dense kernels (GEMM, LU, stencils) have four properties that line up with
Gustafson's assumptions:

1. **Predictable, uniform work:** every block of the matrix costs the same.
2. **High arithmetic intensity:** `O(N³)` flops on `O(N²)` data, so computation
   hides communication.
3. **Regular, local communication:** the data each rank needs is known ahead of
   time (nearest neighbours, block rows and columns).
4. **Contiguous memory access:** cache- and prefetch-friendly, near peak
   bandwidth.

Under weak scaling the per-rank work and communication stay roughly constant, so
α is small and stable.

## 2. Why graph analytics violates every one of these

Take BFS and PageRank on **power-law (scale-free)** graphs such as social
networks, web graphs or Graph500 Kronecker graphs, where degree follows
`P(d) ∝ d^{−γ}`, `2 < γ < 3`.

### 2.1 Frontier imbalance (BFS)

* BFS proceeds level by level. The frontier size per level varies by orders of
  magnitude: a few vertices, then millions at the "peak" level, then a few again.
* Level-synchronous BFS needs a **global barrier per level**. The diameter of a
  small-world graph grows only like `O(log N)`, but each level's cost is set by
  the **most loaded rank**.
* **Hubs:** a few vertices have degree `O(N^{1/(γ−1)})`. The rank that owns a hub
  must scan or send huge adjacency lists, while other ranks idle. Weak scaling
  (more vertices per rank, more ranks) makes the largest hub **bigger**, so the
  imbalance grows with P.

### 2.2 Irregular memory access

* Visiting neighbours means random reads of `visited[]` and `rank[]` arrays.
  Arithmetic intensity is about 1 operation per 8–16 bytes, and access is random.
  Performance is bound by memory **latency**, not bandwidth or flops.
* The cache miss rate approaches 100% once the graph exceeds the LLC. Weak scaling
  increases total graph size, so per-node performance does not improve with more
  nodes the way it can for dense kernels (no cache-capacity bonus).

### 2.3 Communication volume and pattern

* With 1D partitioning, a large fraction of edges crosses partitions. For random
  partitions of a power-law graph the fraction of cut edges is about
  `1 − 1/P → 1`. Nearly **all** edge traversals become messages.
* The pattern is **all-to-all and data-dependent**. It is unknown until the
  frontier is computed, so it cannot be scheduled or overlapped statically.
* Bisection bandwidth of real networks grows more slowly than P (fat-tree taper,
  torus `P^{2/3}`), while all-to-all volume grows like `P`. Per-rank communication
  time therefore **grows** under weak scaling.

### 2.4 Data-dependent synchronisation

* **PageRank:** each iteration is a sparse matrix-vector product (SpMV) followed
  by a global convergence check (allreduce, `O(log P)`). The iteration count
  depends on the graph's spectral gap, not on P, but every iteration pays the
  irregular all-to-all exchange.
* **BFS:** the number of barriers equals the graph diameter, which grows like
  `log N`, so the barrier cost grows as `log N · log P`.

### 2.5 Partitioning cost

Good partitions (METIS, 2D edge partitioning, vertex-cut) reduce communication,
but they are themselves expensive (often costlier than one traversal). They also
partition hubs poorly. This adds a serial or poorly scaling pre-processing phase
whose cost grows with the problem.

## 3. Mapping to Gustafson's model

| Assumption | Dense LA | Graph analytics |
|---|---|---|
| Constant work per processor | ✔ | ✘ (hubs, frontier spikes) |
| Constant α | ✔ | ✘ (barriers × levels; imbalance grows with P) |
| Communication independent of P | ≈ ✔ (local) | ✘ (all-to-all, cut fraction → 1) |
| Time per unit work constant | ✔ (compute-bound) | ✘ (latency-bound, random access) |

Effective model: `T(P) = T_local + C_a2a(P) + L(P)·(t_barrier log P) + I(P)`,
with an all-to-all term `C_a2a ∝ P/bisection(P)`, `L ∝ log N` levels, and an
imbalance term `I(P)` that grows with the maximum degree. α_eff therefore rises
with P.

Empirically, Graph500 BFS rates (TEPS) per node fall steadily with node count,
whereas HPL (dense LU) achieves about 70–90% of peak at full system scale.

## 4. Mitigations

1. **2D (edge) partitioning:** limits each rank's communication to `√P` peers.
2. **Direction-optimising BFS** (Beamer et al.): switches from top-down to
   bottom-up at frontier peaks, which cuts edge checks by about 10×.
3. **Hub replication or delegation** (vertex-cut, PowerGraph): splits high-degree
   vertices across ranks.
4. **Asynchronous or relaxed algorithms** (async PageRank, Δ-stepping SSSP):
   remove per-level barriers.
5. **Message aggregation and compression:** batches small irregular messages to
   amortise latency.
6. **Locality-improving reordering** (RCM, Gorder): increases cache hit rates.

## 5. Conclusion

Gustafson's law presumes that growing the problem with P keeps the work per
processor, and its cost, constant. For power-law graphs, growing the graph makes
the hubs bigger, the cut fraction larger, communication more global and memory
access more random. The effective serial fraction therefore rises with P. That is
why weak scaling is notoriously hard for graph analytics but routine for
regular dense linear algebra.
