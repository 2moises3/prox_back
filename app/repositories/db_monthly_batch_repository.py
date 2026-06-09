"""
PROXVEL Backend - DB Monthly Batch Repository.
"""
import logging
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config.database import SessionLocal
from app.models.monthly_review_batch_model import MonthlyReviewBatch
from app.models.review_model import Review

logger = logging.getLogger(__name__)

def create_batch(year: int, month: int, total_reviews: int, export_path: str) -> Optional[MonthlyReviewBatch]:
    try:
        db = SessionLocal()
        try:
            batch_id = f"B{year}{month:02d}{uuid.uuid4().hex[:4].upper()}"
            new_batch = MonthlyReviewBatch(
                batch_id=batch_id,
                year=year,
                month=month,
                total_reviews=total_reviews,
                status="exported",
                export_path=export_path
            )
            db.add(new_batch)
            db.commit()
            db.refresh(new_batch)
            return new_batch
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error creating batch: {e}")
        return None

def get_batches() -> List[MonthlyReviewBatch]:
    try:
        db = SessionLocal()
        try:
            return list(db.scalars(select(MonthlyReviewBatch)).all())
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching batches: {e}")
        return []

def get_batch_by_id(batch_id: str) -> Optional[MonthlyReviewBatch]:
    try:
        db = SessionLocal()
        try:
            return db.scalar(select(MonthlyReviewBatch).where(MonthlyReviewBatch.batch_id == batch_id))
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching batch: {e}")
        return None

def mark_batch_used_for_training(batch_id: str) -> bool:
    try:
        db = SessionLocal()
        try:
            batch = db.scalar(select(MonthlyReviewBatch).where(MonthlyReviewBatch.batch_id == batch_id))
            if not batch:
                return False
            
            batch.status = "used_for_training"
            
            # Update associated reviews
            reviews = db.scalars(select(Review).where(Review.training_batch_id == batch_id)).all()
            for r in reviews:
                r.status = "processed"
            
            db.commit()
            return True
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error marking batch used for training: {e}")
        return False
