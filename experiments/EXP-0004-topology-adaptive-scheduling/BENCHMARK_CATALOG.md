# SynapticContinuum EXP-0004: Benchmark Catalog & Workload Registry

**Schema Version**: `1.0.0` ([schemas/benchmark_schema.json](schemas/benchmark_schema.json))  
**Document Status**: ACTIVE SPECIFICATION  
**Host Architecture (Current)**: Linux x86_64 (`lenobox`, AMD Ryzen 5 PRO 5650GE, 6C/12T, 16 MiB L3, 16 GB DDR4)  
**Host Architecture (Planned Follow-on)**: Apple Silicon M4 Pro (Darwin ARM64, 14-core [10P + 4E], 48 GB Unified Memory) — **MAC PENDING**  

---

## 1. Overview and Design Principles

The SynapticContinuum Benchmark Catalog standardizes benchmark configurations across experiments (EXP-0004, EXP-0005+), ensuring that performance claims across different engines, data representations, and hardware platforms share identical mathematical stimuli and graph definitions.

### Key Rules:
1. **Deterministic Benchmark ID**: `benchmark_id` is a canonical hash/slug uniquely encoding the workload parameters, graph generator, degree sequence, stimulus seed, and partition scheme.
2. **Explicit Semantic Classes**: Performance cannot be compared across different semantic classes:
   - `exact`: Bit-exact causal parity with serial continuous-time LIF reference (Digest match required).
   - `fixed-dt-approx`: Time-stepped approximation ($\Delta t$-discretized update).
   - `relaxed-model`: Bounded temporal order relaxation with parameter $\epsilon$ (no rollback).
   - `trace-replay-only`: Fixed trace dispatch microbenchmark isolating memory/cache dispatch without neural model updates.
3. **Machine Headroom Guardrails**:
   - On 16 GB Linux host: Strict preflight check ensuring peak memory $\le 60\%$ of currently available RAM (~6.5 GiB max).
   - On 48 GB macOS host: Workload ladder extends to $N = 10\text{M}$ and $30\text{M}$ with unified memory profiling.

---

## 2. Canonical Workload Registry

| Benchmark ID | Workload Description | Graph Topology | $N$ | Out-Degree $D$ | Active Fraction $f$ | Events Horizon | Semantic Class |
|---|---|---|---|---|---|---|---|
| `cfg_sw_n10k_d16_p001_s42` | Watts-Strogatz Small World | Small World ($p=0.01$) | 10,000 | 16 | 0.05 | 2,000 | `exact` |
| `cfg_mod_n100k_d16_c005_s777` | Modular SBM 100k | Modular SBM ($c=0.05$, 24 modules) | 100,000 | 16 | 0.01 | 20,000 | `exact` |
| `cfg_mod_n1m_d16_c005_s999` | Modular SBM 1M Sustained | Modular SBM ($c=0.05$, 48 modules) | 1,000,000 | 16 | 0.005 | $\ge 1,000,000$ | `exact` |
| `cfg_disc_n100k_d16_m6_s123` | Disconnected 6-Module Control | Disconnected ($c=0.0$) | 100,000 | 16 | 0.01 | 20,000 | `exact` |
| `cfg_celegans_multiplex_n279` | C. elegans Connectome | CoMuNeLab Multiplex Connectome | 279 | Empirical | 0.20 | 500 | `exact` |
| `cfg_relaxed_discrim_eps05` | Temporal Discrimination ($\epsilon$) | Sequence Discrimination ($A \to B$) | 128 | 8 | 0.10 | 1,000 | `relaxed-model` |

---

## 3. Querying the Benchmark Catalog & Pareto Frontier

A dedicated query CLI (`scripts/pareto_query.py`) allows subsequent experiments to inspect the catalog and extract Pareto-optimal configurations:

```bash
# Query all exact runs with memory <= 8 GiB and N >= 100k
python3 scripts/pareto_query.py --path runs --max-memory-gib 8.0 --min-nodes 100000 --semantic-class exact --pareto

# Output raw JSON for pipeline consumption
python3 scripts/pareto_query.py --path runs --topology modular --pareto --json
```

---

## 4. Mac Apple Silicon M4 Pro Handoff Guide (Darwin ARM64 PENDING)

When running on the 48 GB M4 Pro machine:
1. **Do not fabricate Mac results on Linux.** All Mac benchmark cells remain `PENDING`.
2. **Workload Compatibility**: Use identical canonical configuration files from `configs/`.
3. **Build Flags**:
   - Compiler: Apple Clang (`clang++ -O3 -std=c++20 -DNDEBUG`)
   - Target Arch: `-mcpu=apple-m4` or `-march=armv8.6-a+fp16+neon`
4. **Core Pinning**:
   - Differentiate Apple Performance (P) cores vs Efficiency (E) cores (e.g. via `pthread_setaffinity_np` or macOS QoS classes).
   - Report $W=1 \to 2 \to 4 \to 8 \to 10$ on P-cores separately from E-core mix.
