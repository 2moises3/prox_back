"""Motor reproducible NB02/Fase3 + NB03/Fase4, snapshot 2026-10-22."""
from functools import lru_cache
from pathlib import Path
import json,re,unicodedata,hashlib
import numpy as np
import pandas as pd
DATA=Path(__file__).resolve().parents[1]/'data/tesis_v3'
VERSION='tesis-v3-20261022'
MONTHS=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
def normalize(v):
 v=unicodedata.normalize('NFKD',str(v or '').strip().lower())
 return re.sub(r'\s+','_',''.join(c for c in v if not unicodedata.combining(c)))
def minmax(v):
 lo,hi=v.min(),v.max()
 return (v-lo)/(hi-lo) if hi-lo>1e-12 else np.full_like(v,.5)
def label(coverage,quality):
 if coverage>=.50 and quality>=.60:return 'recomendado'
 if coverage>=.01 or quality>=.60:return 'parcialmente_recomendado'
 return 'no_recomendado'
class ThesisEngine:
 def __init__(self,directory=DATA):
  directory=Path(directory)
  manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
  for entry in manifest['archivos']:
   if hashlib.sha256((directory/entry['archivo']).read_bytes()).hexdigest()!=entry['sha256']:
    raise RuntimeError('El snapshot científico no coincide con su manifiesto')
  self.reference=json.loads((directory/'referencia.json').read_text(encoding='utf-8'))
  self.shap=json.loads((directory/'shap_referencia.json').read_text(encoding='utf-8'))
  self.alpha=float(self.reference['modelo_afinidad']['alpha_absa']);self.context_weight=.30
  self.aspects=self.reference['pesos_por_perfil']['aspectos_del_modelo']
  self.profile_weights=self.reference['pesos_por_perfil']['por_perfil']
  self.interests=list(self.reference['intereses']['distribucion'])
  self.destinations=pd.read_csv(directory/'destinos.csv').sort_values('destination_id').reset_index(drop=True)
  self.ids=self.destinations.destination_id.to_numpy()
  tags=[{normalize(t) for t in s.split(',') if t.strip()} for s in self.destinations.intereses.fillna('')]
  self.D=np.array([[float(i in ts) for i in self.interests] for ts in tags])
  matrix=pd.read_csv(directory/'matriz.csv').pivot(index='destination_id',columns='aspecto',values='score_normalizado_0_1').reindex(self.ids)
  self.all_aspects=matrix
  self.A=matrix[self.aspects].to_numpy(float)
  if not np.isfinite(self.A).all():raise ValueError('Matriz ABSA incompleta')
  self.climate={};self.crowd={};self.climate_text={};self.crowd_text={}
  ci=pd.read_csv(directory/'clima.csv').set_index(['preferencia_climatica','mes_num','destination_id'])
  cr=pd.read_csv(directory/'aforo.csv').set_index(['tolerancia_multitudes','mes_num','destination_id'])
  self.climate_data=ci;self.crowd_data=cr
  for pref in ci.index.get_level_values(0).unique():
   self.climate[pref]=np.array([[ci.loc[(pref,m,d),'score_clima'] for d in self.ids] for m in range(1,13)])
   self.climate_text[pref]=[[str(ci.loc[(pref,m,d),'explicacion_clima']) for d in self.ids] for m in range(1,13)]
  for tol in cr.index.get_level_values(0).unique():
   self.crowd[tol]=np.array([[cr.loc[(tol,m,d),'score_aforo_personalizado'] for d in self.ids] for m in range(1,13)])
   self.crowd_text[tol]=[[str(cr.loc[(tol,m,d),'explicacion_aforo']) for d in self.ids] for m in range(1,13)]
  for arr in list(self.climate.values())+list(self.crowd.values()):
   if arr.shape!=(12,len(self.ids)) or not np.isfinite(arr).all():raise ValueError('Contexto incompleto')
 def resolve_profile(self,p):
  kind=normalize(p.get('perfil_turistico'))
  if kind not in self.profile_weights:raise ValueError('Selecciona un tipo de viajero válido en tus preferencias')
  supplied=p.get('intereses')
  if supplied is None:supplied=[i for i in self.interests if float(p.get('interes_'+i,0))>0]
  if not isinstance(supplied,(list,tuple,set)):raise ValueError('Los intereses deben ser una lista')
  aliases={'cultural':'cultura','gastronomico':'gastronomia'}
  interests={aliases.get(normalize(i),normalize(i)) for i in supplied}
  unknown=interests-set(self.interests)
  if unknown:raise ValueError('Intereses fuera de la taxonomía: '+', '.join(sorted(unknown)))
  if not interests:raise ValueError('Selecciona al menos un interés')
  pref=normalize(p.get('preferencia_climatica') or p.get('clima_preferido') or 'indiferente')
  tol=normalize(p.get('tolerancia_multitudes') or 'media')
  tol={'bajo':'baja','medio':'media','alto':'alta','moderado':'media'}.get(tol,tol)
  if pref not in self.climate or tol not in self.crowd:raise ValueError('Clima o tolerancia no válidos')
  raw=np.array([self.profile_weights[kind][a] for a in self.aspects],float)
  weights=np.round(raw/raw.sum(),4) # NB01 exporta los pesos con cuatro decimales.
  return kind,interests,pref,tol,weights
 def components(self,p):
  kind,interests,pref,tol,weights=self.resolve_profile(p)
  vec=np.array([float(i in interests) for i in self.interests])
  coverage=(vec@self.D.T)/max(vec.sum(),1);quality=weights@self.A.T
  affinity=(1-self.alpha)*minmax(coverage)+self.alpha*minmax(quality)
  scores=affinity[None,:]+self.context_weight*(.5*self.climate[pref]+.5*self.crowd[tol]-.5)
  return dict(kind=kind,interests=interests,pref=pref,tol=tol,weights=weights,coverage=coverage,quality=quality,affinity=affinity,scores=scores)
 def recommend(self,p,month,limit=3,contextual=True):
  if not isinstance(month,int) or not 1<=month<=12:raise ValueError('Mes fuera de 1–12')
  c=self.components(p);scores=c['scores'][month-1] if contextual else c['affinity']
  # Mismo orden de IDs y argsort que los notebooks; nunca redondear antes de ordenar.
  order=np.argsort(-scores)[:max(0,min(int(limit),len(self.ids)))];items=[]
  means=np.array(self.shap['media_fondo'],float);coef=np.array([1.,.15,.15]) if contextual else np.array([1.,0.,0.])
  shap_base=float(self.shap['valor_base']) if contextual else float(means[0])
  for rank,j in enumerate(order,1):
   row=self.destinations.iloc[j];cl=float(self.climate[c['pref']][month-1,j]);af=float(self.crowd[c['tol']][month-1,j])
   phi=(np.array([c['affinity'][j],cl,af])-means)*coef
   aspects=sorted([dict(aspect=a,user_weight=float(c['weights'][k]),destination_score=float(self.A[j,k]),contribution=float(c['weights'][k]*self.A[j,k])) for k,a in enumerate(self.aspects)],key=lambda v:v['contribution'],reverse=True)
   best=int(np.argmax(c['scores'][:,j]))+1
   items.append(dict(destination_id=str(row.destination_id),name=str(row.destination),region=str(row.region),city=None,category=str(row.tipo_experiencia),cover_image_url=None,rating=None,
    compatibility_score=float(scores[j]),compatibility_percent=round(float(c['affinity'][j])*100),score_semantics='puntaje de ordenamiento; no probabilidad',
    label=label(c['coverage'][j],c['quality'][j]),month=month,month_name=MONTHS[month-1],best_month=best,best_month_name=MONTHS[best-1],ranking_position=rank,has_real_scores=True,
    perfil_turistico=c['kind'],coverage=float(c['coverage'][j]),quality_absa=float(c['quality'][j]),affinity_f3=float(c['affinity'][j]),climate_score=cl,crowd_score=af,
    context_status=f'Clima {cl:.2f} · afluencia {af:.2f} · {MONTHS[month-1]}',
    explanation=dict(summary=f"Coincide con {c['coverage'][j]:.0%} de tus intereses. "+self.climate_text[c['pref']][month-1][j]+' '+self.crowd_text[c['tol']][month-1][j],top_aspects=aspects,shap_base=shap_base,shap_values=dict(zip(['afinidad','clima','afluencia'],phi.tolist())),shap_method=self.shap['metodo'])))
  return items
@lru_cache(maxsize=1)
def get_engine():return ThesisEngine()
