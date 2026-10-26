"""Regression checks for the app's monthly ranking presentation."""
import numpy as np
from app.services.thesis_engine import get_engine

PROFILE = dict(perfil_turistico='naturalista', intereses=['naturaleza', 'cultura', 'relax'], clima_preferido='calido', tolerancia_multitudes='baja')

def test_each_month_returns_complete_catalog_in_real_score_order():
    engine = get_engine()
    components = engine.components(PROFILE)
    for month in range(1, 13):
        rows = engine.recommend(PROFILE, month, limit=100)
        assert len(rows) == len(engine.ids)
        assert len({r['destination_id'] for r in rows}) == len(rows)
        scores = [r['compatibility_score'] for r in rows]
        assert scores == sorted(scores, reverse=True)
        for row in rows:
            idx = list(engine.ids).index(row['destination_id'])
            assert row['month'] == month
            assert abs(row['compatibility_score'] - components['scores'][month - 1, idx]) < 1e-12
            assert row['best_month'] == int(np.argmax(components['scores'][:, idx])) + 1

def test_month_changes_context_not_interest_labels_or_affinity_percent():
    engine = get_engine()
    january = {r['destination_id']: r for r in engine.recommend(PROFILE, 1, 100)}
    july = {r['destination_id']: r for r in engine.recommend(PROFILE, 7, 100)}
    assert any(january[id]['compatibility_score'] != july[id]['compatibility_score'] for id in january)
    for id in january:
        assert january[id]['label'] == july[id]['label']
        assert january[id]['compatibility_percent'] == july[id]['compatibility_percent']
