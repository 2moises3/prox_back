"""Contexto histórico de la misma versión científica usada por el ranking V3."""
from pandas import isna
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.destination_model import Destination
from app.services.thesis_engine import get_engine, normalize, MONTHS, VERSION

MONTH_NAMES = {i+1: name for i,name in enumerate(MONTHS)}

FAVORABLE = .70
MODERADO = .50

def climate_level(score):
    if score is None: return None
    return "Favorable" if score >= FAVORABLE else "Moderado" if score >= MODERADO else "Desfavorable"

def _preferences(clima, tolerancia):
    e = get_engine()
    pref = normalize(clima or 'indiferente')
    tol = normalize(tolerancia or 'media')
    tol = {'bajo':'baja','medio':'media','alto':'alta','moderado':'media'}.get(tol,tol)
    if pref not in e.climate or tol not in e.crowd:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Selecciona un clima y una tolerancia válidos.")
    return pref, tol

def _month(did, month, pref, tol):
    e = get_engine()
    c = e.climate_data.loc[(pref, month, did)]
    a = e.crowd_data.loc[(tol, month, did)]
    cl, af = float(c.score_clima), float(a.score_aforo_personalizado)
    return dict(month=month, month_name=MONTHS[month-1], has_data=True,
        clima_score=cl, clima_nivel=climate_level(cl), clima_riesgo=None if isna(c.riesgo_climatico) else str(c.riesgo_climatico),
        clima_explicacion=str(c.explicacion_clima), temp_prom=float((c.tmax_c+c.tmin_c)/2),
        lluvia_mm=float(c.pp_mm), aforo_score=af, aforo_nivel=str(a.nivel_aforo),
        aforo_explicacion=str(a.explicacion_aforo), visitantes_medios=float(a.visitantes_medios),
        combined=.5*cl+.5*af)

def month_context(db: Session, month: int) -> list[dict]:
    e = get_engine()
    active = set(db.scalars(select(Destination.destination_id).where(Destination.is_active.is_(True))).all())
    result=[]
    for did in e.ids:
        if did not in active: continue
        row=_month(did,month,'indiferente','media')
        row.update(destination_id=did, clima_por_preferencia={p:float(e.climate[p][month-1,list(e.ids).index(did)]) for p in e.climate},
            engine_version=VERSION)
        result.append(row)
    return result

def calendar(db: Session, destination_id: str, clima: str | None, tolerancia: str | None) -> dict | None:
    dest=db.scalar(select(Destination).where(Destination.destination_id==destination_id, Destination.is_active.is_(True)))
    if dest is None or destination_id not in get_engine().ids: return None
    pref,tol=_preferences(clima,tolerancia)
    months=[_month(destination_id,m,pref,tol) for m in range(1,13)]
    return dict(destination_id=destination_id,destination=dest.destination,preference=pref,tolerance=tol,
        engine_version=VERSION,best_month=max(months,key=lambda m:m['combined'])['month'],
        worst_month=min(months,key=lambda m:m['combined'])['month'],months=months)
