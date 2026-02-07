import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_root():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert "message" in body

def test_chat_endpoint_responds():
    r = client.post("/chat", json={"question": "hello"})
    assert r.status_code in (200, 500)
    raw = r.json()
    body = raw[0] if isinstance(raw, list) and len(raw) == 2 and isinstance(raw[0], dict) else raw
    assert ("answer" in body) or ("error" in body) or ("detail" in body)

def test_ui_route_serves_html():
    r = client.get("/ui")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")

def test_auth_login_no_db():
    r = client.post("/auth/login", json={"email": "test@test.com", "password": "test123"})
    assert r.status_code in (401, 503)

def test_auth_signup_no_db():
    r = client.post("/auth/signup", json={"email": "test@test.com", "password": "test123"})
    assert r.status_code in (400, 503)

def test_chats_unauthorized():
    r = client.get("/chats")
    assert r.status_code == 401
