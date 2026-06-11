import subprocess
import sys


def _run(step: str, cmd: list[str]) -> None:
    print(f"[release-gate] {step}: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(f"[release-gate] failed at step: {step} (exit={result.returncode})")


def main() -> None:
    _run("validate_runtime_config", [sys.executable, "-m", "scripts.validate_runtime_config"])
    _run("smoke_runtime_health", [sys.executable, "-m", "scripts.smoke_runtime_health"])
    _run("pytest", [sys.executable, "-m", "pytest", "-q"])
    _run("compileall", [sys.executable, "-m", "compileall", "app"])
    print("[release-gate] all checks passed")


if __name__ == "__main__":
    main()
