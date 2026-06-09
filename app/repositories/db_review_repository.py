"""
PROXVEL Backend - DB Review Repository.
"""
import logging
import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.config.database import SessionLocal
from app.models.review_model import Review
from app.models.review_aspect_rating_model import ReviewAspectRating
from app.schemas.review_schema import ReviewCreate

logger = logging.getLogger(__name__)

def create_review(review_data: ReviewCreate) -> Optional[Review]:
    try:
        db = SessionLocal()
        try:
            review_id = f"rev-{uuid.uuid4().hex[:8]}"
            now = datetime.utcnow()
            processing_month = now.strftime("%Y-%m")
            
            new_review = Review(
                review_id=review_id,
                user_id=review_data.user_id,
                destination_id=review_data.destination_id,
                rating_general=review_data.rating_general,
                review_text=review_data.review_text,
                visit_date=review_data.visit_date,
                language=review_data.language,
                is_verified_visit=review_data.is_verified_visit,
                validation_method="self_report_pending",
                status="pending_processing",
                processing_month=processing_month,
                source="app",
            )
            db.add(new_review)
            
            for aspect_rating in review_data.aspect_ratings:
                ar = ReviewAspectRating(
                    review_id=review_id,
                    aspect=aspect_rating.aspect,
                    rating=aspect_rating.rating,
                    comment=aspect_rating.comment
                )
                db.add(ar)
                
            db.commit()
            db.refresh(new_review)
            # Fetch with relationship for response
            return db.scalar(
                select(Review).options(joinedload(Review.aspect_ratings)).where(Review.id == new_review.id)
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error creating review: {e}")
        return None

def get_review_by_id(review_id: str) -> Optional[Review]:
    try:
        db = SessionLocal()
        try:
            return db.scalar(
                select(Review).options(joinedload(Review.aspect_ratings)).where(Review.review_id == review_id)
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching review by id: {e}")
        return None

def get_reviews_by_destination(destination_id: str) -> List[Review]:
    try:
        db = SessionLocal()
        try:
            return list(db.scalars(
                select(Review).options(joinedload(Review.aspect_ratings)).where(Review.destination_id == destination_id)
            ).unique().all())
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching reviews by destination: {e}")
        return []

def get_reviews_by_user(user_id: str) -> List[Review]:
    try:
        db = SessionLocal()
        try:
            return list(db.scalars(
                select(Review).options(joinedload(Review.aspect_ratings)).where(Review.user_id == user_id)
            ).unique().all())
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching reviews by user: {e}")
        return []

def get_pending_reviews() -> List[Review]:
    try:
        db = SessionLocal()
        try:
            return list(db.scalars(
                select(Review).options(joinedload(Review.aspect_ratings)).where(Review.status == "pending_processing")
            ).unique().all())
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching pending reviews: {e}")
        return []

def get_and_mark_reviews_for_export(year: int, month: int, batch_id: str) -> List[Review]:
    try:
        db = SessionLocal()
        try:
            processing_month_str = f"{year}-{month:02d}"
            
            # Find all pending reviews matching the processing month
            # Or any pending review if we want to catch up, but the requirement says:
            # "Solo exportar reseñas del año/mes indicado según processing_month o created_at"
            reviews = db.scalars(
                select(Review)
                .options(joinedload(Review.aspect_ratings))
                .where(Review.status == "pending_processing")
                .where(Review.processing_month == processing_month_str)
            ).unique().all()
            
            if not reviews:
                return []
                
            # Mark them as exported and assign batch_id
            for r in reviews:
                r.status = "exported"
                r.training_batch_id = batch_id
                
            db.commit()
            return list(reviews)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error exporting reviews: {e}")
        return []
