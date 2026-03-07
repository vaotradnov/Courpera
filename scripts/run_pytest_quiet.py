from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def deps_available() -> bool:
    try:
        import django  # noqa: F401
        import django_filters  # noqa: F401
        import drf_spectacular  # noqa: F401
        import rest_framework  # noqa: F401
    except Exception:
        return False
    return True


def main() -> int:
    # Ensure we run from repo root (file lives in Project/Courpera/scripts)
    here = Path(__file__).resolve()
    root = here.parents[1]
    os.chdir(root)
    # Clear addopts from pytest.ini to suppress HTML reports and extra noise
    # We'll pass only the essentials here.
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
        "--disable-warnings",
        "--maxfail=1",
        "--color=no",
        "--ds",
        "config.settings.precommit",
    ]
    if not deps_available():
        # Missing deps in the hook environment: do not block the commit.
        return 0
    # Capture output so pre-commit shows only Passed/Failed
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
