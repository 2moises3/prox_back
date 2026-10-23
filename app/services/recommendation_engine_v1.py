"""Adaptador API para la tesis V3. PostgreSQL aporta metadatos, no puntajes.
La normalización usa el catálogo completo; los filtros se aplican después.
"""
from datetime import datetime
from app.services.thesis_engine import get_engine,normalize

def generate_recommendations(user_profile,limit=3,month=None,region=None):
 from app.config.database import SessionLocal
 from app.models.destination_model import Destination
 from app.models.tourism_catalog_model import TourismCatalog
 from app.services import destination_media_service
 engine=get_engine()
 items=engine.recommend(user_profile,month if month is not None else datetime.now().month,limit=len(engine.ids))
 if SessionLocal is None:raise RuntimeError('PostgreSQL no está configurado')
 with SessionLocal() as db:
  rows=db.query(Destination,TourismCatalog).outerjoin(TourismCatalog,Destination.destination_id==TourismCatalog.destination_id).all()
  by_id={d.destination_id:(d,cat) for d,cat in rows};covers=destination_media_service.get_covers_batch(db);result=[]
  for item in items:
   pair=by_id.get(item['destination_id'])
   if pair is None or not pair[0].is_active or not pair[0].in_engine:continue
   _,cat=pair
   if cat:
    for key in ['city','region','category','cover_image_url']:
     value=getattr(cat,key,None)
     if value:item[key]=value
   item['cover_image_url']=covers.get(item['destination_id']) or item['cover_image_url']
   if region and normalize(item['region'])!=normalize(region):continue
   item['label_code']=item['label']
   item['label']={'recomendado':'Recomendado','parcialmente_recomendado':'Parcialmente recomendado','no_recomendado':'No recomendado'}[item['label_code']]
   result.append(item)
  for rank,item in enumerate(result,1):item['ranking_position']=rank
  return result[:limit]

# Compatibilidad de vocabulario para los consumidores existentes; sin fórmula antigua.
INTEREST_VOCAB = set(get_engine().interests)
_CLIMATE_PREFS = set(get_engine().climate)
def _perfil_tolerancia(profile):
 value = normalize(profile.get('tolerancia_multitudes') or 'media')
 return {'bajo':'baja','medio':'media','alto':'alta','moderado':'media'}.get(value,value)
