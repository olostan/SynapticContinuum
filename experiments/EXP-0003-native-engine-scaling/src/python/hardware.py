"""Hardware discovery and memory preflight enforcement for EXP-0003."""
from dataclasses import asdict, dataclass
import os
import platform
import subprocess
from typing import Dict, Optional, Tuple


@dataclass
class HostSpecs:
    platform_system: str
    machine: str
    processor: str
    cpu_model: str
    physical_cores: int
    logical_cores: int
    total_ram_bytes: int
    available_ram_bytes: int
    swap_total_bytes: int
    swap_free_bytes: int
    compiler_info: str


def discover_hardware() -> HostSpecs:
    sys_name = platform.system()
    machine = platform.machine()
    processor = platform.processor() or "unknown"
    cpu_model = "unknown"
    total_ram = 16 * 1024 * 1024 * 1024
    available_ram = 8 * 1024 * 1024 * 1024
    swap_total = 0
    swap_free = 0

    if sys_name == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    key = parts[0].strip()
                    val_kb = int(parts[1].strip().split()[0])
                    if key == "MemTotal":
                        total_ram = val_kb * 1024
                    elif key == "MemAvailable":
                        available_ram = val_kb * 1024
                    elif key == "SwapTotal":
                        swap_total = val_kb * 1024
                    elif key == "SwapFree":
                        swap_free = val_kb * 1024
        except Exception:
            pass
    elif sys_name == "Darwin":
        try:
            res = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
            if res.returncode == 0:
                cpu_model = res.stdout.strip()
            mem_res = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
            if mem_res.returncode == 0:
                total_ram = int(mem_res.stdout.strip())
                available_ram = int(total_ram * 0.7) # Conservative estimate on macOS
        except Exception:
            pass

    physical_cores = os.cpu_count() or 1
    logical_cores = os.cpu_count() or 1

    compiler_info = "unknown"
    try:
        res = subprocess.run(["g++", "--version"], capture_output=True, text=True)
        if res.returncode == 0:
            compiler_info = res.stdout.splitlines()[0]
        else:
            res2 = subprocess.run(["clang++", "--version"], capture_output=True, text=True)
            if res2.returncode == 0:
                compiler_info = res2.stdout.splitlines()[0]
    except Exception:
        pass

    return HostSpecs(
        platform_system=sys_name,
        machine=machine,
        processor=processor,
        cpu_model=cpu_model,
        physical_cores=physical_cores,
        logical_cores=logical_cores,
        total_ram_bytes=total_ram,
        available_ram_bytes=available_ram,
        swap_total_bytes=swap_total,
        swap_free_bytes=swap_free,
        compiler_info=compiler_info,
    )


def estimate_workload_memory_bytes(
    num_nodes: int,
    degree: int,
    active_fraction: float,
    rate: float,
    t_max: float,
    engine: str,
) -> int:
    """Preflight estimation of memory consumption in bytes."""
    num_edges = num_nodes * degree
    graph_bytes = num_nodes * 8 + num_edges * 12
    state_bytes = num_nodes * 24
    est_events = max(1000, int(num_nodes * active_fraction * rate * t_max * 2))
    queue_bytes = est_events * 32

    if "sync" in engine:
        max_delay_steps = int(2.0 / 0.1) + 4
        sync_bytes = max_delay_steps * num_nodes * 4
        return graph_bytes + state_bytes + sync_bytes
    elif "literal" in engine:
        vector_overhead = num_nodes * (3 * 24)
        return graph_bytes + state_bytes + queue_bytes * 2 + vector_overhead
    else:
        return graph_bytes + state_bytes + queue_bytes


def preflight_check(
    num_nodes: int,
    degree: int,
    active_fraction: float,
    rate: float,
    t_max: float,
    engine: str,
    max_fraction: float = 0.60,
) -> Tuple[bool, int, int]:
    """Returns (is_safe, estimated_bytes, available_limit)."""
    hw = discover_hardware()
    est_bytes = estimate_workload_memory_bytes(num_nodes, degree, active_fraction, rate, t_max, engine)
    limit_bytes = int(hw.available_ram_bytes * max_fraction)
    return (est_bytes <= limit_bytes, est_bytes, limit_bytes)
