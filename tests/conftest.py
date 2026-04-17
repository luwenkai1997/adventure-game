import os

import pytest
from fastapi.testclient import TestClient

from app.utils import game_manager
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


@pytest.fixture
def client():
    """
    Provide an initialized TestClient for HTTP API testing.
    """
    with TestClient(app) as test_client:
        yield test_client
