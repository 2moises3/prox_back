"""
PROXVEL Backend - Media Upload Schemas.
"""
from typing import Optional
from pydantic import BaseModel

class MediaUploadResponse(BaseModel):
    success: bool
    message: str
    media: dict

class MediaPatchRequest(BaseModel):
    position: Optional[int] = None
    alt_text: Optional[str] = None
    credit: Optional[str] = None
    license_note: Optional[str] = None
    is_active: Optional[bool] = None
