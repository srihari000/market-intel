import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/auth/register", json={"email": "new@example.com", "password": "pass123"})
    assert resp.status_code == 201
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/auth/register", json={"email": "dup@example.com", "password": "pass123"})
    resp = await client.post("/auth/register", json={"email": "dup@example.com", "password": "pass123"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/auth/register", json={"email": "login@example.com", "password": "pass123"})
    resp = await client.post("/auth/login", json={"email": "login@example.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/auth/register", json={"email": "wp@example.com", "password": "pass123"})
    resp = await client.post("/auth/login", json={"email": "wp@example.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user(client, auth_headers):
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403
