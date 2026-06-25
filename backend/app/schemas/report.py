from pydantic import BaseModel
from datetime import datetime


class Theme(BaseModel):
    theme: str
    summary: str
    source_indices: list[int]


class CompetitorActivity(BaseModel):
    competitor: str
    activity: str
    source_index: int


class FlaggedClaim(BaseModel):
    claim: str
    reason: str


class HallucinationVerdict(BaseModel):
    score: float
    flagged_claims: list[FlaggedClaim]
    reasoning: str


class ReportOut(BaseModel):
    id: str
    run_id: str
    themes: list[Theme]
    competitor_activities: list[CompetitorActivity]
    raw_sources: dict[str, str]
    hallucination_verdict: HallucinationVerdict
    created_at: datetime

    model_config = {"from_attributes": True}
