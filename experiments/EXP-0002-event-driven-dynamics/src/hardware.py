"""Hardware, machine, and environment detection for EXP-0002.

Detects physical OS, CPU, RAM, disk, framework versions, git commit, and accelerator support.
"""
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict


def detect_environment() -> Dict[str, Any]:
    env_info: Dict[str, Any] = {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "python": {
            "version": platform.python_version(),
            "compiler": platform.python_compiler(),
            "executable": sys.executable,
        },
    }

    # RAM detection
    try:
        total_ram_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024**3)
        avail_ram_gb = None
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        avail_ram_gb = int(line.split()[1]) / (1024**2)
                        break
        if avail_ram_gb is None:
            available_pages = os.sysconf("SC_AVPHYS_PAGES")
            avail_ram_gb = os.sysconf("SC_PAGE_SIZE") * available_pages / (1024**3)
        env_info["ram"] = {
            "total_gb": round(total_ram_gb, 2),
            "available_gb": round(avail_ram_gb, 2),
        }
    except Exception as e:
        env_info["ram"] = {"error": str(e)}

    # CPU cores and model
    env_info["cpu"] = {
        "logical_cores": os.cpu_count() or 1,
    }
    if platform.system() == "Linux" and os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        env_info["cpu"]["model_name"] = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

    # Disk space
    try:
        disk = shutil.disk_usage(".")
        env_info["disk"] = {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
        }
    except Exception as e:
        env_info["disk"] = {"error": str(e)}

    # Framework detection (torch, numpy, etc.)
    try:
        import torch

        env_info["torch"] = {
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "mps_available": (
                getattr(torch.backends, "mps", None) is not None
                and torch.backends.mps.is_available()
            ),
            "vulkan_available": getattr(torch, "is_vulkan_available", lambda: False)(),
            "cpu_capability": getattr(
                torch.backends.cpu, "get_cpu_capability", lambda: "unknown"
            )(),
        }
    except ImportError:
        env_info["torch"] = {"available": False}

    try:
        import numpy as np

        env_info["numpy"] = {"version": np.__version__}
    except ImportError:
        env_info["numpy"] = {"available": False}

    # Git metadata
    try:
        commit_sha = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
        status = (
            subprocess.check_output(
                ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        env_info["git"] = {
            "commit_sha": commit_sha,
            "branch": branch,
            "is_dirty": len(status) > 0,
        }
    except Exception as e:
        env_info["git"] = {"error": str(e)}

    return env_info


if __name__ == "__main__":
    import json

    print(json.dumps(detect_environment(), indent=2))
