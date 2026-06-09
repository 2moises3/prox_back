"""
PROXVEL Backend - Admin Training Routes.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List

from app.services import monthly_export_service, model_update_run_service
from app.schemas.monthly_export_schema import MonthlyExportRequest
from app.schemas.model_update_run_schema import ModelUpdateRunCreate
from app.utils.response_builder import success_response
from app.repositories import db_monthly_batch_repository

router = APIRouter(prefix="/admin", tags=["Admin Training"])

@router.post("/training-batches/monthly", response_model=dict, summary="Exportar batch mensual")
def create_monthly_batch(req: MonthlyExportRequest):
    batch, error = monthly_export_service.create_monthly_export(req)
    if error:
        # success false for no pending reviews
        if "No hay reseñas pendientes" in error:
            return {
                "success": False,
                "message": error,
                "data": None
            }
        raise HTTPException(status_code=422, detail=error)
    return success_response(data=batch.model_dump(), message="Batch mensual exportado correctamente")

@router.get("/training-batches", response_model=dict, summary="Listar batches")
def get_batches():
    batches = db_monthly_batch_repository.get_batches()
    return success_response(data=[{"batch_id": b.batch_id, "year": b.year, "month": b.month, "status": b.status, "export_path": b.export_path, "total_reviews": b.total_reviews} for b in batches], message="Batches listados")

@router.get("/training-batches/{batch_id}", response_model=dict, summary="Detalle de batch")
def get_batch(batch_id: str):
    batch = db_monthly_batch_repository.get_batch_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch no encontrado")
    return success_response(data={"batch_id": batch.batch_id, "year": batch.year, "month": batch.month, "status": batch.status, "export_path": batch.export_path, "total_reviews": batch.total_reviews}, message="Batch obtenido")

@router.patch("/training-batches/{batch_id}/mark-used-for-training", response_model=dict, summary="Marcar batch como usado")
def mark_batch_used(batch_id: str):
    success, error = monthly_export_service.mark_batch_used_for_training(batch_id)
    if not success:
        raise HTTPException(status_code=404, detail=error)
    return success_response(data={"batch_id": batch_id, "status": "used_for_training"}, message="Batch marcado como usado para entrenamiento")

@router.post("/model-update-runs", response_model=dict, summary="Registrar actualización de modelo")
def register_model_update(run: ModelUpdateRunCreate):
    created_run, error = model_update_run_service.create_run(run)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return success_response(data=created_run.model_dump(), message="Ejecución externa registrada correctamente")

@router.get("/model-update-runs", response_model=dict, summary="Listar ejecuciones de modelo")
def get_model_runs():
    runs = model_update_run_service.get_runs()
    return success_response(data=[r.model_dump() for r in runs], message="Ejecuciones obtenidas")
