from app.config import Settings
from app.services.security.dependency_audit import build_audit_commands, collect_dependency_audit_report


def test_database_url_file_is_loaded_from_secret(monkeypatch, tmp_path):
    secret_file = tmp_path / "database_url.secret"
    secret_file.write_text("postgresql+psycopg://ekip:super-secret@localhost:5432/ekip", encoding="utf-8")

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL_FILE", str(secret_file))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://ekip:super-secret@localhost:5432/ekip"


def test_collect_dependency_audit_report_identifies_manifests_and_tooling(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir(parents=True, exist_ok=True)
    (frontend_dir / "package.json").write_text('{"name": "demo"}', encoding="utf-8")

    report = collect_dependency_audit_report(tmp_path)

    assert report["python_manifest_exists"] is True
    assert report["javascript_manifest_exists"] is True
    assert "requirements.txt" in report["python_manifests"]
    assert "frontend/package.json" in report["javascript_manifests"]
    assert "pip-audit" in report["tool_status"]
    assert "npm" in report["tool_status"]


def test_build_audit_commands_uses_available_manifests(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir(parents=True, exist_ok=True)
    (frontend_dir / "package.json").write_text('{"name": "demo"}', encoding="utf-8")

    commands = build_audit_commands(tmp_path)

    assert any("pip-audit" in command for command in commands)
    assert any("npm audit" in command for command in commands)
