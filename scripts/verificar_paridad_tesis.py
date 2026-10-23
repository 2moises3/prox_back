"""Compara TODOS los top-3 exportados por los notebooks, sin DB ni GPU."""
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.thesis_engine import get_engine,label,VERSION

def verify():
 engine=get_engine();f=Path(__file__).resolve().parents[1]/'tests/fixtures/tesis_v3'
 profiles=pd.read_csv(f/'perfiles.csv.gz');f3=pd.read_csv(f/'fase3.csv.gz');f4=pd.read_csv(f/'fase4.csv.gz')
 scores=[];base=[];labels=[]
 for p in profiles.to_dict('records'):
  c=engine.components(p);scores.append(c['scores']);base.append(c['affinity'])
  labels.append([label(x,y) for x,y in zip(c['coverage'],c['quality'])])
 scores=np.array(scores);base=np.array(base);labels=np.array(labels)
 idx={u:i for i,u in enumerate(profiles.user_id)};checks={}
 for name,df,values in [('fase3',f3,base),('fase4',f4,scores)]:
  order=np.argsort(-values,axis=-1)
  u=df.user_id.map(idx).to_numpy();rank=df.posicion.to_numpy()-1
  if name=='fase3':
   dest=order[u,rank];pred=values[u,dest]
  else:
   m=df.mes_num.to_numpy()-1;dest=order[u,m,rank];pred=values[u,m,dest]
  same=engine.ids[dest]==df.destination_id.to_numpy();error=np.abs(pred-df.score_final.to_numpy())
  tags=labels[u,dest]==df.etiqueta.to_numpy()
  checks[name]=dict(filas=len(df),ranking_coincidente=int(same.sum()),etiquetas_coincidentes=int(tags.sum()),error_maximo_vs_csv_redondeado=float(error.max()))
  assert same.all(),(name,df.loc[~same].head().to_dict('records'))
  assert tags.all(),(name,'etiquetas')
  assert error.max()<=.000050001,(name,error.max())
 # API-facing serialization, full precision SHAP and zero-weight baseline.
 max_additivity=0.
 for p in profiles.iloc[::53].to_dict('records'):
  for month in [1,4,7,12]:
   for r in engine.recommend(p,month):
    ex=r['explanation'];err=abs(ex['shap_base']+sum(ex['shap_values'].values())-r['compatibility_score'])
    max_additivity=max(max_additivity,err)
    assert err<1e-12
    json.dumps(r,allow_nan=False)
 report=dict(version=VERSION,perfiles=len(profiles),combinaciones_perfil_mes=len(profiles)*12,checks=checks,error_aditividad_shap=max_additivity)
 print(json.dumps(report,ensure_ascii=False,indent=2));return report
if __name__=='__main__':
 result=verify()
 if len(sys.argv)>1:
  output=Path(sys.argv[1]);output.parent.mkdir(parents=True,exist_ok=True)
  output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
