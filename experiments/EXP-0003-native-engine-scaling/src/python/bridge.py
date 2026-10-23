"""Bridge connecting Python schedulers (EXP-0002) and compiled C++ native engines."""
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Dynamically bind EXP-0002 into its own isolated namespace `exp0002`
EXP0002_SRC = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "EXP-0002-event-driven-dynamics", "src"
))
if "exp0002" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "exp0002",
        os.path.join(EXP0002_SRC, "__init__.py"),
        submodule_search_locations=[EXP0002_SRC],
    )
    exp0002 = importlib.util.module_from_spec(spec)
    sys.modules["exp0002"] = exp0002
    spec.loader.exec_module(exp0002)

PyNeuralGraph = importlib.import_module("exp0002.substrate").NeuralGraph
PySubstrateConfig = importlib.import_module("exp0002.substrate").SubstrateConfig
PyEventScheduler = importlib.import_module("exp0002.schedulers").EventDrivenScheduler
PyDenseSyncScheduler = importlib.import_module("exp0002.schedulers").DenseSynchronousScheduler
PySparseSyncScheduler = importlib.import_module("exp0002.schedulers").SparseSynchronousScheduler

from .prng import generate_deterministic_events, generate_deterministic_graph

# Path to native binary
BIN_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "build", "bin", "sc_engine"
))


def run_py_event(
    num_nodes: int,
    degree: int,
    active_fraction: float,
    rate: float,
    t_max: float,
    seed: int,
) -> Dict[str, Any]:
    """Runs Python Event-Driven Scheduler from EXP-0002."""
    config = PySubstrateConfig(num_nodes=num_nodes, mean_out_degree=degree)
    adj_targets, adj_weights, adj_delays = generate_deterministic_graph(num_nodes, degree, seed)
    graph = PyNeuralGraph(num_nodes, adj_targets, adj_weights, adj_delays)
    ext_events = generate_deterministic_events(num_nodes, active_fraction, rate, t_max, seed)

    sched = PyEventScheduler(config, graph)
    res = sched.run(ext_events, t_max)

    return {
        "scheduler_name": "py_event",
        "wall_time_sec": res.wall_time_sec,
        "total_events_processed": res.total_events_processed,
        "total_edges_traversed": res.total_edges_traversed,
        "total_spikes": res.total_spikes,
        "peak_queue_size": res.peak_queue_size,
        "final_time": res.final_time,
        "injected_active_fraction": res.injected_active_fraction,
        "propagated_active_fraction": res.propagated_active_fraction,
        "max_queue_exceeded": res.max_queue_exceeded,
        "final_potentials": res.final_potentials,
        "spike_records": res.spike_records,
    }


def run_py_sync(
    num_nodes: int,
    degree: int,
    active_fraction: float,
    rate: float,
    t_max: float,
    seed: int,
    dt: float = 0.1,
    sparse: bool = False,
) -> Dict[str, Any]:
    """Runs Python Synchronous Scheduler (Dense or Sparse) from EXP-0002."""
    config = PySubstrateConfig(num_nodes=num_nodes, mean_out_degree=degree)
    adj_targets, adj_weights, adj_delays = generate_deterministic_graph(num_nodes, degree, seed)
    graph = PyNeuralGraph(num_nodes, adj_targets, adj_weights, adj_delays)
    ext_events = generate_deterministic_events(num_nodes, active_fraction, rate, t_max, seed)

    if sparse:
        sched = PySparseSyncScheduler(config, graph, dt=dt)
    else:
        sched = PyDenseSyncScheduler(config, graph, dt=dt)
    res = sched.run(ext_events, t_max)

    return {
        "scheduler_name": f"py_sync_{'sparse' if sparse else 'dense'}_dt_{dt}",
        "wall_time_sec": res.wall_time_sec,
        "total_events_processed": res.total_events_processed,
        "total_edges_traversed": res.total_edges_traversed,
        "total_spikes": res.total_spikes,
        "peak_queue_size": res.peak_queue_size,
        "final_time": res.final_time,
        "injected_active_fraction": res.injected_active_fraction,
        "propagated_active_fraction": res.propagated_active_fraction,
        "final_potentials": res.final_potentials,
        "spike_records": res.spike_records,
    }


def run_cpp_engine(
    engine: str,
    num_nodes: int,
    degree: int,
    active_fraction: float,
    rate: float,
    t_max: float,
    seed: int,
    dt: float = 0.1,
    workers: int = 4,
    topology: str = "random",
    timing: str = "poisson",
    history_L: int = 0,
    trace_B: int = 0,
    warmups: int = 2,
    reps: int = 5,
) -> Dict[str, Any]:
    """Runs compiled C++ native engine via sc_engine binary."""
    cmd = [
        BIN_PATH,
        "--engine", engine,
        "--nodes", str(num_nodes),
        "--degree", str(degree),
        "--seed", str(seed),
        "--active-fraction", str(active_fraction),
        "--rate", str(rate),
        "--t-max", str(t_max),
        "--dt", str(dt),
        "--workers", str(workers),
        "--topology", topology,
        "--timing", timing,
        "--history", str(history_L),
        "--trace-bank", str(trace_B),
        "--warmups", str(warmups),
        "--reps", str(reps),
    ]

    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"sc_engine failed with code {p.returncode}: {p.stderr}")

    try:
        data = json.loads(p.stdout)
        return data
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON output: {p.stdout}") from e
