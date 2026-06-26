from pydantic import BaseModel, field_validator


class Theme(BaseModel):
    theme: str
    summary: str
    source_indices: list[int] = []

    @field_validator("theme", "summary")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty")
        return v


class CompetitorActivity(BaseModel):
    competitor: str
    activity: str
    source_index: int = 0

    @field_validator("competitor", "activity")
    @classmethod
    def not_empty(cls, v: str) -> str:
        return v.strip()


class AnalysisOutput(BaseModel):
    themes: list[Theme] = []
    competitor_activities: list[CompetitorActivity] = []


class ClaimVerdict(BaseModel):
    status: str = "verified"  # "verified" or "flagged"
    confidence: float = 1.0
    reason: str = ""

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        return v if v in ("verified", "flagged") else "verified"

    @field_validator("confidence")
    @classmethod
    def clamp(cls, v: float) -> float:
        return round(max(0.0, min(1.0, float(v))), 4)


class JudgeOutput(BaseModel):
    theme_verdicts: list[ClaimVerdict] = []
    activity_verdicts: list[ClaimVerdict] = []
    overall_score: float = 1.0
    reasoning: str = ""

    @field_validator("overall_score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return round(max(0.0, min(1.0, float(v))), 4)
