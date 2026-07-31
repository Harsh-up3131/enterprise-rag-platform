import json
import logging
from io import StringIO

from app.services.security.dependency_audit import build_audit_commands, collect_dependency_audit_report
from app.utils.logging import get_logger


def test_get_logger_emits_json_payload(tmp_path):
    stream = StringIO()
    logger = get_logger("test-json-logger")
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("hello world", extra={"request_id": "abc-123"})

    payload = json.loads(stream.getvalue().strip())
    assert payload["message"] == "hello world"
    assert payload["request_id"] == "abc-123"
    assert payload["logger"] == "test-json-logger"


def test_dependency_audit_commands_are_built_for_manifests(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "package.json").write_text('{"name": "demo"}\n', encoding="utf-8")

    report = collect_dependency_audit_report(tmp_path)
    commands = build_audit_commands(tmp_path)

    assert report["python_manifest_exists"] is True
    assert report["javascript_manifest_exists"] is True
    assert any("pip-audit" in command for command in commands)
    assert any("npm audit" in command for command in commands)
