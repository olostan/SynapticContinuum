"""
Import helper for EXP-0005 tests so `python3 -m unittest discover -s experiments/EXP-0005-scientific-simulation-substrates/tests -v`
works cleanly from the repository root without modifying global PYTHONPATH or importing EXP-0004 code.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

EXP0005_ROOT = Path(__file__).resolve().parent.parent


def _load_module(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_fixture_generator_module() -> ModuleType:
    return _load_module("sc05_fixture_generator", EXP0005_ROOT / "scripts" / "fixture_generator.py")


def load_oracle_module() -> ModuleType:
    return _load_module("sc05_analytic_lif_oracle", EXP0005_ROOT / "oracle" / "analytic_lif_oracle.py")


def load_validator_module() -> ModuleType:
    return _load_module("sc05_validate_v2", EXP0005_ROOT / "scripts" / "validate_sc05_v2.py")
