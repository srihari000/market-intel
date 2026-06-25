import pytest
from unittest.mock import AsyncMock, patch
from app.models.user import User
from app.models.run import Run
from app.utils.security import hash_password


async def make_user_and_run(db_session, email: str, urls: list):
    user = User(email=email, password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    run = Run(user_id=user.id, title="Test", competitors=["OpenAI"], topics=["AI"], source_urls=urls)
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


@pytest.mark.asyncio
async def test_pipeline_completes_successfully(db_session):
    from app.services.pipeline import run_pipeline

    run = await make_user_and_run(db_session, "pipe1@test.com", ["https://example.com"])

    with patch("app.services.pipeline.scrape_url", new=AsyncMock(return_value="OpenAI launched new model.")):
        with patch("app.services.pipeline.analyze", new=AsyncMock(return_value={
            "themes": [{"theme": "AI", "summary": "Growing.", "source_indices": [0]}],
            "competitor_activities": [{"competitor": "OpenAI", "activity": "launched model", "source_index": 0}],
        })):
            with patch("app.services.pipeline.judge", new=AsyncMock(return_value={
                "score": 1.0, "flagged_claims": [], "reasoning": "All verified.",
            })):
                events = [e async for e in run_pipeline(run, db_session)]

    types = [e["type"] for e in events]
    assert "complete" in types
    assert run.status == "completed"
    assert run.completed_at is not None


@pytest.mark.asyncio
async def test_pipeline_fails_when_all_urls_unreachable(db_session):
    from app.services.pipeline import run_pipeline

    run = await make_user_and_run(db_session, "pipe2@test.com", ["https://bad.invalid"])

    with patch("app.services.pipeline.scrape_url", new=AsyncMock(return_value=None)):
        events = [e async for e in run_pipeline(run, db_session)]

    types = [e["type"] for e in events]
    assert "error" in types
    assert run.status == "failed"
