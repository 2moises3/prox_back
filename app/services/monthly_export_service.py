"""
PROXVEL Backend - Monthly Export Service.
"""
import os
import csv
import json
import uuid
from typing import Optional, Tuple
from app.repositories import db_monthly_batch_repository, db_review_repository
from app.schemas.monthly_export_schema import MonthlyExportRequest, MonthlyExportResponse

EXPORT_DIR = "app/exports/reviews"

def create_monthly_export(req: MonthlyExportRequest) -> Tuple[Optional[MonthlyExportResponse], Optional[str]]:
    if req.month < 1 or req.month > 12:
        return None, "Mes inválido. Debe estar entre 1 y 12."

    # Ensure export directory exists
    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    # Generate batch id
    batch_id = f"B{req.year}{req.month:02d}{uuid.uuid4().hex[:4].upper()}"
    export_path = f"{EXPORT_DIR}/reviews_{req.year}_{req.month:02d}_batch_{batch_id}.{req.format}"
    
    # Get and mark reviews
    reviews = db_review_repository.get_and_mark_reviews_for_export(req.year, req.month, batch_id)
    
    if not reviews:
        return None, "No hay reseñas pendientes para exportar en este mes"

    # Create CSV
    if req.format == "csv":
        with open(export_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Headers
            writer.writerow([
                "review_id", "user_id", "destination_id", "rating_general", 
                "review_text", "visit_date", "source", "language", 
                "is_verified_visit", "validation_method", "status", 
                "processing_month", "created_at", "aspect_ratings_json"
            ])
            for r in reviews:
                aspects = []
                for a in r.aspect_ratings:
                    aspects.append({
                        "aspect": a.aspect,
                        "rating": a.rating,
                        "comment": a.comment
                    })
                
                writer.writerow([
                    r.review_id, r.user_id, r.destination_id, r.rating_general,
                    r.review_text, r.visit_date, r.source, r.language,
                    r.is_verified_visit, r.validation_method, "exported", # Update status in CSV
                    r.processing_month, r.created_at.isoformat(), json.dumps(aspects, ensure_ascii=False)
                ])
    
    # Register batch in DB
    batch = db_monthly_batch_repository.create_batch(req.year, req.month, len(reviews), export_path)
    
    if batch:
        return MonthlyExportResponse.model_validate(batch), None
        
    return None, "Error interno al registrar el batch"

def mark_batch_used_for_training(batch_id: str) -> Tuple[bool, Optional[str]]:
    success = db_monthly_batch_repository.mark_batch_used_for_training(batch_id)
    if success:
        return True, None
    return False, "Batch no encontrado o error interno"
