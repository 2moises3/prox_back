"""
PROXVEL Backend - DB Model Update Run Repository.
"""
import logging
import uuid
import json
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config.database import SessionLocal
from app.models.model_update_run_model import ModelUpdateRun
from app.schemas.model_update_run_schema import ModelUpdateRunCreate

logger = logging.getLogger(__name__)

def create_model_update_run(run_data: ModelUpdateRunCreate) -> Optional[ModelUpdateRun]:
    try:
        db = SessionLocal()
        try:
            run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
            metrics_str = json.dumps(run_data.metrics_json) if run_data.metrics_json else None
            
            new_run = ModelUpdateRun(
                run_id=run_id,
                batch_id=run_data.batch_id,
                model_name=run_data.model_name,
                metrics_json=metrics_str,
                status=run_data.status
            )
            db.add(new_run)
            db.commit()
            db.refresh(new_run)
            return new_run
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error creating model update run: {e}")
        return None

def get_runs() -> List[ModelUpdateRun]:
    try:
        db = SessionLocal()
        try:
            return list(db.scalars(select(ModelUpdateRun)).all())
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching runs: {e}")
        return []
