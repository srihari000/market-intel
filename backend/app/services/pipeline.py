from typing import AsyncGenerator
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.run import Run
from app.models.report import Report
from app.services.scraper import scrape_url
from app.services.analyzer import analyze
from app.services.judge import judge


async def run_pipeline(run: Run, db: AsyncSession) -> AsyncGenerator[dict, None]:
    run.status = "processing"
    await db.commit()

    try:
        raw_sources: dict[str, str] = {}
        for i, url in enumerate(run.source_urls):
            yield {"type": "progress", "step": "scraping", "message": f"Scraping URL {i + 1}/{len(run.source_urls)}: {url}"}
            text = await scrape_url(url)
            if text:
                raw_sources[url] = text
            else:
                yield {"type": "progress", "step": "scraping", "message": f"Could not scrape {url} — skipping"}

        if not raw_sources:
            raise RuntimeError("All URLs failed to scrape. Check that the URLs are publicly accessible.")

        yield {"type": "progress", "step": "analyzing", "message": "Analyzing themes and competitor activity..."}
        analysis = await analyze(raw_sources, run.competitors or [], run.topics or [])

        yield {"type": "progress", "step": "judging", "message": "Running hallucination check..."}
        verdict = await judge(analysis, raw_sources)

        report = Report(
            run_id=run.id,
            themes=analysis.get("themes", []),
            competitor_activities=analysis.get("competitor_activities", []),
            raw_sources=raw_sources,
            hallucination_verdict=verdict,
        )
        db.add(report)
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()

        yield {"type": "complete", "run_id": run.id}

    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        await db.commit()
        yield {"type": "error", "message": str(exc)}
