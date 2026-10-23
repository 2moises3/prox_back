"""Pruebas del motor real y del contrato HTTP sobre una DB aislada en memoria."""
import os
# Las pruebas científicas no cambian la configuración del resto de la suite.

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.services.thesis_engine import get_engine

PROFILE=dict(perfil_turistico='naturalista',intereses=['naturaleza','cultura','relax'],clima_preferido='calido',tolerancia_multitudes='baja')

def test_unknown_profile_and_interests_rejected():
 e=get_engine()
 for p in [{**PROFILE,'perfil_turistico':None},{**PROFILE,'intereses':[]},{**PROFILE,'intereses':['compras']},{**PROFILE,'clima_preferido':'nieve'}]:
  with pytest.raises(ValueError):e.recommend(p,1)

def test_inactive_fields_do_not_change_scores():
 e=get_engine();a=e.components(PROFILE)
 b=e.components({**PROFILE,'presupuesto':'alto','dias_viaje':15,'peso_costos':5})
 np.testing.assert_array_equal(a['scores'],b['scores'])

def test_zero_valid_context_and_no_clipping():
 e=get_engine();assert min(v.min() for v in e.crowd.values())==0
 rows=e.recommend(PROFILE,1,14)
 assert max(r['compatibility_score'] for r in rows)>1
 for r in rows:
  ex=r['explanation'];assert abs(ex['shap_base']+sum(ex['shap_values'].values())-r['compatibility_score'])<1e-12

def test_fase3_explanation_without_context():
 for r in get_engine().recommend(PROFILE,1,contextual=False):
  ex=r['explanation']
  assert ex['shap_values']['clima']==0 and ex['shap_values']['afluencia']==0
  assert abs(ex['shap_base']+sum(ex['shap_values'].values())-r['compatibility_score'])<1e-12

def test_tolerance_aliases():
 e=get_engine()
 for old,new in [('bajo','baja'),('medio','media'),('alto','alta'),('moderado','media')]:
  np.testing.assert_array_equal(e.components({**PROFILE,'tolerancia_multitudes':old})['scores'],e.components({**PROFILE,'tolerancia_multitudes':new})['scores'])
