from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RunCreate(BaseModel):
    title: str
    competitors: list[str] = []
    topics: list[str] = []
    source_urls: list[str]


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
