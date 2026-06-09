"""
PROXVEL Backend - Model Update Run Schemas.
"""
from pydantic import BaseModel
from typing import Optional, Any, Dict

class ModelUpdateRunCreate(BaseModel):
    batch_id: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    training_data_path: Optional[str] = None
    metrics_json: Optional[Dict[str, Any]] = None
    status: str
    notes: Optional[str] = None

class ModelUpdateRunResponse(BaseModel):
    run_id: str
    batch_id: str
    model_name: Optional[str] = None
    metrics_json: Optional[str] = None
    status: str

    class Config:
        from_attributes = True
