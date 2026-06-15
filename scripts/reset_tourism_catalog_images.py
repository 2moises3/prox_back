import os
import shutil
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'app', 'data')
CSV_PATH = os.path.join(DATA_DIR, 'destinations_catalog.csv')
BACKUPS_DIR = os.path.join(DATA_DIR, 'backups')

# We connect using localhost because the backend is stopped and we run this on the host, 
# or we run it via python while DB is running.
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://proxvel_user:proxvel_password@localhost:5432/proxvel_db')

def run():
    print("Iniciando reseteo total de campos de imagen heredados...")
    
    if not os.path.exists(BACKUPS_DIR):
        os.makedirs(BACKUPS_DIR)
    
    import datetime
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUPS_DIR, f'destinations_catalog_before_total_reset_{timestamp}.csv')
    shutil.copy2(CSV_PATH, backup_path)
    print(f"Backup del CSV creado: {backup_path}")
    
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig', encoding_errors='replace', dtype=str)
    cols_to_clean = ['cover_image_url', 'gallery_image_1', 'gallery_image_2', 'gallery_image_3', 'gallery_image_4']
    
    for col in cols_to_clean:
        if col in df.columns:
            df[col] = ''

    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    print("CSV limpiado completamente.")

    # Limpiar PostgreSQL
    print(f"Conectando a {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    sql = text("""
        UPDATE tourism_catalog 
        SET cover_image_url = NULL,
            gallery_image_1 = NULL,
            gallery_image_2 = NULL,
            gallery_image_3 = NULL,
            gallery_image_4 = NULL
    """)
    
    res = session.execute(sql)
    session.commit()
    print(f"Campos limpiados a NULL en {res.rowcount} filas de PostgreSQL.")

if __name__ == '__main__':
    run()
