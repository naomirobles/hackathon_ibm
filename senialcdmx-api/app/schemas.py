from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ReportCreate(BaseModel):
    description: str
    street: str
    ext_number: str
    int_number: str | None = None
    postal_code: str
    alcaldia: str
    colonia: str
    between_street_1: str | None = None
    between_street_2: str | None = None
    lat: float | None = None
    lng: float | None = None


class ReportCreatedResponse(BaseModel):
    report_id: int
    status: str


class LayersSummary(BaseModel):
    matched_layers: list[str]
    findings: list[str]


class ReportResponse(BaseModel):
    report_id: int
    status: str
    category: str | None = None
    priority: str | None = None
    lat: float | None = None
    lng: float | None = None
    analysis: str | None = None
    layers_summary: LayersSummary | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
