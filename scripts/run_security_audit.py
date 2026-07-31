#!/usr/bin/env python3
"""Run dependency and secret-scan checks for the project."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.security.dependency_audit import build_audit_commands, collect_dependency_audit_report


def main() -> int:
    project_root = PROJECT_ROOT
    report = collect_dependency_audit_report(project_root)
    print("Dependency audit report")
    print(f"- Python manifests: {report['python_manifests']}")
    print(f"- JavaScript manifests: {report['javascript_manifests']}")
    print(f"- Tool availability: {report['tool_status']}")

    if os.getenv("SKIP_DEPENDENCY_AUDIT") == "1":
        print("Skipping dependency audit because SKIP_DEPENDENCY_AUDIT=1")
        return 0

    for command in build_audit_commands(project_root):
        print(f"$ {command}")
        if "pip-audit" in command and report["tool_status"]["pip-audit"] != "available":
            print("Skipping pip-audit because it is not installed.")
            continue
        if "npm audit" in command and report["tool_status"]["npm"] != "available":
            print("Skipping npm audit because npm is not installed.")
            continue

        result = subprocess.run(command, shell=True, cwd=str(project_root), capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        if result.returncode != 0:
            print(f"Audit command failed with exit code {result.returncode}", file=sys.stderr)
            return result.returncode

    print("Secret-management reminder: prefer Docker/K8s secrets or a vault provider for JWT and DB credentials.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
