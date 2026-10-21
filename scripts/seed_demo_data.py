"""
PROXVEL - Datos de demostración (SOLO para el entorno local).

Crea viajeros de prueba con perfil, residencia, favoritos y reseñas realistas en los destinos,
para que la app y el dashboard se vean con vida. No toca los datos de la tesis ni el motor.

    python scripts/seed_demo_data.py            # crea (o recrea) los datos demo
    python scripts/seed_demo_data.py --remove   # borra todo lo creado por este script

Todas las cuentas demo usan correos @example.com (dominio reservado, no llega a nadie)
y la contraseña DEMO_PASSWORD de abajo. No subir estos datos a producción.
"""
import argparse
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.config.database import SessionLocal  # noqa: E402
from app.models.destination_model import Destination  # noqa: E402
from app.models.favorite_model import Favorite  # noqa: E402
from app.models.review_model import Review  # noqa: E402
from app.models.traveler_profile_model import TravelerProfile  # noqa: E402
from app.models.user_model import User  # noqa: E402
from app.repositories.db_user_repository import get_next_user_id  # noqa: E402
from app.utils.hash_util import get_password_hash  # noqa: E402

DEMO_DOMAIN = "@example.com"
DEMO_PASSWORD = "ProxvelDemo2026"

# nombre, residencia (departamento, provincia, distrito), perfil
TRAVELERS = [
    ("Valeria Quispe Mamani", ("CUSCO", "CUSCO", "WANCHAQ"),
     dict(intereses=["historia", "cultura", "fotografía"], clima_preferido="templado", tolerancia_multitudes="media", presupuesto="medio", dias_viaje=5)),
    ("Diego Ramírez Torres", ("LIMA", "LIMA", "MIRAFLORES"),
     dict(intereses=["aventura", "montañismo", "naturaleza"], clima_preferido="frío", tolerancia_multitudes="baja", presupuesto="medio", dias_viaje=7)),
    ("Camila Flores Huamán", ("AREQUIPA", "AREQUIPA", "YANAHUARA"),
     dict(intereses=["naturaleza", "fotografía", "relax"], clima_preferido="seco", tolerancia_multitudes="baja", presupuesto="alto", dias_viaje=3)),
    ("Luis Mendoza Rojas", ("LA LIBERTAD", "TRUJILLO", "TRUJILLO"),
     dict(intereses=["historia", "académico", "cultura"], clima_preferido="cálido", tolerancia_multitudes="media", presupuesto="bajo", dias_viaje=2)),
    ("Andrea Castillo Vega", ("PIURA", "PIURA", "PIURA"),
     dict(intereses=["playa", "gastronomía", "relax"], clima_preferido="cálido", tolerancia_multitudes="alta", presupuesto="medio", dias_viaje=5)),
    ("José Huamaní Ccori", ("JUNIN", "HUANCAYO", "EL TAMBO"),
     dict(intereses=["rural", "naturaleza", "aventura"], clima_preferido="frío", tolerancia_multitudes="baja", presupuesto="bajo", dias_viaje=3)),
    ("María Fernanda Salazar", ("LAMBAYEQUE", "CHICLAYO", "CHICLAYO"),
     dict(intereses=["cultura", "gastronomía", "historia"], clima_preferido="cálido", tolerancia_multitudes="media", presupuesto="medio", dias_viaje=3)),
    ("Renzo Paredes Lazo", ("ICA", "ICA", "ICA"),
     dict(intereses=["aventura", "playa", "fotografía"], clima_preferido="seco", tolerancia_multitudes="alta", presupuesto="medio", dias_viaje=2)),
    ("Lucía Gutiérrez Alva", ("LIMA", "LIMA", "SAN ISIDRO"),
     dict(intereses=["familiar", "urbano", "relax"], clima_preferido="templado", tolerancia_multitudes="alta", presupuesto="alto", dias_viaje=2)),
    ("Kevin Chávez Soto", ("SAN MARTIN", "SAN MARTIN", "TARAPOTO"),
     dict(intereses=["naturaleza", "aventura", "relax"], clima_preferido="cálido", tolerancia_multitudes="media", presupuesto="bajo", dias_viaje=3)),
    ("Ximena Rivera Paz", ("CAJAMARCA", "CAJAMARCA", "CAJAMARCA"),
     dict(intereses=["historia", "rural", "gastronomía"], clima_preferido="templado", tolerancia_multitudes="baja", presupuesto="medio", dias_viaje=4)),
    ("Bruno Alarcón Díaz", ("PUNO", "PUNO", "PUNO"),
     dict(intereses=["montañismo", "fotografía", "cultura"], clima_preferido="frío", tolerancia_multitudes="baja", presupuesto="medio", dias_viaje=7)),
]

# Reseñas por destino: (calificación, texto)
REVIEWS = {
    "machu_picchu": [
        (5, "Increíble. Entramos en el primer turno y vimos cómo se iba la neblina sobre la ciudadela. Vale cada sol."),
        (4, "Impresionante, pero hay que comprar el boleto con semanas de anticipación. El bus de Aguas Calientes tiene colas largas."),
        (5, "Subimos a Huayna Picchu y la vista es de otro mundo. Lleven agua y paciencia con las escaleras."),
        (4, "Hermoso, aunque en julio estaba muy lleno. Recomiendo ir en temporada baja y contratar guía."),
        (5, "El mejor lugar que he visitado en el Perú. El guía nos explicó todo con mucho detalle."),
    ],
    "ollantaytambo": [
        (5, "El pueblo es lindo y las terrazas son enormes. Subir al Templo del Sol cansa, pero la vista lo compensa."),
        (4, "Buen punto para dormir antes de tomar el tren a Machu Picchu. Mucha historia en cada calle."),
        (4, "Llegamos temprano y casi no había gente. Las piedras del templo son impresionantes."),
        (5, "Los depósitos de Pinkuylluna son gratis y tienen una vista espectacular del valle."),
    ],
    "ciudadela_kuelap": [
        (5, "El teleférico ya es una experiencia. La fortaleza es gigante y hay mucha menos gente que en Cusco."),
        (5, "Las casas circulares y las murallas te dejan sin palabras. Llevar casaca, el clima cambia rápido."),
        (4, "Muy bonito, pero el camino desde Chachapoyas es largo. Combínenlo con la catarata de Gocta."),
    ],
    "chan_chan": [
        (4, "Impresiona caminar por la ciudad de barro más grande de América. Hace mucho calor, lleven gorra."),
        (5, "Los frisos de peces y aves están muy bien conservados. El museo de sitio ayuda a entenderlo todo."),
        (4, "Interesante y fácil de llegar desde Trujillo. Después fuimos a Huanchaco a comer ceviche."),
        (3, "Bonito, pero hay poca sombra y algunas zonas están cerradas por mantenimiento."),
    ],
    "huaca_luna": [
        (5, "Los relieves de colores son impresionantes, parecen recién pintados. La guía fue excelente."),
        (5, "Mejor de lo que esperaba. Ver las capas del templo una sobre otra es fascinante."),
        (4, "Visita corta y muy didáctica. El museo es moderno y está bien organizado."),
    ],
    "huaca_pucllana": [
        (4, "Increíble tener una pirámide en medio de Miraflores. La visita guiada dura como una hora."),
        (5, "Fuimos de noche al restaurante con vista a la huaca iluminada. Una experiencia muy limeña."),
        (4, "Ideal para ir con niños: tienen animales andinos y una huerta. Fácil de llegar."),
    ],
    "lineas_nazca": [
        (5, "El sobrevuelo es inolvidable, se ven clarito el colibrí y el mono. Eso sí, marea un poco."),
        (4, "Caro, pero vale la pena. Si no quieres volar, el mirador te deja ver un par de figuras."),
        (5, "Una de esas cosas que hay que ver una vez en la vida. Vayan sin desayunar mucho."),
        (3, "El vuelo se retrasó dos horas por el viento. Las figuras son increíbles, la organización no tanto."),
    ],
    "museo_sipan": [
        (5, "El mejor museo del Perú. Las joyas de oro del Señor de Sipán son espectaculares."),
        (5, "Muy bien montado, recorres la tumba como si estuvieras excavando. No se pueden tomar fotos, ojo."),
        (4, "Excelente museo, fácil de visitar desde Chiclayo. Combínenlo con el Brüning y Túcume."),
    ],
    "parque_aguas": [
        (5, "De noche es mágico, el espectáculo de luces y música encanta a grandes y chicos."),
        (4, "Plan barato y bonito en Lima. Lleven ropa de cambio si van con niños, se mojan sí o sí."),
        (4, "Lindo para pasear en familia. Los fines de semana se llena bastante."),
    ],
    "parque_huascaran": [
        (5, "La Laguna 69 es de las caminatas más lindas que he hecho. Aclimátense uno o dos días antes."),
        (5, "Las lagunas de Llanganuco tienen un color turquesa que no parece real. Paisajes de postal."),
        (4, "Exigente por la altura, pero cada paso vale la pena. Salgan temprano para evitar la lluvia."),
        (5, "Vimos el Huascarán nevado de cerca. Un paraíso para los amantes de la montaña."),
    ],
    "reserva_paracas": [
        (4, "El paseo a las Islas Ballestas está buenazo: lobos marinos, pingüinos y miles de aves."),
        (5, "La Playa Roja y La Catedral son preciosas. Paisaje de desierto junto al mar, único."),
        (4, "Fuimos un fin de semana desde Lima. Lleven bloqueador, el sol pega fuerte aunque haya viento."),
    ],
    "valle_colca": [
        (5, "Ver al cóndor volar a pocos metros en la Cruz del Cóndor fue emocionante. Lleguen antes de las 8."),
        (5, "Las termas de La Calera después del viaje son lo máximo. Los pueblos del valle son muy lindos."),
        (4, "El soroche se siente en Patapampa. Tomen mate de coca y vayan con calma."),
        (4, "Paisajes impresionantes y terrazas por todos lados. Mejor ir con tour de dos días."),
    ],
    "catarata_ahuashiyacu": [
        (4, "Una catarata bonita y fácil de llegar desde Tarapoto. El agua es helada pero rica."),
        (5, "Perfecta para pasar la mañana. Lleven zapatillas, las piedras resbalan."),
        (3, "Bonita, pero el fin de semana estaba llena de gente. Mejor ir entre semana."),
    ],
    "ventanillas_otuzco": [
        (4, "Lugar curioso y muy fotogénico. La visita es corta, ideal para combinar con los Baños del Inca."),
        (4, "Interesante ver cómo enterraban a sus muertos. Buena vista del valle de Cajamarca."),
        (3, "Bonito, pero esperaba un poco más de información en el sitio. Vale la pena con guía."),
    ],
}

FAVORITES = {
    0: ["machu_picchu", "ollantaytambo", "valle_colca"],
    1: ["parque_huascaran", "ciudadela_kuelap"],
    2: ["valle_colca", "reserva_paracas", "lineas_nazca"],
    3: ["chan_chan", "huaca_luna", "museo_sipan"],
    4: ["reserva_paracas", "parque_aguas"],
    5: ["parque_huascaran", "catarata_ahuashiyacu"],
    6: ["museo_sipan", "chan_chan"],
    7: ["lineas_nazca", "reserva_paracas"],
    8: ["parque_aguas", "huaca_pucllana"],
    9: ["catarata_ahuashiyacu", "ciudadela_kuelap"],
    10: ["ventanillas_otuzco", "ciudadela_kuelap"],
    11: ["machu_picchu", "valle_colca", "parque_huascaran"],
}


def _email(full_name: str) -> str:
    import unicodedata
    base = unicodedata.normalize("NFKD", full_name.lower())
    base = "".join(c for c in base if not unicodedata.combining(c))
    parts = base.split()
    return f"{parts[0]}.{parts[-2] if len(parts) > 2 else parts[-1]}{DEMO_DOMAIN}"


def remove(db) -> int:
    ids = [u for (u,) in db.query(User.user_id).filter(User.email.like(f"%{DEMO_DOMAIN}")).all()]
    if not ids:
        return 0
    review_ids = [r for (r,) in db.query(Review.review_id).filter(Review.user_id.in_(ids)).all()]
    if review_ids:
        db.execute(text("delete from review_aspect_ratings where review_id = any(:r)"), {"r": review_ids})
    tablas = [t for (t,) in db.execute(text(
        "select table_name from information_schema.columns "
        "where column_name='user_id' and table_schema='public' and table_name <> 'users'"))]
    for t in tablas:
        db.execute(text(f'delete from "{t}" where user_id = any(:ids)'), {"ids": ids})
    db.query(User).filter(User.user_id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return len(ids)


def seed(db) -> dict:
    rng = random.Random(2026)
    remove(db)
    existing = {d for (d,) in db.query(Destination.destination_id).all()}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    password_hash = get_password_hash(DEMO_PASSWORD)

    users = []
    first = int(get_next_user_id()[1:])  # se calcula una vez: la sesión de esa función no ve lo que agregamos
    for i, (name, (dep, prov, dist), profile) in enumerate(TRAVELERS):
        uid = f"U{first + i:05d}"
        created = now - timedelta(days=120 - i * 9, hours=rng.randint(0, 20))
        u = User(user_id=uid, name=name, email=_email(name), password_hash=password_hash, role="traveler",
                 is_active=True, account_status="active", residence_department=dep,
                 residence_province=prov, residence_city=dist, created_at=created, updated_at=created)
        db.add(u)
        db.flush()
        db.add(TravelerProfile(user_id=uid, tipo_interes="mixto", apply_ai_globally=i % 3 == 0, **profile))
        users.append(u)
    db.flush()

    favs = 0
    for i, dests in FAVORITES.items():
        for did in dests:
            if did in existing:
                db.add(Favorite(user_id=users[i].user_id, destination_id=did))
                favs += 1

    reviews = 0
    for did, items in REVIEWS.items():
        if did not in existing:
            continue
        authors = rng.sample(users, k=len(items))
        for (rating, body), author in zip(items, authors):
            when = now - timedelta(days=rng.randint(2, 110), hours=rng.randint(0, 23))
            when = max(when, author.created_at + timedelta(days=1))
            db.add(Review(
                review_id=f"rev-{uuid.uuid4().hex[:8]}", user_id=author.user_id, destination_id=did,
                rating_general=float(rating), review_text=body, visit_date=when.strftime("%Y-%m"),
                source="app", language="es", status="pending_processing",
                processing_month=when.strftime("%Y-%m"), created_at=when, updated_at=when,
            ))
            reviews += 1
    db.commit()
    return {"usuarios": len(users), "favoritos": favs, "reseñas": reviews}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--remove", action="store_true", help="Borra los datos demo y termina.")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.remove:
            print(f"Usuarios demo borrados: {remove(db)}")
        else:
            print("Datos demo creados:", seed(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
