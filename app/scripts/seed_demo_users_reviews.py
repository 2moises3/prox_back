"""
PROXVEL Backend - Seed Demo Users and Reviews.
"""
import logging
import uuid
from app.config.database import SessionLocal
from app.models.user_model import User
from app.models.review_model import Review
from app.models.review_aspect_rating_model import ReviewAspectRating

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)

def run_seeder():
    db = SessionLocal()
    try:
        logger.info("Iniciando seed de usuarios demo y reseñas...")

        # 1. Crear usuarios demo
        users_data = [
            {"user_id": "U00001", "name": "Usuario Demo 1", "email": "demo1@proxvel.local"},
            {"user_id": "U00002", "name": "Usuario Demo 2", "email": "demo2@proxvel.local"},
            {"user_id": "U00003", "name": "Usuario Demo 3", "email": "demo3@proxvel.local"},
        ]

        for u_data in users_data:
            existing_user = db.query(User).filter(User.user_id == u_data["user_id"]).first()
            if not existing_user:
                new_user = User(
                    user_id=u_data["user_id"],
                    name=u_data["name"],
                    email=u_data["email"],
                    password_hash="demo_not_for_auth",
                    role="user",
                    is_active=True
                )
                db.add(new_user)
        db.commit()
        logger.info("Usuarios demo creados.")

        # 2. Crear reseñas demo
        reviews_data = [
            {
                "user_id": "U00001", "destination_id": "machu-picchu", "rating_general": 5.0,
                "review_text": "El lugar fue impresionante y la vista superó mis expectativas, aunque había bastante afluencia de visitantes.",
                "aspect_ratings": [
                    {"aspect": "atractivos", "rating": 5.0, "comment": "El paisaje fue excelente."},
                    {"aspect": "accesibilidad", "rating": 3.0, "comment": "El acceso requiere planificación."},
                    {"aspect": "clima", "rating": 4.0, "comment": "Buen clima en la mañana."},
                    {"aspect": "aforo_multitudes", "rating": 2.0, "comment": "Demasiada gente."}
                ]
            },
            {
                "user_id": "U00002", "destination_id": "machu-picchu", "rating_general": 4.0,
                "review_text": "La experiencia fue buena, pero el acceso puede ser complicado si no se planifica con anticipación.",
                "aspect_ratings": [
                    {"aspect": "accesibilidad", "rating": 2.0, "comment": "Muy difícil subir."},
                    {"aspect": "costos", "rating": 3.0, "comment": "Algo caro."},
                    {"aspect": "seguridad", "rating": 5.0, "comment": "Me sentí seguro."},
                    {"aspect": "limpieza", "rating": 5.0, "comment": "Todo impecable."}
                ]
            },
            {
                "user_id": "U00001", "destination_id": "lago-titicaca", "rating_general": 4.5,
                "review_text": "Me gustó mucho el paisaje y la experiencia cultural, aunque algunos costos podrían estar mejor explicados.",
                "aspect_ratings": [
                    {"aspect": "atractivos", "rating": 5.0, "comment": "Cultura fascinante."},
                    {"aspect": "costos", "rating": 3.0, "comment": "Faltó claridad."},
                    {"aspect": "atencion_servicio", "rating": 4.0, "comment": "Gente amable."},
                    {"aspect": "alojamiento", "rating": 4.0, "comment": "Cómodo pero rústico."}
                ]
            },
            {
                "user_id": "U00003", "destination_id": "lago-titicaca", "rating_general": 5.0,
                "review_text": "El destino es bonito y tranquilo, ideal para tomar fotografías y conocer más de la cultura local.",
                "aspect_ratings": [
                    {"aspect": "atractivos", "rating": 5.0, "comment": "Fotos increíbles."},
                    {"aspect": "clima", "rating": 3.0, "comment": "Hace bastante frío."},
                    {"aspect": "seguridad", "rating": 5.0, "comment": "Muy tranquilo."},
                    {"aspect": "gastronomia", "rating": 4.0, "comment": "Comida típica deliciosa."}
                ]
            },
            {
                "user_id": "U00002", "destination_id": "circuito-magico-del-agua", "rating_general": 4.0,
                "review_text": "El espectáculo visual fue atractivo, accesible y recomendado para una visita corta en la ciudad.",
                "aspect_ratings": [
                    {"aspect": "atractivos", "rating": 5.0, "comment": "Show de luces muy bonito."},
                    {"aspect": "accesibilidad", "rating": 5.0, "comment": "Fácil de llegar."},
                    {"aspect": "costos", "rating": 5.0, "comment": "Entrada muy barata."},
                    {"aspect": "gastronomia", "rating": 2.0, "comment": "Pocas opciones dentro."}
                ]
            },
            {
                "user_id": "U00003", "destination_id": "circuito-magico-del-agua", "rating_general": 3.5,
                "review_text": "La visita fue agradable, aunque en horas de mayor afluencia puede sentirse algo saturado.",
                "aspect_ratings": [
                    {"aspect": "aforo_multitudes", "rating": 2.0, "comment": "Muy saturado de noche."},
                    {"aspect": "limpieza", "rating": 4.0, "comment": "Limpio pese a la gente."},
                    {"aspect": "seguridad", "rating": 3.0, "comment": "Hay que tener cuidado con las cosas."},
                    {"aspect": "atencion_servicio", "rating": 4.0, "comment": "Personal atento."}
                ]
            }
        ]

        for r_data in reviews_data:
            # Check if this user-destination review combo already exists roughly to be idempotent
            existing = db.query(Review).filter(
                Review.user_id == r_data["user_id"],
                Review.destination_id == r_data["destination_id"]
            ).first()

            if not existing:
                review_id = f"rev-{uuid.uuid4().hex[:8]}"
                new_review = Review(
                    review_id=review_id,
                    user_id=r_data["user_id"],
                    destination_id=r_data["destination_id"],
                    rating_general=r_data["rating_general"],
                    review_text=r_data["review_text"],
                    visit_date="2026-06-09",
                    source="app",
                    language="es",
                    is_verified_visit=False,
                    validation_method="self_report_pending",
                    status="pending_processing",
                    processing_month="2026-06"
                )
                db.add(new_review)

                for ar in r_data["aspect_ratings"]:
                    new_ar = ReviewAspectRating(
                        review_id=review_id,
                        aspect=ar["aspect"],
                        rating=ar["rating"],
                        comment=ar["comment"]
                    )
                    db.add(new_ar)

        db.commit()
        logger.info("Reseñas demo creadas.")
        logger.info("Seeding de usuarios y reseñas completado.")

    except Exception as e:
        logger.error(f"Error durante seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_seeder()
