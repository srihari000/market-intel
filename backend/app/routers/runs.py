import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.run import Run
from app.models.report import Report
from app.schemas.run import RunCreate, RunOut, RunListOut
from app.schemas.report import ReportOut
from app.utils.security import get_current_user, get_current_user_from_token
from app.models.user import User

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunOut, status_code=201)
async def create_run(
    body: RunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = Run(
        user_id=current_user.id,
        title=body.title,
        competitors=body.competitors,
        topics=body.topics,
        source_urls=body.source_urls,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.get("", response_model=RunListOut)
async def list_runs(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Run)
        .where(Run.user_id == current_user.id)
        .order_by(desc(Run.created_at))
        .offset(skip)
        .limit(limit)
    )
    runs = list(result.scalars().all())
    return RunListOut(runs=runs, total=len(runs))


@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Run).where(Run.id == run_id, Run.user_id == current_user.id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/report", response_model=ReportOut)
async def get_report(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Run).where(Run.id == run_id, Run.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Run not found")
    result = await db.execute(select(Report).where(Report.run_id == run_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not ready")
    return report


@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Run).where(Run.id == run_id, Run.user_id == current_user.id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    await db.delete(run)
    await db.commit()


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    from app.services.pipeline import run_pipeline

    current_user = await get_current_user_from_token(token, db)
    result = await db.execute(select(Run).where(Run.id == run_id, Run.user_id == current_user.id))
    run = result.scalar_one_or_none()

    if not run:
        async def not_found():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Run not found'})}\n\n"
        return StreamingResponse(not_found(), media_type="text/event-stream")

    async def event_generator():
        async for event in run_pipeline(run, db):
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
