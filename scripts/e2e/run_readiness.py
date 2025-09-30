"""Run end-to-end readiness checks.

This script stitches together slow-running readiness scenarios that need
additional orchestration beyond unit/integration suites. For now it executes
selected pytest modules, but it can be extended to invoke CLI workflows or
service endpoints once staging infrastructure is available.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Sequence


def main(args: Sequence[str] | None = None) -> int:
    suites: list[list[str]] = [
        ["pytest", "-q", "tests/test_readiness_pipeline.py"],
    ]
    for command in suites:
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())

