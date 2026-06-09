"""
PROXVEL Backend - Tourism Routes.
Endpoints del catálogo turístico oficial (información complementaria).
No afecta los scores ni el ranking de recomendación de tesis.
"""

from fastapi import APIRouter, HTTPException

from app.services import tourism_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/tourism", tags=["Tourism Catalog"])


@router.get(
    "/catalog",
    summary="Catálogo turístico oficial",
    description=(
        "Devuelve la lista de destinos del catálogo turístico oficial "
        "con información de MINCETUR. Este catálogo es complementario "
        "y no afecta los scores de recomendación de tesis."
    ),
)
def get_catalog():
    """Lista todos los destinos del catálogo turístico."""
    catalog = tourism_service.get_catalog()
    return success_response(
        data=catalog,
        message="Catálogo turístico obtenido correctamente",
    )


@router.get(
    "/catalog/{destination_id}",
    summary="Detalle turístico de un destino",
    description=(
        "Devuelve la ficha turística oficial de un destino "
        "con información de fuentes MINCETUR."
    ),
)
def get_catalog_detail(destination_id: str):
    """Obtiene el detalle turístico de un destino."""
    detail = tourism_service.get_catalog_detail(destination_id)

    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"Destino no encontrado en catálogo turístico: {destination_id}",
        )

    return success_response(
        data=detail,
        message="Detalle turístico obtenido correctamente",
    )


@router.get(
    "/map-markers",
    summary="Marcadores de mapa",
    description=(
        "Devuelve solo destinos con coordenadas geográficas válidas. "
        "Si las coordenadas están como PENDIENTE, no se incluyen."
    ),
)
def get_map_markers():
    """Obtiene marcadores de mapa con coordenadas válidas."""
    markers = tourism_service.get_map_markers()

    if not markers:
        return success_response(
            data=[],
            message="No hay marcadores disponibles porque las coordenadas están pendientes.",
            count=0,
        )

    return success_response(
        data=markers,
        message="Marcadores de mapa obtenidos correctamente",
    )
