"""
PROXVEL Backend - Visit & Atlas Schemas.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    destination_id: str
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitud GPS actual del usuario")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitud GPS actual del usuario")


class VerifyVisitRequest(BaseModel):
    visit_id: str
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitud GPS actual del usuario")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitud GPS actual del usuario")


class VisitResponse(BaseModel):
    visit_id: str
    destination_id: str
    destination_name: Optional[str] = None
    visit_status: str
    validation_method: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dwell_minutes: int = 0
    min_dwell_minutes: int = 20
    remaining_minutes: int = 0
    distance_meters: Optional[float] = None
    geofence_radius_meters: Optional[int] = None

    class Config:
        from_attributes = True


class AtlasItemResponse(BaseModel):
    visit_id: str
    destination_id: str
    destination_name: str
    region: Optional[str] = None
    city: Optional[str] = None
    category: Optional[str] = None
    cover_image_url: Optional[str] = None
    completed_at: datetime
    dwell_minutes: int
    validation_method: str

    class Config:
        from_attributes = True


class AtlasSummaryResponse(BaseModel):
    total_verified_visits: int
    regions_visited: int
    visits: List[AtlasItemResponse]
