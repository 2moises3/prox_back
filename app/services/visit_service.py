"""
PROXVEL Backend - Visit & Atlas Service.
Lógica de verificación de presencia por geolocalización y compilación del Atlas de Visitas.
"""
import math
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.repositories import db_visit_repository
from app.services import destination_media_service


@contextmanager
def _get_db_context(db_session: Optional[Session] = None):
    if db_session is not None:
        yield db_session
    else:
        with SessionLocal() as session:
            yield session


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia ortodrómica en metros entre dos puntos geográficos (Haversine)."""
    r_earth = 6371000.0  # Radio medio de la Tierra en metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_earth * c


def check_in_visit(
    user_id: str,
    destination_id: str,
    latitude: float,
    longitude: float,
    db: Optional[Session] = None,
) -> Tuple[Optional[dict], Optional[str], int]:
    """Inicia o recupera el check-in de visita dentro del radio del destino."""
    with _get_db_context(db) as session:
        dest = session.query(Destination).filter(Destination.destination_id == destination_id).first()
        if not dest:
            return None, "Destino turístico no encontrado", 404

        catalog = session.query(TourismCatalog).filter(TourismCatalog.destination_id == destination_id).first()
        dest_lat = (catalog.latitude if catalog else None) or getattr(dest, "latitude", None)
        dest_lon = (catalog.longitude if catalog else None) or getattr(dest, "longitude", None)

        if dest_lat is None or dest_lon is None:
            return None, "El destino aún no tiene coordenadas de acceso configuradas", 422

        radius = (catalog.geofence_radius_meters if catalog and catalog.geofence_radius_meters else 250)
        min_dwell = (catalog.min_dwell_minutes if catalog and catalog.min_dwell_minutes else 20)

        distance = haversine_distance_meters(latitude, longitude, dest_lat, dest_lon)
        if distance > radius:
            return (
                None,
                f"Te encuentras a {int(distance)} m del destino. Debes estar a menos de {radius} m para registrar tu visita.",
                422,
            )

        # Verificar si ya existe una visita en progreso para este usuario en este destino
        existing = db_visit_repository.get_active_visit_by_user(user_id, destination_id, db=session)
        now = datetime.now(timezone.utc)
        if existing:
            started = existing.started_at
            if started and started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            elif started is None:
                started = now

            elapsed_min = max(0, int((now - started).total_seconds() / 60))
            remaining = max(0, min_dwell - elapsed_min)
            return {
                "visit_id": existing.visit_id,
                "destination_id": destination_id,
                "destination_name": dest.destination,
                "visit_status": existing.visit_status,
                "validation_method": existing.validation_method or "gps_geofence",
                "started_at": started,
                "completed_at": existing.completed_at,
                "dwell_minutes": elapsed_min,
                "min_dwell_minutes": min_dwell,
                "remaining_minutes": remaining,
                "distance_meters": round(distance, 1),
                "geofence_radius_meters": radius,
            }, None, 200

        # Crear nueva visita en progreso
        new_vid = f"vis-{uuid.uuid4().hex[:8]}"
        created = db_visit_repository.create_visit(
            visit_id=new_vid,
            user_id=user_id,
            destination_id=destination_id,
            entry_latitude=latitude,
            entry_longitude=longitude,
            validation_method="gps_geofence",
            started_at=now,
            db=session,
        )

        return {
            "visit_id": created.visit_id,
            "destination_id": destination_id,
            "destination_name": dest.destination,
            "visit_status": created.visit_status,
            "validation_method": "gps_geofence",
            "started_at": now,
            "completed_at": None,
            "dwell_minutes": 0,
            "min_dwell_minutes": min_dwell,
            "remaining_minutes": min_dwell,
            "distance_meters": round(distance, 1),
            "geofence_radius_meters": radius,
        }, None, 201


def verify_visit(
    user_id: str,
    visit_id: str,
    latitude: float,
    longitude: float,
    db: Optional[Session] = None,
) -> Tuple[Optional[dict], Optional[str], int]:
    """Sella y certifica una visita cumplido el tiempo mínimo de permanencia."""
    with _get_db_context(db) as session:
        visit = db_visit_repository.get_visit_by_id(visit_id, db=session)
        if not visit:
            return None, "Visita no encontrada", 404

        if visit.user_id != user_id:
            return None, "No tienes permiso para certificar esta visita", 403

        if visit.visit_status == "verified":
            dest = session.query(Destination).filter(Destination.destination_id == visit.destination_id).first()
            return {
                "visit_id": visit.visit_id,
                "destination_id": visit.destination_id,
                "destination_name": dest.destination if dest else visit.destination_id,
                "visit_status": "verified",
                "validation_method": visit.validation_method or "gps_geofence",
                "started_at": visit.started_at,
                "completed_at": visit.completed_at,
                "dwell_minutes": visit.dwell_minutes or 0,
                "remaining_minutes": 0,
            }, None, 200

        catalog = session.query(TourismCatalog).filter(TourismCatalog.destination_id == visit.destination_id).first()
        min_dwell = (catalog.min_dwell_minutes if catalog and catalog.min_dwell_minutes else 20)
        radius = (catalog.geofence_radius_meters if catalog and catalog.geofence_radius_meters else 250)

        # Calcular tiempo transcurrido
        now = datetime.now(timezone.utc)
        started = visit.started_at
        if started is None:
            started = now
        elif started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)

        elapsed_seconds = (now - started).total_seconds()
        elapsed_minutes = elapsed_seconds / 60.0

        # Margen de 1 minuto de tolerancia por latencia de red
        if elapsed_minutes < (min_dwell - 1):
            remaining = int(math.ceil(min_dwell - elapsed_minutes))
            return (
                None,
                f"Aún faltan {remaining} minuto(s) para validar tu visita a este destino.",
                422,
            )

        # Verificar proximidad al momento de completar
        dest = session.query(Destination).filter(Destination.destination_id == visit.destination_id).first()
        dest_lat = (catalog.latitude if catalog else None) or getattr(dest, "latitude", None)
        dest_lon = (catalog.longitude if catalog else None) or getattr(dest, "longitude", None)
        if dest_lat is not None and dest_lon is not None:
            distance = haversine_distance_meters(latitude, longitude, dest_lat, dest_lon)
            if distance > radius * 2.0:
                return (
                    None,
                    f"Te has alejado demasiado del destino ({int(distance)} m) para validar la visita.",
                    422,
                )

        final_dwell = max(min_dwell, int(round(elapsed_minutes)))
        completed = db_visit_repository.complete_visit(
            visit_id=visit.visit_id,
            dwell_minutes=final_dwell,
            completed_at=now,
            db=session,
        )

        return {
            "visit_id": completed.visit_id,
            "destination_id": completed.destination_id,
            "destination_name": dest.destination if dest else completed.destination_id,
            "visit_status": "verified",
            "validation_method": completed.validation_method or "gps_geofence",
            "started_at": completed.started_at,
            "completed_at": completed.completed_at,
            "dwell_minutes": completed.dwell_minutes,
            "min_dwell_minutes": min_dwell,
            "remaining_minutes": 0,
        }, None, 200


def get_active_visit(user_id: str, db: Optional[Session] = None) -> Optional[dict]:
    """Obtiene la visita en progreso activa del usuario si existe."""
    with _get_db_context(db) as session:
        visit = db_visit_repository.get_active_visit_by_user(user_id, db=session)
        if not visit:
            return None
        dest = session.query(Destination).filter(Destination.destination_id == visit.destination_id).first()
        catalog = session.query(TourismCatalog).filter(TourismCatalog.destination_id == visit.destination_id).first()
        min_dwell = (catalog.min_dwell_minutes if catalog and catalog.min_dwell_minutes else 20)

        now = datetime.now(timezone.utc)
        started = visit.started_at
        if started is None:
            started = now
        elif started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)

        elapsed_min = max(0, int((now - started).total_seconds() / 60))
        remaining = max(0, min_dwell - elapsed_min)

        return {
            "visit_id": visit.visit_id,
            "destination_id": visit.destination_id,
            "destination_name": dest.destination if dest else visit.destination_id,
            "visit_status": visit.visit_status,
            "validation_method": visit.validation_method or "gps_geofence",
            "started_at": started,
            "dwell_minutes": elapsed_min,
            "min_dwell_minutes": min_dwell,
            "remaining_minutes": remaining,
        }


def get_user_atlas(user_id: str, db: Optional[Session] = None) -> dict:
    """Compila el Atlas de Visitas del usuario con todos los sellos verificados."""
    with _get_db_context(db) as session:
        visits = db_visit_repository.get_verified_visits_by_user(user_id, db=session)
        if not visits:
            return {
                "total_verified_visits": 0,
                "regions_visited": 0,
                "visits": [],
            }

        dest_ids = {v.destination_id for v in visits}
        destinations = {
            d.destination_id: d
            for d in session.query(Destination).filter(Destination.destination_id.in_(dest_ids)).all()
        }
        catalogs = {
            c.destination_id: c
            for c in session.query(TourismCatalog).filter(TourismCatalog.destination_id.in_(dest_ids)).all()
        }
        covers = destination_media_service.get_covers_batch(session)

        items = []
        regions = set()
        for v in visits:
            d = destinations.get(v.destination_id)
            c = catalogs.get(v.destination_id)
            reg = (c.region if c else None) or (d.region if d else None)
            if reg:
                regions.add(reg.strip().upper())

            items.append({
                "visit_id": v.visit_id,
                "destination_id": v.destination_id,
                "destination_name": d.destination if d else v.destination_id,
                "region": reg,
                "city": c.city if c else None,
                "category": c.category if c else None,
                "cover_image_url": covers.get(v.destination_id),
                "completed_at": v.completed_at or v.updated_at,
                "dwell_minutes": v.dwell_minutes or 0,
                "validation_method": v.validation_method or "gps_geofence",
            })

        return {
            "total_verified_visits": len(items),
            "regions_visited": len(regions),
            "visits": items,
        }
