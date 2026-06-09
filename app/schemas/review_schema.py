"""
PROXVEL Backend - Review Schemas.
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class AspectRatingCreate(BaseModel):
    aspect: str
    rating: float = Field(..., ge=1.0, le=5.0)
    comment: Optional[str] = None

class ReviewCreate(BaseModel):
    user_id: str
    destination_id: str
    rating_general: float = Field(..., ge=1.0, le=5.0)
    review_text: str = Field(..., min_length=1)
    visit_date: Optional[str] = None
    language: str = "es"
    is_verified_visit: bool = False
    aspect_ratings: List[AspectRatingCreate] = []

class AspectRatingResponse(BaseModel):
    aspect: str
    rating: float
    comment: Optional[str]

    class Config:
        from_attributes = True

class ReviewResponse(BaseModel):
    review_id: str
    user_id: str
    destination_id: str
    rating_general: float
    review_text: str
    status: str
    processing_month: Optional[str]
    aspect_ratings: List[AspectRatingResponse] = []

    class Config:
        from_attributes = True
