"""API smoke tests (TestClient runs ASGI lifespan — initializes httpx client)."""

from fastapi.testclient import TestClient

from app.services import game_service as game_service_module
from server import app


def test_list_games():
    with TestClient(app) as client:
        r = client.get("/api/games")
    assert r.status_code == 200
    data = r.json()
    assert "games" in data
    assert "count" in data


def test_current_game():
    with TestClient(app) as client:
        r = client.get("/api/games/current")
    assert r.status_code == 200
    body = r.json()
    assert "current_game" in body


def test_player_skills():
    with TestClient(app) as client:
        r = client.get("/api/player/skills")
    assert r.status_code == 200
    assert "skills" in r.json()


def test_relation_types():
    with TestClient(app) as client:
        r = client.get("/api/relation-types")
    assert r.status_code == 200
    assert "types" in r.json()


def test_index_html():
    with TestClient(app) as client:
        r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "app.js" in r.text


def test_static_css():
    with TestClient(app) as client:
        r = client.get("/static/css/styles.css")
    assert r.status_code == 200
    assert r.text.strip().startswith("html")


def test_static_js():
    with TestClient(app) as client:
        r = client.get("/static/js/app.js")
    assert r.status_code == 200
    assert "STORAGE_KEY" in r.text


def test_story_expand_validation_app_error():
    with TestClient(app) as client:
        r = client.post("/api/story/expand", json={"user_input": "   "})
    assert r.status_code == 400
    body = r.json()
    assert body.get("success") is False
    assert "error" in body
    assert body["error"].get("code") == "validation_error"


def test_malformed_game_id_rejected():
    with TestClient(app) as client:
        r = client.get("/api/games/not-a-valid-id")
    assert r.status_code == 400
    body = r.json()
    assert body.get("success") is False
    assert body["error"].get("code") == "validation_error"


def test_malformed_char_id_rejected():
    with TestClient(app) as client:
        r = client.get("/api/characters/bad!id")
    assert r.status_code == 400
    body = r.json()
    assert body.get("success") is False
    assert body["error"].get("code") == "validation_error"


def test_chat_happy_path_mock_llm(monkeypatch):
    async def fake_llm(*args, **kwargs):
        return (
            '{"scene":"测试场景","log":"测试","choices":['
            '{"text":"继续","tendency":["勇敢"],"is_key_decision":false}'
            "]}"
        )

    monkeypatch.setattr(game_service_module, "call_llm", fake_llm)

    with TestClient(app) as client:
        cr = client.post("/api/games/create", json={"world_setting": "单元测试世界"})
        assert cr.status_code == 200
        game_id = cr.json()["game_id"]
        lr = client.post(f"/api/games/load/{game_id}")
        assert lr.status_code == 200

        r = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "你好"}],
                "extraPrompt": "",
                "turn_context": {"tendency": {"勇敢": 2, "谨慎": 0}},
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["content"]["scene"] == "测试场景"
    assert data["meta"].get("repaired") is False


def test_request_id_header_echoed():
    with TestClient(app) as client:
        r = client.get("/api/games", headers={"X-Request-ID": "test-req-123"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "test-req-123"
