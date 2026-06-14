"""
PROXVEL Backend - Traveler Profile Service.
"""
from typing import Optional
from app.repositories import db_traveler_profile_repository, db_user_repository
from app.schemas.traveler_profile_schema import TravelerProfileResponse, TravelerProfileCreate, TravelerProfileUpdate

def derive_profile_weights(data: dict) -> dict:
    """Deriva los pesos ABSA (1.0 a 5.0) en base a las preferencias explícitas del usuario."""
    # Pesos base
    weights = {
        "peso_accesibilidad": 3.0,
        "peso_aforo_multitudes": 3.0,
        "peso_alojamiento": 3.0,
        "peso_atencion_servicio": 3.0,
        "peso_atractivos": 3.0,
        "peso_clima": 3.0,
        "peso_costos": 3.0,
        "peso_gastronomia": 3.0,
        "peso_limpieza": 3.0,
        "peso_seguridad": 3.0,
    }
    
    presupuesto = data.get("presupuesto", "").lower() if data.get("presupuesto") else ""
    if presupuesto == "bajo":
        weights["peso_costos"] = 5.0
        weights["peso_alojamiento"] = 2.0
    elif presupuesto == "alto":
        weights["peso_costos"] = 1.0
        weights["peso_alojamiento"] = 5.0
        weights["peso_atencion_servicio"] = 4.0
        
    clima = data.get("clima_preferido", "").lower() if data.get("clima_preferido") else ""
    if clima in ["frio", "cálido", "calido"]:
        weights["peso_clima"] = 5.0
        
    tolerancia = data.get("tolerancia_multitudes", "").lower() if data.get("tolerancia_multitudes") else ""
    if tolerancia == "bajo":
        weights["peso_aforo_multitudes"] = 5.0
        
    intereses = data.get("intereses", [])
    if not isinstance(intereses, list):
        intereses = []
        
    # Combinar pesos por interés
    for interes in intereses:
        interes_low = interes.lower()
        if interes_low == "cultural":
            weights["peso_atractivos"] = max(weights["peso_atractivos"], 5.0)
        elif interes_low == "naturaleza":
            weights["peso_atractivos"] = max(weights["peso_atractivos"], 4.5)
            weights["peso_clima"] = max(weights["peso_clima"], 4.5)
        elif interes_low in ["gastronomico", "gastronomía", "gastronomia"]:
            weights["peso_gastronomia"] = max(weights["peso_gastronomia"], 5.0)
        elif interes_low == "aventura":
            weights["peso_accesibilidad"] = max(weights["peso_accesibilidad"], 4.0)
            weights["peso_atractivos"] = max(weights["peso_atractivos"], 4.5)
            weights["peso_seguridad"] = max(weights["peso_seguridad"], 4.5)
        elif interes_low == "relax":
            weights["peso_alojamiento"] = max(weights["peso_alojamiento"], 4.5)
            weights["peso_limpieza"] = max(weights["peso_limpieza"], 4.5)
            weights["peso_aforo_multitudes"] = max(weights["peso_aforo_multitudes"], 4.5)
            
    # clamp 1.0 to 5.0 just in case
    for k, v in weights.items():
        weights[k] = max(1.0, min(5.0, v))
        
    return weights

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
    
    # Derive weights before saving
    derived_weights = derive_profile_weights(update_dict)
    update_dict.update(derived_weights)
    
    profile = db_traveler_profile_repository.create_or_update_profile(user_id, update_dict, is_partial)
    
    if profile:
        return TravelerProfileResponse.model_validate(profile), None
        
    return None, "Error interno al guardar el perfil viajero"
