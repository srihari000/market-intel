from pydantic import BaseModel, field_validator, HttpUrl
from typing import Optional
from datetime import datetime


class RunCreate(BaseModel):
    title: str
    competitors: list[str] = []
    topics: list[str] = []
    source_urls: list[str]

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        if len(v) > 255:
            raise ValueError("Title must be under 255 characters")
        return v

    @field_validator("source_urls")
    @classmethod
    def validate_urls(cls, urls: list[str]) -> list[str]:
        if not urls:
            raise ValueError("At least one source URL is required")
        if len(urls) > 10:
            raise ValueError("Maximum 10 source URLs allowed")
        for url in urls:
            url = url.strip()
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"URL must start with http:// or https://: {url}")
            try:
                HttpUrl(url)
            except Exception:
                raise ValueError(f"Invalid URL: {url}")
        return [u.strip() for u in urls]

    @field_validator("competitors")
    @classmethod
    def validate_competitors(cls, v: list[str]) -> list[str]:
        if len(v) > 20:
            raise ValueError("Maximum 20 competitors allowed")
        return [c.strip()[:100] for c in v if c.strip()]

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: list[str]) -> list[str]:
        if len(v) > 20:
            raise ValueError("Maximum 20 topics allowed")
        return [t.strip()[:100] for t in v if t.strip()]


class RunOut(BaseModel):
    id: str
    title: str
    competitors: list[str]
    topics: list[str]
    source_urls: list[str]
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RunListOut(BaseModel):
    runs: list[RunOut]
    total: int
