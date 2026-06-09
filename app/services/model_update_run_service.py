"""
PROXVEL Backend - Model Update Run Service.
"""
from typing import List, Optional, Tuple
from app.repositories import db_model_update_run_repository
from app.repositories import db_monthly_batch_repository
from app.schemas.model_update_run_schema import ModelUpdateRunCreate, ModelUpdateRunResponse

def create_run(run_data: ModelUpdateRunCreate) -> Tuple[Optional[ModelUpdateRunResponse], Optional[str]]:
    # Validate batch exists
    batch = db_monthly_batch_repository.get_batch_by_id(run_data.batch_id)
    if not batch:
        return None, "El batch_id proporcionado no existe"
        
    run = db_model_update_run_repository.create_model_update_run(run_data)
    if run:
        return ModelUpdateRunResponse.model_validate(run), None
    return None, "Error interno al registrar la ejecución externa"

def get_runs() -> List[ModelUpdateRunResponse]:
    runs = db_model_update_run_repository.get_runs()
    return [ModelUpdateRunResponse.model_validate(r) for r in runs]
