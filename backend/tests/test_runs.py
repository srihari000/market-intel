import pytest

RUN_PAYLOAD = {
    "title": "Q2 AI Report",
    "competitors": ["OpenAI", "Google"],
    "topics": ["multimodal"],
    "source_urls": ["https://example.com"],
}


@pytest.mark.asyncio
async def test_create_run(client, auth_headers):
    resp = await client.post("/runs", json=RUN_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Q2 AI Report"
    assert data["status"] == "pending"
    assert data["competitors"] == ["OpenAI", "Google"]


@pytest.mark.asyncio
async def test_list_runs(client, auth_headers):
    await client.post("/runs", json=RUN_PAYLOAD, headers=auth_headers)
    resp = await client.get("/runs", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["runs"][0]["title"] == "Q2 AI Report"


@pytest.mark.asyncio
async def test_get_run(client, auth_headers):
    create_resp = await client.post("/runs", json=RUN_PAYLOAD, headers=auth_headers)
    run_id = create_resp.json()["id"]
    resp = await client.get(f"/runs/{run_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


@pytest.mark.asyncio
async def test_get_run_not_found(client, auth_headers):
    resp = await client.get("/runs/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_run(client, auth_headers):
    create_resp = await client.post("/runs", json=RUN_PAYLOAD, headers=auth_headers)
    run_id = create_resp.json()["id"]
    resp = await client.delete(f"/runs/{run_id}", headers=auth_headers)
    assert resp.status_code == 204
    assert (await client.get(f"/runs/{run_id}", headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_runs_require_auth(client):
    resp = await client.get("/runs")
    assert resp.status_code == 403
