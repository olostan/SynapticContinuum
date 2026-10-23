"""Unified Benchmark Harness: CPU vs Vulkan GPU for Neural State Operations."""

import json
import os
import sys
import time
import numpy as np
import torch

from gpu_vulkan import VulkanEngine
from cpu_reference import CPUReferenceEngine


def read_drm_sensor(name: str) -> int:
    path = f"/sys/class/drm/card0/device/{name}"
    try:
        with open(path, "r") as f:
            return int(f.read().strip())
    except Exception:
        return -1


def compute_stats(latencies_ms: list[float]) -> dict:
    arr = np.array(latencies_ms)
    return {
        "median_ms": float(np.median(arr)),
        "p95_ms": float(np.percentile(arr, 95)),
        "mean_ms": float(np.mean(arr)),
        "min_ms": float(np.min(arr)),
        "max_ms": float(np.max(arr)),
        "std_ms": float(np.std(arr)),
    }


def benchmark_fn(fn, warmups: int, iters: int) -> dict:
    for _ in range(warmups):
        fn()
    latencies = []
    t_start = time.perf_counter()
    for _ in range(iters):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
    total_time_s = time.perf_counter() - t_start
    stats = compute_stats(latencies)
    stats["throughput_ops_per_sec"] = float(iters / total_time_s)
    return stats


def run_all_benchmarks(num_warmup: int = 15, num_iter: int = 100):
    print("=" * 70)
    print("SynapticContinuum — Linux Vega GPU vs CPU Benchmark Suite")
    print("=" * 70)

    print("\n1. Initializing GPU & CPU engines...")
    vulkan = VulkanEngine()
    cpu = CPUReferenceEngine()

    print(f"   Vulkan Adapter: {vulkan.device_name} ({vulkan.backend_type})")
    print(f"   Vulkan Init Time: {vulkan.init_time_ms:.2f} ms")
    print(f"   CPU Threads: {cpu.num_threads}")

    results = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "gpu_device": vulkan.device_name,
            "vulkan_backend": vulkan.backend_type,
            "vulkan_init_time_ms": vulkan.init_time_ms,
            "cpu_threads": cpu.num_threads,
            "warmup_runs": num_warmup,
            "measured_runs": num_iter,
        },
        "dense_gemm": [],
        "temporal_trace_decay": [],
        "recurrent_state_update": [],
        "sparse_event_propagation": [],
        "backpropagation": [],
    }

    # ==========================================
    # BENCHMARK 1: Dense GEMM
    # ==========================================
    print("\n" + "=" * 70)
    print("Benchmark 1: Dense GEMM (Matrix Multiplication)")
    print("=" * 70)
    sizes = [128, 512, 1024]
    batches = [1, 32]

    for N in sizes:
        for B in batches:
            A_np = np.random.randn(B, N).astype(np.float32)
            W_np = np.random.randn(N, N).astype(np.float32)
            A_t = torch.from_numpy(A_np)
            W_t = torch.from_numpy(W_np)

            # Correctness verification
            c_gpu = vulkan.run_gemm(A_np, W_np)
            c_cpu = cpu.run_gemm_numpy(A_np, W_np)
            max_err = float(np.max(np.abs(c_gpu - c_cpu)))
            assert max_err < 1e-3, f"GEMM correctness failed! max_err={max_err}"

            # Benchmarks
            stats_gpu = benchmark_fn(lambda: vulkan.run_gemm(A_np, W_np), num_warmup, num_iter)
            stats_cpu_torch = benchmark_fn(lambda: cpu.run_gemm_torch(A_t, W_t), num_warmup, num_iter)
            stats_cpu_numpy = benchmark_fn(lambda: cpu.run_gemm_numpy(A_np, W_np), num_warmup, num_iter)

            speedup_vs_torch = stats_cpu_torch["median_ms"] / stats_gpu["median_ms"]

            item = {
                "batch": B,
                "dim": N,
                "gpu_vulkan": stats_gpu,
                "cpu_torch": stats_cpu_torch,
                "cpu_numpy": stats_cpu_numpy,
                "speedup_gpu_over_torch": speedup_vs_torch,
                "max_abs_error": max_err,
            }
            results["dense_gemm"].append(item)

            print(f"Shape ({B}x{N}) * ({N}x{N}):")
            print(f"  GPU Vulkan:   median = {stats_gpu['median_ms']:.4f} ms | p95 = {stats_gpu['p95_ms']:.4f} ms")
            print(f"  CPU PyTorch:  median = {stats_cpu_torch['median_ms']:.4f} ms | p95 = {stats_cpu_torch['p95_ms']:.4f} ms")
            print(f"  Speedup (GPU/CPU): {speedup_vs_torch:.2f}x (crossover: {'GPU FASTER' if speedup_vs_torch > 1.0 else 'CPU FASTER'})")

    # ==========================================
    # BENCHMARK 2: Temporal Trace Decay
    # ==========================================
    print("\n" + "=" * 70)
    print("Benchmark 2: Temporal Trace Decay (Z = alpha*Z + (1-alpha)*H)")
    print("=" * 70)
    K = 4
    for N in sizes:
        Z_np = np.random.randn(N, K).astype(np.float32)
        H_np = np.random.randn(N).astype(np.float32)
        alpha_np = np.array([0.9, 0.7, 0.5, 0.2], dtype=np.float32)

        Z_t = torch.from_numpy(Z_np)
        H_t = torch.from_numpy(H_np)
        alpha_t = torch.from_numpy(alpha_np)

        # Correctness
        z_gpu = vulkan.run_trace_decay(Z_np, H_np, alpha_np)
        z_cpu = cpu.run_trace_decay_numpy(Z_np, H_np, alpha_np)
        max_err = float(np.max(np.abs(z_gpu - z_cpu)))
        assert max_err < 1e-4, f"Trace decay correctness failed! max_err={max_err}"

        stats_gpu = benchmark_fn(lambda: vulkan.run_trace_decay(Z_np, H_np, alpha_np), num_warmup, num_iter)
        stats_cpu_torch = benchmark_fn(lambda: cpu.run_trace_decay_torch(Z_t, H_t, alpha_t), num_warmup, num_iter)
        stats_cpu_numpy = benchmark_fn(lambda: cpu.run_trace_decay_numpy(Z_np, H_np, alpha_np), num_warmup, num_iter)

        speedup = stats_cpu_torch["median_ms"] / stats_gpu["median_ms"]
        item = {
            "num_neurons": N,
            "num_timescales": K,
            "gpu_vulkan": stats_gpu,
            "cpu_torch": stats_cpu_torch,
            "cpu_numpy": stats_cpu_numpy,
            "speedup_gpu_over_torch": speedup,
            "max_abs_error": max_err,
        }
        results["temporal_trace_decay"].append(item)

        print(f"Neurons {N}, Timescales {K}:")
        print(f"  GPU Vulkan:   median = {stats_gpu['median_ms']:.4f} ms")
        print(f"  CPU PyTorch:  median = {stats_cpu_torch['median_ms']:.4f} ms")
        print(f"  Speedup (GPU/CPU): {speedup:.2f}x ({'GPU FASTER' if speedup > 1.0 else 'CPU FASTER'})")

    # ==========================================
    # BENCHMARK 3: Recurrent State Update Step
    # ==========================================
    print("\n" + "=" * 70)
    print("Benchmark 3: Streaming Recurrent State Update (h_next = tanh(W*h + b + x))")
    print("=" * 70)
    for N in sizes:
        W_np = (np.random.randn(N, N) * 0.1).astype(np.float32)
        h_np = np.random.randn(N).astype(np.float32)
        b_np = np.zeros(N, dtype=np.float32)
        x_np = np.random.randn(N).astype(np.float32)

        W_t = torch.from_numpy(W_np)
        h_t = torch.from_numpy(h_np)
        b_t = torch.from_numpy(b_np)
        x_t = torch.from_numpy(x_np)

        # Correctness
        hn_gpu = vulkan.run_recurrent_step(W_np, h_np, b_np, x_np)
        hn_cpu = cpu.run_recurrent_step_numpy(W_np, h_np, b_np, x_np)
        max_err = float(np.max(np.abs(hn_gpu - hn_cpu)))
        assert max_err < 1e-4, f"Recurrent step correctness failed! max_err={max_err}"

        stats_gpu = benchmark_fn(lambda: vulkan.run_recurrent_step(W_np, h_np, b_np, x_np), num_warmup, num_iter)
        stats_cpu_torch = benchmark_fn(lambda: cpu.run_recurrent_step_torch(W_t, h_t, b_t, x_t), num_warmup, num_iter)

        speedup = stats_cpu_torch["median_ms"] / stats_gpu["median_ms"]
        item = {
            "dim": N,
            "gpu_vulkan": stats_gpu,
            "cpu_torch": stats_cpu_torch,
            "speedup_gpu_over_torch": speedup,
            "max_abs_error": max_err,
        }
        results["recurrent_state_update"].append(item)

        print(f"Dimension {N}:")
        print(f"  GPU Vulkan:   median = {stats_gpu['median_ms']:.4f} ms")
        print(f"  CPU PyTorch:  median = {stats_cpu_torch['median_ms']:.4f} ms")
        print(f"  Speedup (GPU/CPU): {speedup:.2f}x ({'GPU FASTER' if speedup > 1.0 else 'CPU FASTER'})")

    # ==========================================
    # BENCHMARK 4: Sparse Event Propagation
    # ==========================================
    print("\n" + "=" * 70)
    print("Benchmark 4: Sparse Event Propagation (Active Subset & Connection Traversal)")
    print("=" * 70)
    active_fractions = [0.05, 0.10, 0.25, 0.50, 1.00]
    DEGREE = 16  # average outward degree per node

    for N in sizes:
        # Build random graph
        rng = np.random.RandomState(42)
        adj_list = []
        all_src = []
        all_dst = []
        all_weights = []
        for i in range(N):
            targets = rng.choice(N, size=DEGREE, replace=False)
            weights = rng.randn(DEGREE).astype(np.float32) * 0.1
            adj_list.append(list(zip(targets.tolist(), weights.tolist())))
            for dst, w in zip(targets, weights):
                all_src.append(i)
                all_dst.append(dst)
                all_weights.append(w)

        all_src_arr = np.array(all_src, dtype=np.uint32)
        all_dst_arr = np.array(all_dst, dtype=np.uint32)
        all_weights_arr = np.array(all_weights, dtype=np.float32)

        for frac in active_fractions:
            num_active = max(1, int(N * frac))
            active_nodes = sorted(rng.choice(N, size=num_active, replace=False).tolist())
            active_set = set(active_nodes)

            # Sub-graph for active nodes
            active_edge_mask = np.isin(all_src_arr, active_nodes)
            sub_src = all_src_arr[active_edge_mask]
            sub_dst = all_dst_arr[active_edge_mask]
            sub_weights = all_weights_arr[active_edge_mask]

            h_in = np.zeros(N, dtype=np.float32)
            h_in[active_nodes] = rng.randn(num_active).astype(np.float32)

            # Torch tensors
            sub_src_t = torch.from_numpy(sub_src.astype(np.int64))
            sub_dst_t = torch.from_numpy(sub_dst.astype(np.int64))
            sub_weights_t = torch.from_numpy(sub_weights)
            h_in_t = torch.from_numpy(h_in)

            # Benchmarks
            stats_event_cpu = benchmark_fn(
                lambda: cpu.run_event_driven_sparse_cpu(active_nodes, adj_list, h_in, N),
                num_warmup, num_iter
            )
            stats_torch_scatter = benchmark_fn(
                lambda: cpu.run_sparse_scatter_torch(sub_src_t, sub_dst_t, sub_weights_t, h_in_t, N),
                num_warmup, num_iter
            )
            stats_gpu_vulkan = benchmark_fn(
                lambda: vulkan.run_sparse_scatter(sub_src, sub_dst, sub_weights, h_in, N),
                num_warmup, num_iter
            )

            crossover_ratio = stats_event_cpu["median_ms"] / stats_gpu_vulkan["median_ms"]

            item = {
                "num_neurons": N,
                "degree": DEGREE,
                "active_fraction": frac,
                "num_active_nodes": num_active,
                "num_active_edges": len(sub_src),
                "cpu_event_driven": stats_event_cpu,
                "cpu_torch_scatter": stats_torch_scatter,
                "gpu_vulkan": stats_gpu_vulkan,
                "ratio_cpu_event_to_gpu": crossover_ratio,
            }
            results["sparse_event_propagation"].append(item)

            print(f"N={N}, Active={frac*100:.0f}% ({num_active} nodes, {len(sub_src)} edges):")
            print(f"  CPU Event-Driven: median = {stats_event_cpu['median_ms']:.4f} ms ({stats_event_cpu['median_ms']*1000:.1f} µs)")
            print(f"  CPU PyTorch:      median = {stats_torch_scatter['median_ms']:.4f} ms")
            print(f"  GPU Vulkan:       median = {stats_gpu_vulkan['median_ms']:.4f} ms")
            advantage = "CPU EVENT-DRIVEN FASTER" if stats_event_cpu['median_ms'] < stats_gpu_vulkan['median_ms'] else "GPU FASTER"
            print(f"  Result: {advantage} ({stats_gpu_vulkan['median_ms']/stats_event_cpu['median_ms']:.1f}x difference)")

    # ==========================================
    # BENCHMARK 5: Backpropagation
    # ==========================================
    print("\n" + "=" * 70)
    print("Benchmark 5: Backpropagation (Forward + Autograd Backward)")
    print("=" * 70)
    for N in sizes:
        W_t = torch.randn(N, N, dtype=torch.float32) * 0.1
        h_t = torch.randn(N, dtype=torch.float32)
        x_t = torch.randn(N, dtype=torch.float32)

        stats_cpu_autograd = benchmark_fn(
            lambda: cpu.run_recurrent_step_autograd_torch(W_t, h_t, x_t),
            num_warmup, num_iter
        )

        item = {
            "dim": N,
            "cpu_torch_autograd": stats_cpu_autograd,
            "gpu_vulkan_autograd": {
                "status": "NOT EXECUTABLE",
                "reason": "No Vulkan autograd backend exists in PyTorch (Vulkan: False) or ROCm (gfx90c dropped).",
            }
        }
        results["backpropagation"].append(item)
        print(f"Dimension {N}:")
        print(f"  CPU PyTorch Autograd: median = {stats_cpu_autograd['median_ms']:.4f} ms | throughput = {stats_cpu_autograd['throughput_ops_per_sec']:.1f} steps/s")
        print(f"  GPU Vulkan Autograd:  NOT EXECUTABLE (Unsupported architecture / missing autograd runtime)")

    # Sensor check after full run
    gpu_busy = read_drm_sensor("gpu_busy_percent")
    vram_used_mb = read_drm_sensor("mem_info_vram_used") / (1024 * 1024)
    gtt_used_mb = read_drm_sensor("mem_info_gtt_used") / (1024 * 1024)
    print("\n" + "=" * 70)
    print("Post-Benchmark Hardware State:")
    print(f"  GPU Busy: {gpu_busy}%")
    print(f"  VRAM Used: {vram_used_mb:.1f} MB")
    print(f"  GTT Used: {gtt_used_mb:.1f} MB")
    print("=" * 70)

    results["post_state"] = {
        "gpu_busy_percent": gpu_busy,
        "vram_used_mb": vram_used_mb,
        "gtt_used_mb": gtt_used_mb,
    }

    out_path = os.path.join(os.path.dirname(__file__), "results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved benchmark results to {out_path}")


if __name__ == "__main__":
    warmup = 15
    iters = 100
    if len(sys.argv) > 1:
        iters = int(sys.argv[1])
    run_all_benchmarks(num_warmup=warmup, num_iter=iters)
