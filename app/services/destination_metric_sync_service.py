"""
PROXVEL Backend - Destination Metric Sync Service.
Sincroniza los destinos desde los archivos del motor de IA hacia la base de datos.
"""

import os
import pandas as pd
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.utils.normalizers import generate_destination_id
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def sync_destinations_from_metrics(db: Session) -> Dict[str, Any]:
    base_path = os.path.join("app", "data")
    
    absa_path = os.path.join(base_path, "matriz_absa_normalizada.csv")
    ranking_path = os.path.join(base_path, "ranking_contextual_final.csv")
    clima_path = os.path.join(base_path, "clima_scores.csv")
    aforo_path = os.path.join(base_path, "aforo_scores.csv")
    
    if not os.path.exists(absa_path):
        raise HTTPException(status_code=500, detail="No se encontró la matriz ABSA")
        
    try:
        # 1. Leer CSVs
        absa_df = pd.read_csv(absa_path)
        ranking_df = pd.read_csv(ranking_path) if os.path.exists(ranking_path) else pd.DataFrame()
        clima_df = pd.read_csv(clima_path) if os.path.exists(clima_path) else pd.DataFrame()
        aforo_df = pd.read_csv(aforo_path) if os.path.exists(aforo_path) else pd.DataFrame()
        
        # 2. Extraer conjuntos de destinos
        absa_destinations = set(absa_df['destination'].dropna().unique()) if 'destination' in absa_df.columns else set()
        ranking_destinations = set(ranking_df['destination'].dropna().unique()) if 'destination' in ranking_df.columns else set()
        clima_destinations = set(clima_df['destination'].dropna().unique()) if 'destination' in clima_df.columns else set()
        aforo_destinations = set(aforo_df['destination'].dropna().unique()) if 'destination' in aforo_df.columns else set()
            
        # Regla: Destino detectable = aparece en matriz_absa_normalizada.csv
        detectable_destinations = absa_destinations
        
        # Destinos actuales en DB
        db_destinations = db.query(Destination).all()
        db_dest_map = {d.destination_id: d for d in db_destinations}
        
        summary = {
            "metrics_destinations": len(detectable_destinations),
            "created_count": 0,
            "updated_count": 0,
            "deactivated_count": 0,
            "warnings_count": 0
        }
        
        warnings = []
        created = []
        updated = []
        deactivated = []
        
        processed_slugs = set()
        
        # 3. Procesar Destinos Detectables
        for dest_name in detectable_destinations:
            slug = generate_destination_id(dest_name)
            processed_slugs.add(slug)
            
            in_ranking = dest_name in ranking_destinations
            in_clima = dest_name in clima_destinations
            in_aforo = dest_name in aforo_destinations
            
            # Lógica de estados según reglas del usuario
            if not in_ranking:
                data_status = "metrics_incomplete"
            elif in_ranking and (not in_clima or not in_aforo):
                data_status = "metrics_incomplete"
            else:
                data_status = "ready" # Cubierto por métricas, pero depende de la info editorial
            
            db_dest = db_dest_map.get(slug)
            
            if not db_dest:
                # CREAR DESTINO NUEVO
                new_dest = Destination(
                    destination_id=slug,
                    destination=dest_name,
                    is_active=False
                )
                db.add(new_dest)
                db.flush() # Para generar ID si hiciera falta
                
                new_catalog = TourismCatalog(
                    destination_id=slug,
                    official_name=dest_name,
                    data_status=data_status if data_status == "metrics_incomplete" else "pending_info"
                )
                db.add(new_catalog)
                
                summary["created_count"] += 1
                created.append(slug)
                if data_status == "metrics_incomplete":
                    warnings.append(f"{dest_name}: creado, pero faltan métricas (ranking/clima/aforo).")
            else:
                # ACTUALIZAR DESTINO EXISTENTE
                catalog = db.query(TourismCatalog).filter(TourismCatalog.destination_id == slug).first()
                if not catalog:
                    catalog = TourismCatalog(
                        destination_id=slug,
                        official_name=dest_name,
                    )
                    db.add(catalog)
                
                # Validar completitud editorial para ver si es pending_info o ready
                is_editorial_complete = bool(
                    catalog.city and catalog.region and catalog.category and catalog.description
                )
                
                if data_status == "metrics_incomplete":
                    final_status = "metrics_incomplete"
                elif not is_editorial_complete:
                    final_status = "pending_info"
                else:
                    final_status = "ready"
                
                status_changed = False
                if catalog.data_status != final_status:
                    catalog.data_status = final_status
                    status_changed = True
                    
                # Regla: Si está metrics_incomplete, asegurarse que no esté activo
                if final_status == "metrics_incomplete" and db_dest.is_active:
                    db_dest.is_active = False
                    status_changed = True
                    warnings.append(f"{dest_name}: desactivado porque pasó a metrics_incomplete.")
                    
                if status_changed:
                    summary["updated_count"] += 1
                    updated.append(slug)
                    
                if final_status == "metrics_incomplete":
                    warnings.append(f"{dest_name}: presente en DB, pero métricas incompletas.")

            # UPSERT ABSA SCORES FROM CSV
            dest_row = absa_df[absa_df['destination'] == dest_name]
            if not dest_row.empty:
                row_dict = dest_row.iloc[0].to_dict()
                aspects = ["accesibilidad", "aforo_multitudes", "alojamiento", "atencion_servicio", "atractivos", "clima", "costos", "gastronomia", "limpieza", "seguridad"]
                scores_to_save = {k: row_dict.get(k) for k in aspects if k in row_dict and pd.notna(row_dict[k])}
                
                existing_score = db.query(DestinationAspectScore).filter(DestinationAspectScore.destination_id == slug).first()
                if existing_score:
                    for k, v in scores_to_save.items():
                        setattr(existing_score, k, v)
                else:
                    new_score = DestinationAspectScore(destination_id=slug, **scores_to_save)
                    db.add(new_score)
                    
        # 4. Procesar Destinos Fuera del Motor (out_of_engine)
        for db_dest in db_destinations:
            if db_dest.destination_id not in processed_slugs:
                # Este destino ya no está en la matriz ABSA
                changed = False
                if db_dest.is_active:
                    db_dest.is_active = False
                    changed = True
                    
                catalog = db.query(TourismCatalog).filter(TourismCatalog.destination_id == db_dest.destination_id).first()
                if catalog and catalog.data_status != "out_of_engine":
                    catalog.data_status = "out_of_engine"
                    changed = True
                elif not catalog:
                    catalog = TourismCatalog(
                        destination_id=db_dest.destination_id,
                        data_status="out_of_engine"
                    )
                    db.add(catalog)
                    changed = True
                    
                if changed:
                    summary["deactivated_count"] += 1
                    deactivated.append(db_dest.destination_id)
        
        summary["warnings_count"] = len(warnings)
        
        db.commit()
        return {
            "created": created,
            "updated": updated,
            "deactivated": deactivated,
            "warnings": warnings,
            "summary": summary
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error sincronizando métricas: {e}")
        raise HTTPException(status_code=500, detail=f"Error en sincronización: {str(e)}")
