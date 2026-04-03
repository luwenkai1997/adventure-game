import os
import pytest
from fastapi.testclient import TestClient

from app.utils import game_manager
from app.services import llm_gateway
from server import app

@pytest.fixture(autouse=True)
def mock_db_dir(tmp_path, monkeypatch):
    """
    Ensure no test accesses the real games directory, unless REAL_E2E is set.
    """
    if os.environ.get("REAL_E2E") == "1":
        yield
        return
    mock_dir = tmp_path / "games"
    mock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(game_manager, "GAMES_DIR", str(mock_dir))
    yield str(mock_dir)

@pytest.fixture(autouse=True)
def llm_mock(monkeypatch):
    """
    Globally mock LLM calls to prevent real network requests, unless REAL_E2E is set.
    """
    if os.environ.get("REAL_E2E") == "1":
        yield None
        return
    async def fake_call_llm(*args, **kwargs):
        # Return a generic successful response format
        return (
            '{"scene":"全局测试场景","log":"测试流日志","choices":['
            '{"text":"继续测试分支","tendency":["勇敢"],"is_key_decision":false}'
            ']}'
        )
    
    async def fake_stream_llm(*args, **kwargs):
        yield '{"scene":"全局测试流场景","log":"测试流日志","choices":['
        yield '{"text":"片段合并内容","tendency":["勇敢"],"is_key_decision":false}'
        yield ']}'

    monkeypatch.setattr(llm_gateway, "call_llm", fake_call_llm)
    monkeypatch.setattr(llm_gateway, "call_llm_with_retry", fake_call_llm)
    monkeypatch.setattr(llm_gateway, "stream_llm", fake_stream_llm)
    return {
        "call_llm": fake_call_llm,
        "stream_llm": fake_stream_llm
    }

@pytest.fixture
def client():
    """
    Provide an initialized TestClient for HTTP API testing.
    """
    with TestClient(app) as test_client:
        yield test_client
