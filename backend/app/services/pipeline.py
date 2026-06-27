import logging
from typing import AsyncGenerator, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

from app.models.run import Run
from app.models.report import Report
from app.services.scraper import scrape_url
from app.services.analyzer import analyze
from app.services.judge import judge


class PipelineState(TypedDict):
    run_id: str
    source_urls: list
    competitors: list
    topics: list
    raw_sources: dict
    analysis: dict
    verdict: dict
    error: Optional[str]
    retry_count: int
    saved: bool  # set to True by save_node so LangGraph receives a non-empty update


# --- Nodes ---

async def scrape_node(state: PipelineState, config: RunnableConfig) -> dict:
    import asyncio
    run_id = state["run_id"]
    urls = state["source_urls"]
    logger.info("[%s] scrape_node start — %d URL(s) in parallel", run_id, len(urls))

    results = await asyncio.gather(*[scrape_url(url) for url in urls], return_exceptions=False)

    raw_sources: dict[str, str] = {}
    for url, text in zip(urls, results):
        if text:
            raw_sources[url] = text
            logger.info("[%s] scrape_node parsed: %s — %d chars | preview: %.200s", run_id, url, len(text), text[:200].replace("\n", " "))
        else:
            logger.warning("[%s] scrape_node skipped (no content): %s", run_id, url)

    if not raw_sources:
        logger.error("[%s] scrape_node failed — all URLs returned no content", run_id)
        return {"error": "All URLs failed to scrape. Check that URLs are publicly accessible.", "raw_sources": {}}
    logger.info("[%s] scrape_node done — %d/%d URLs scraped successfully", run_id, len(raw_sources), len(urls))
    return {"raw_sources": raw_sources, "error": None}


async def analyze_node(state: PipelineState, config: RunnableConfig) -> dict:
    run_id = state["run_id"]
    logger.info("[%s] analyze_node start", run_id)
    analysis = await analyze(state["raw_sources"], state["competitors"], state["topics"])
    logger.info("[%s] analyze_node done", run_id)
    return {"analysis": analysis}


async def judge_node(state: PipelineState, config: RunnableConfig) -> dict:
    run_id = state["run_id"]
    logger.info("[%s] judge_node start", run_id)
    verdict = await judge(state["analysis"], state["raw_sources"])
    score = verdict.get("overall_score", 0)
    logger.info("[%s] judge_node done — score: %.2f", run_id, score)
    return {"verdict": verdict}


async def re_analyze_node(state: PipelineState, config: RunnableConfig) -> dict:
    run_id = state["run_id"]
    retry = state.get("retry_count", 0) + 1
    logger.info("[%s] re_analyze_node start — attempt %d/2", run_id, retry)
    analysis = await analyze(state["raw_sources"], state["competitors"], state["topics"])
    logger.info("[%s] re_analyze_node done — attempt %d/2", run_id, retry)
    return {"analysis": analysis, "retry_count": retry}


def _sanitize_analysis(analysis: dict, source_count: int) -> dict:
    """Strip out-of-bounds source indices before persisting."""
    valid_indices = set(range(source_count))

    themes = []
    for t in analysis.get("themes", []):
        t["source_indices"] = [i for i in t.get("source_indices", []) if i in valid_indices]
        themes.append(t)

    activities = []
    for a in analysis.get("competitor_activities", []):
        if a.get("source_index", 0) not in valid_indices:
            a["source_index"] = 0
        activities.append(a)

    return {"themes": themes, "competitor_activities": activities}


async def save_node(state: PipelineState, config: RunnableConfig) -> dict:
    run_id = state["run_id"]
    logger.info("[%s] save_node start — persisting report to database", run_id)
    db: AsyncSession = config["configurable"]["db"]
    run: Run = config["configurable"]["run"]

    clean_analysis = _sanitize_analysis(state["analysis"], len(state["raw_sources"]))
    verdict = state["verdict"]

    default_verdict = {"status": "verified", "confidence": 1.0, "reason": ""}
    theme_verdicts = verdict.get("theme_verdicts", [])
    activity_verdicts = verdict.get("activity_verdicts", [])

    themes = clean_analysis["themes"]
    activities = clean_analysis["competitor_activities"]
    for i, theme in enumerate(themes):
        theme["verdict"] = theme_verdicts[i] if i < len(theme_verdicts) else default_verdict
    for i, activity in enumerate(activities):
        activity["verdict"] = activity_verdicts[i] if i < len(activity_verdicts) else default_verdict

    report = Report(
        run_id=run.id,
        themes=themes,
        competitor_activities=activities,
        hallucination_verdict={
            "overall_score": verdict.get("overall_score", 1.0),
            "reasoning": verdict.get("reasoning", ""),
        },
    )
    db.add(report)
    await db.execute(
        update(Run)
        .where(Run.id == run_id)
        .values(status="completed", completed_at=datetime.now(timezone.utc))
    )
    await db.commit()
    logger.info("[%s] save_node done — run marked completed", run_id)
    return {"saved": True}


# --- Routing ---

def _route_after_scrape(state: PipelineState) -> str:
    return "error" if state.get("error") else "analyze"


def _route_after_judge(state: PipelineState) -> str:
    score = state.get("verdict", {}).get("overall_score", 1.0)
    retry_count = state.get("retry_count", 0)
    if score < 0.7 and retry_count < 2:
        return "re_analyze"
    return "save"


# --- Graph ---

def _build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("scrape", scrape_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("judge", judge_node)
    graph.add_node("re_analyze", re_analyze_node)
    graph.add_node("save", save_node)

    graph.set_entry_point("scrape")
    graph.add_conditional_edges("scrape", _route_after_scrape, {"analyze": "analyze", "error": END})
    graph.add_edge("analyze", "judge")
    graph.add_conditional_edges("judge", _route_after_judge, {"re_analyze": "re_analyze", "save": "save"})
    graph.add_edge("re_analyze", "judge")
    graph.add_edge("save", END)

    return graph.compile()


_pipeline_graph = _build_graph()

_NODE_MESSAGES = {
    "scrape":     ("scraping",  None),
    "analyze":    ("analyzing", "Analyzing themes and competitor activity..."),
    "judge":      ("judging",   None),
    "re_analyze": ("analyzing", None),
    "save":       ("judging",   "Saving report..."),
}


# --- Public interface (same signature as before — routers unchanged) ---

async def run_pipeline(run: Run, db: AsyncSession) -> AsyncGenerator[dict, None]:
    logger.info("[%s] Pipeline starting — URLs: %s", run.id, run.source_urls)
    run.status = "processing"
    await db.commit()

    initial_state: PipelineState = {
        "run_id": run.id,
        "source_urls": run.source_urls,
        "competitors": run.competitors or [],
        "topics": run.topics or [],
        "raw_sources": {},
        "analysis": {},
        "verdict": {},
        "error": None,
        "retry_count": 0,
        "saved": False,
    }

    config = RunnableConfig(configurable={"db": db, "run": run})

    try:
        async for chunk in _pipeline_graph.astream(initial_state, config=config, stream_mode="updates"):
            node_name = list(chunk.keys())[0]
            node_data = chunk[node_name]

            if node_data.get("error"):
                raise RuntimeError(node_data["error"])

            step, default_msg = _NODE_MESSAGES.get(node_name, ("processing", f"Running {node_name}..."))

            # Build human-readable message from actual node output
            if node_name == "scrape":
                n = len(node_data.get("raw_sources", {}))
                message = f"Scraped {n} URL{'s' if n != 1 else ''} successfully"
            elif node_name == "judge":
                score = node_data.get("verdict", {}).get("overall_score", 1.0)
                pct = round(score * 100)
                retry = node_data.get("retry_count", initial_state.get("retry_count", 0))
                if score < 0.7 and retry < 2:
                    message = f"Confidence {pct}% — re-analyzing for better accuracy..."
                else:
                    message = f"Hallucination check complete: {pct}% confidence"
            elif node_name == "re_analyze":
                retry = node_data.get("retry_count", 1)
                message = f"Re-analysis complete (attempt {retry})"
            else:
                message = default_msg or f"Running {node_name}..."

            yield {"type": "progress", "step": step, "message": message}

        logger.info("[%s] Pipeline completed successfully", run.id)
        yield {"type": "complete", "run_id": run.id}

    except Exception as exc:
        logger.error("[%s] Pipeline failed: %s", run.id, exc, exc_info=True)
        try:
            await db.rollback()
            await db.execute(
                update(Run)
                .where(Run.id == run.id)
                .values(status="failed", error_message=str(exc)[:500])
            )
            await db.commit()
            logger.info("[%s] Run status set to failed", run.id)
        except Exception as db_exc:
            logger.error("[%s] Could not persist failed status: %s", run.id, db_exc)
        yield {"type": "error", "message": str(exc)}
