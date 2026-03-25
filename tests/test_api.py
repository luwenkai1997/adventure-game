"""API smoke tests (TestClient runs ASGI lifespan — initializes httpx client)."""

from fastapi.testclient import TestClient

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
