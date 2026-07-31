"""Helpers for dependency-vulnerability scanning and manifest discovery."""
from __future__ import annotations

import shutil
import shlex
from pathlib import Path


def collect_dependency_audit_report(project_root: str | Path | None = None) -> dict[str, object]:
    root = Path(project_root or ".").resolve()

    python_manifests = [
        str(path.relative_to(root))
        for path in sorted(root.glob("**/requirements*.txt"))
        if "node_modules" not in path.as_posix() and ".venv" not in path.as_posix()
    ]
    javascript_manifests = [
        str(path.relative_to(root))
        for path in sorted(root.glob("**/package.json"))
        if "node_modules" not in path.as_posix() and ".venv" not in path.as_posix()
    ]

    tool_status = {}
    tool_status["pip-audit"] = "available" if shutil.which("pip-audit") else "not-installed"
    tool_status["npm"] = "available" if shutil.which("npm") else "not-installed"

    return {
        "project_root": str(root),
        "python_manifest_exists": bool(python_manifests),
        "javascript_manifest_exists": bool(javascript_manifests),
        "python_manifests": python_manifests,
        "javascript_manifests": javascript_manifests,
        "tool_status": tool_status,
    }


def build_audit_commands(project_root: str | Path | None = None) -> list[str]:
    report = collect_dependency_audit_report(project_root)
    root = Path(report["project_root"])
    commands: list[str] = []

    for manifest in report["python_manifests"]:
        manifest_path = root / manifest
        manifest_dir = shlex.quote(str(manifest_path.parent))
        commands.append(f"cd {manifest_dir} && pip-audit -r {shlex.quote(manifest_path.name)}")

    for manifest in report["javascript_manifests"]:
        manifest_path = root / manifest
        manifest_dir = shlex.quote(str(manifest_path.parent))
        commands.append(f"cd {manifest_dir} && npm audit --omit=dev")

    if not commands:
        quoted_root = shlex.quote(str(root))
        commands.append(f"cd {quoted_root} && echo 'No dependency manifests found for audit'")

    return commands
