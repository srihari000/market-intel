from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from app.schemas.llm import ClaimVerdict


class Theme(BaseModel):
    theme: str
    summary: str
    source_indices: list[int] = []
    verdict: ClaimVerdict = Field(default_factory=ClaimVerdict)


class CompetitorActivity(BaseModel):
    competitor: str
    activity: str
    source_index: int = 0
    verdict: ClaimVerdict = Field(default_factory=ClaimVerdict)


class HallucinationVerdict(BaseModel):
    overall_score: float = 1.0
    reasoning: str = ""

    @field_validator("overall_score")
    @classmethod
    def clamp(cls, v: float) -> float:
        return round(max(0.0, min(1.0, float(v))), 4)


class ReportOut(BaseModel):
    id: str
    run_id: str
    themes: list[Theme]
    competitor_activities: list[CompetitorActivity]
    source_urls: list[str] = []        # URL list only — raw content never sent to client
    hallucination_verdict: HallucinationVerdict
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_sources(cls, report, source_urls: list[str]) -> "ReportOut":
        return cls(
            id=report.id,
            run_id=report.run_id,
            themes=report.themes,
            competitor_activities=report.competitor_activities,
            source_urls=source_urls,
            hallucination_verdict=report.hallucination_verdict,
            created_at=report.created_at,
        )
