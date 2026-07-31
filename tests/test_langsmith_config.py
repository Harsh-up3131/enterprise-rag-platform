import importlib
import os


def test_settings_populate_langsmith_environment(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)

    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "test-project")

    import app.config as config_module

    importlib.reload(config_module)

    assert config_module.settings.langsmith_tracing is True
    assert config_module.settings.langsmith_api_key == "test-key"
    assert config_module.settings.langsmith_project == "test-project"
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "test-key"
    assert os.environ["LANGSMITH_PROJECT"] == "test-project"
