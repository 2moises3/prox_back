"""
PROXVEL Backend - Monthly Export Schemas.
"""
from pydantic import BaseModel
from typing import Optional

class MonthlyExportRequest(BaseModel):
    year: int
    month: int
    format: str = "csv"

class MonthlyExportResponse(BaseModel):
    batch_id: str
    year: int
    month: int
    total_reviews: int
    status: str
    export_path: Optional[str] = None

    class Config:
        from_attributes = True
