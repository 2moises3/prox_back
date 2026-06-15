import os
import shutil
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'app', 'data')
CSV_PATH = os.path.join(DATA_DIR, 'destinations_catalog.csv')
BACKUPS_DIR = os.path.join(DATA_DIR, 'backups')

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://proxvel_user:proxvel_password@postgres:5432/proxvel_db')

def is_valid_url(url):
    if not url or pd.isna(url) or str(url).strip() == '':
        return False
    url_str = str(url).strip()
    if url_str == 'PENDIENTE':
        return False
    if not url_str.startswith('http'):
        return False
    if 'commons.wikimedia.org/wiki/' in url_str and 'Special:FilePath' not in url_str:
        return False
    return True

def run():
    print("Iniciando saneamiento de imágenes...")
    
    if not os.path.exists(BACKUPS_DIR):
        os.makedirs(BACKUPS_DIR)
    
    df = pd.read_csv(CSV_PATH, encoding='utf-8', encoding_errors='replace')
    cols_to_clean = ['cover_image_url', 'gallery_image_1', 'gallery_image_2', 'gallery_image_3', 'gallery_image_4']
    
    # Limpieza
    for idx, row in df.iterrows():
        for col in cols_to_clean:
            if col in df.columns:
                val = row[col]
                if not is_valid_url(val):
                    df.at[idx, col] = ''

    # Solo actualizar BD, CSV no lo sobreescribimos para evitar encoding bugs (o si, pero con utf-8-sig)
    # Actually, the user asked to clean CSV and DB. Let's write CSV with utf-8
    df.to_csv(CSV_PATH, index=False, encoding='utf-8')
    print("CSV en contenedor actualizado.")

    print(f"Conectando a {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    updated_count = 0
    for idx, row in df.iterrows():
        dest_id = row['destination_id']
        cover = row.get('cover_image_url', '')
        g1 = row.get('gallery_image_1', '')
        g2 = row.get('gallery_image_2', '')
        g3 = row.get('gallery_image_3', '')
        g4 = row.get('gallery_image_4', '')

        cover = cover if cover != '' else None
        g1 = g1 if g1 != '' else None
        g2 = g2 if g2 != '' else None
        g3 = g3 if g3 != '' else None
        g4 = g4 if g4 != '' else None

        sql = text("""
            UPDATE tourism_catalog 
            SET cover_image_url = :cover,
                gallery_image_1 = :g1,
                gallery_image_2 = :g2,
                gallery_image_3 = :g3,
                gallery_image_4 = :g4
            WHERE destination_id = :id
        """)
        
        res = session.execute(sql, {
            'cover': cover, 'g1': g1, 'g2': g2, 'g3': g3, 'g4': g4, 'id': dest_id
        })
        updated_count += res.rowcount

    session.commit()
    print(f"Actualizadas {updated_count} filas en PostgreSQL.")

if __name__ == '__main__':
    run()
