from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_TESTS = [
    "tests/test_integration.py::test_identity_gate_returns_409_for_incomplete_profile_on_match_surfaces",
    "tests/test_integration.py::test_onboarding_submit_rejects_invalid_psycho_payload",
    "tests/test_integration.py::test_onboarding_stage_transitions_incomplete_calibrating_eligible",
    "tests/test_integration.py::test_matches_v2_returns_top_7_high_certainty",
]


def _has_pytest() -> bool:
    return importlib.util.find_spec("pytest") is not None


def _resolve_python(explicit: str | None) -> str:
    if explicit:
        return explicit
    return sys.executable


def _run(py_bin: str, tests: list[str], extra_args: list[str]) -> int:
    env = os.environ.copy()
    env.setdefault("APP_ENV", "test")
    env.setdefault("ADMIN_EMAILS", "admin@example.com")
    env.setdefault("AUTH_RATE_LIMIT_PER_MINUTE", "10000")
    env.setdefault("AUTH_REFRESH_RATE_LIMIT_PER_MINUTE", "10000")
    env.setdefault("MESSAGE_SEND_RATE_LIMIT_PER_MINUTE", "10000")
    env.setdefault("PYTHONPYCACHEPREFIX", "/tmp/pycache")

    cmd = [py_bin, "-m", "pytest", "-q", *tests, *extra_args]
    print("[identity-tests] running:", " ".join(cmd))
    proc = subprocess.run(cmd, env=env, check=False)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run identity-model integration tests (gating, onboarding validation, stage transitions, top-7 output)."
    )
    parser.add_argument("--python", dest="python_bin", default=None, help="Python binary to use (default: current executable)")
    parser.add_argument("--all", action="store_true", help="Run full integration suite instead of focused identity tests")
    parser.add_argument("pytest_args", nargs="*", help="Extra args passed through to pytest")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    py_bin = _resolve_python(args.python_bin)

    if not _has_pytest():
        print("[identity-tests] pytest is not installed in this Python environment.")
        print("[identity-tests] install dependencies, then re-run:")
        print(f"  {py_bin} -m pip install -r requirements.txt")
        print(f"  {py_bin} -m scripts.run_identity_tests")
        return 2

    tests = ["tests/test_integration.py"] if args.all else DEFAULT_TESTS
    rc = _run(py_bin, tests, args.pytest_args)

    if rc == 0:
        print("[identity-tests] passed")
    else:
        print(f"[identity-tests] failed with exit code {rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
