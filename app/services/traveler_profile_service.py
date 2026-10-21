"""
PROXVEL Backend - Traveler Profile Service.
"""
from typing import Optional
from app.repositories import db_traveler_profile_repository, db_user_repository
from app.schemas.traveler_profile_schema import TravelerProfileResponse, TravelerProfileCreate, TravelerProfileUpdate

def get_profile_by_user_id(user_id: str) -> tuple[Optional[TravelerProfileResponse], Optional[str]]:
    # Validar que el usuario exista
    user = db_user_repository.get_user_by_id(user_id)
    if not user:
        return None, "Usuario no encontrado"

    profile = db_traveler_profile_repository.get_profile_by_user_id(user_id)
    if not profile:
        return None, "Perfil viajero no existe"
        
    return TravelerProfileResponse.model_validate(profile), None

def update_profile(user_id: str, profile_data: TravelerProfileUpdate, is_partial: bool = False) -> tuple[Optional[TravelerProfileResponse], Optional[str]]:
    # Validar que el usuario exista
    user = db_user_repository.get_user_by_id(user_id)
    if not user:
        return None, "Usuario no encontrado"
        
    # Verificar si el perfil existe para el PATCH
    if is_partial:
        existing_profile = db_traveler_profile_repository.get_profile_by_user_id(user_id)
        if not existing_profile:
            return None, "Perfil viajero no existe"
            
    # exclude_unset=True for PATCH, so we only send what was provided
    # For PUT (is_partial=False), exclude_unset=False to get all fields, even if None
    update_dict = profile_data.model_dump(exclude_unset=is_partial)

    # Los pesos peso_* solo cambian si el viajero los envía. El backend ya no los deriva:
    # el motor los toma como "sliders ajustados por el viajero" cuando no son iguales, y
    # unos pesos inventados aquí reemplazaban los pesos por tipo de viajero de la tesis.

    profile = db_traveler_profile_repository.create_or_update_profile(user_id, update_dict, is_partial)
    
    if profile:
        return TravelerProfileResponse.model_validate(profile), None
        
    return None, "Error interno al guardar el perfil viajero"
