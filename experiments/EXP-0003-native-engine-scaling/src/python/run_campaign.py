"""Main benchmark campaign runner script for EXP-0003."""
import argparse
import os
import subprocess
import sys
import time

from src.python.benchmarks import BenchmarkRunner
from src.python.hardware import discover_hardware


def main():
    parser = argparse.ArgumentParser(description="Run EXP-0003 benchmark campaign")
    parser.add_argument("--profile", choices=["standard", "extended", "all"], default="all")
    parser.add_argument("--out", default="runs", help="Output directory for metrics")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pre-benchmark unit tests")
    args = parser.parse_args()

    print("=" * 70)
    print("SynapticContinuum EXP-0003: Native Engine Scaling Campaign")
    print("=" * 70)

    hw = discover_hardware()
    print(f"Host OS: {hw.platform_system} ({hw.machine})")
    print(f"CPU: {hw.cpu_model} ({hw.physical_cores} physical / {hw.logical_cores} logical)")
    print(f"Memory: {hw.total_ram_bytes / 1e9:.2f} GB total, {hw.available_ram_bytes / 1e9:.2f} GB available")
    print(f"Compiler: {hw.compiler_info}")
    print("=" * 70)

    # 1. Run unit test suites (C++ and Python) before any benchmark
    if not args.skip_tests:
        print("[STAGE 1] Running C++ Native Unit Tests (sc_tests)...")
        bin_tests = os.path.join(os.path.dirname(__file__), "..", "..", "build", "bin", "sc_tests")
        if not os.path.exists(bin_tests):
            print(f"Error: {bin_tests} not found. Please build native engine first with cmake.")
            sys.exit(1)
        res_cpp = subprocess.run([bin_tests])
        if res_cpp.returncode != 0:
            print("C++ native unit tests FAILED! Aborting benchmark.")
            sys.exit(1)

        print("[STAGE 2] Running Python Parity & Safety Tests (pytest)...")
        tests_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tests")
        res_py = subprocess.run([sys.executable, "-m", "pytest", tests_dir])
        if res_py.returncode != 0:
            print("Python unit tests FAILED! Aborting benchmark.")
            sys.exit(1)
        print("All correctness tests PASSED! Proceeding to benchmarks.\n")

    # 2. Run benchmarks
    runner = BenchmarkRunner(output_root=args.out)
    all_results = []

    if args.profile in ["standard", "all"]:
        print("[STAGE 3] Executing Standard Shared Screening Matrix (seeds 11, 23, 37)...")
        std_results = runner.run_standard_screening(seeds=[11, 23, 37])
        all_results.extend(std_results)

    if args.profile in ["extended", "all"]:
        print("[STAGE 4] Executing Primary Scaling Matrix (N=100k, 1M, threads, queues)...")
        scale_results = runner.run_primary_scaling(seeds=[11, 23, 37, 41, 53])
        all_results.extend(scale_results)

    # 3. Save metrics bundle
    metrics_path = runner.save_metrics(all_results)
    print("\n" + "=" * 70)
    print(f"Benchmark run complete! Results saved to: {metrics_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
