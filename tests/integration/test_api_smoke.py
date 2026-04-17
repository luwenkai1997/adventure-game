"""API smoke tests for the explicit context + repository + LLM adapter stack."""

from fastapi.testclient import TestClient

from app.container import container
from app.models.chat import ChatTurnContent
from server import app


def _session_headers(session_id: str) -> dict:
    return {"X-Adventure-Session-ID": session_id}


def test_list_games():
    with TestClient(app) as client:
        response = client.get("/api/games")
    assert response.status_code == 200
    data = response.json()
    assert "games" in data
    assert "count" in data


def test_current_game():
    with TestClient(app) as client:
        response = client.get("/api/games/current")
    assert response.status_code == 200
    body = response.json()
    assert "current_game" in body


def test_player_skills():
    with TestClient(app) as client:
        response = client.get("/api/player/skills")
    assert response.status_code == 200
    assert "skills" in response.json()


def test_relation_types():
    with TestClient(app) as client:
        response = client.get("/api/relation-types")
    assert response.status_code == 200
    assert "types" in response.json()


def test_index_html():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "app.js" in response.text


def test_static_css():
    with TestClient(app) as client:
        response = client.get("/static/css/styles.css")
    assert response.status_code == 200
    stripped = response.text.strip()
    assert stripped.startswith(":root") or stripped.startswith("html")


def test_static_js():
    with TestClient(app) as client:
        response = client.get("/static/js/app.js")
    assert response.status_code == 200
    assert "STORAGE_KEY" in response.text


def test_story_expand_validation_app_error():
    with TestClient(app) as client:
        response = client.post("/api/story/expand", json={"user_input": "   "})
    assert response.status_code == 400
    body = response.json()
    assert body.get("success") is False
    assert "error" in body
    assert body["error"].get("code") == "validation_error"


def test_malformed_game_id_rejected():
    with TestClient(app) as client:
        response = client.get("/api/games/not-a-valid-id")
    assert response.status_code == 400
    body = response.json()
    assert body.get("success") is False
    assert body["error"].get("code") == "validation_error"


def test_malformed_char_id_rejected():
    with TestClient(app) as client:
        response = client.get("/api/characters/bad!id")
    assert response.status_code == 400
    body = response.json()
    assert body.get("success") is False
    assert body["error"].get("code") == "validation_error"


def test_create_game_updates_session_mapping():
    session_id = "test-session-current"
    with TestClient(app) as client:
        create_response = client.post(
            "/api/games/create",
            json={"world_setting": "单元测试世界"},
            headers=_session_headers(session_id),
        )
        assert create_response.status_code == 200
        game_id = create_response.json()["game_id"]

        current_response = client.get(
            "/api/games/current", headers=_session_headers(session_id)
        )
        assert current_response.status_code == 200
        current_body = current_response.json()
        assert current_body["current_game"] == game_id


def test_player_create_and_get_use_explicit_context():
    session_id = "test-player-session"
    with TestClient(app) as client:
        create_game = client.post(
            "/api/games/create",
            json={"world_setting": "玩家测试世界"},
            headers=_session_headers(session_id),
        )
        assert create_game.status_code == 200

        create_player = client.post(
            "/api/player/create",
            headers=_session_headers(session_id),
            json={
                "name": "测试角色",
                "strength": 12,
                "dexterity": 11,
                "constitution": 13,
                "intelligence": 10,
                "wisdom": 9,
                "charisma": 8,
                "skills": ["剑术", "说服"],
            },
        )
        assert create_player.status_code == 200
        assert create_player.json()["success"] is True

        get_player = client.get("/api/player", headers=_session_headers(session_id))
        assert get_player.status_code == 200
        body = get_player.json()
        assert body["exists"] is True
        assert body["player"]["name"] == "测试角色"


def test_chat_happy_path_mock_llm(monkeypatch):
    async def fake_generate_chat_turn(ctx, messages, request_id=None, method_name="game_chat"):
        return (
            ChatTurnContent(
                scene="测试场景",
                log="测试",
                choices=[{"text": "继续", "tendency": ["勇敢"], "is_key_decision": False}],
            ),
            '{"scene":"测试场景","log":"测试","choices":[{"text":"继续","tendency":["勇敢"],"is_key_decision":false}]}',
            False,
        )

    monkeypatch.setattr(container.llm_adapter, "generate_chat_turn", fake_generate_chat_turn)

    session_id = "test-chat-session"
    with TestClient(app) as client:
        create_game = client.post(
            "/api/games/create",
            json={"world_setting": "单元测试世界"},
            headers=_session_headers(session_id),
        )
        assert create_game.status_code == 200

        response = client.post(
            "/api/chat",
            headers=_session_headers(session_id),
            json={
                "messages": [{"role": "user", "content": "你好"}],
                "extraPrompt": "",
                "turn_context": {"tendency": {"勇敢": 2, "谨慎": 0}},
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["content"]["scene"] == "测试场景"
    assert data["meta"].get("repaired") is False


def test_request_id_header_echoed():
    with TestClient(app) as client:
        response = client.get("/api/games", headers={"X-Request-ID": "test-req-123"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-req-123"
