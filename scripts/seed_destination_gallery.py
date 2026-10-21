"""Add two curated gallery images per destination to Cloudinary and PostgreSQL.

Run from proxvel_backend. Dry run by default; pass --apply to upload.
Use --db-port 5435 from Windows for the local Docker PostgreSQL.
"""

import argparse
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cloudinary
import cloudinary.uploader
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.destination_media_model import DestinationMedia
from app.models.destination_model import Destination
from seed_destination_covers import USER_AGENT, image_bytes, plain


# Ahuashiyacu has one Commons photograph of the waterfall (already the cover).
# Its gallery shows two explicitly labelled scenes from the surrounding Cordillera Escalera.
GALLERY = {
    "catarata_ahuashiyacu": [
        ("Paisaje de la Cordillera Escalera.jpg", "Paisaje de la Cordillera Escalera, cerca de Ahuashiyacu"),
        ("Cascada en río Shilcayo en reserva botánica. Cordillera Escalera.jpg", "Cascada del río Shilcayo en la Cordillera Escalera"),
    ],
    "chan_chan": [
        ("Chan Chan - reliefs.jpg", "Relieves del templo Tschudi en Chan Chan"),
        ("Chan Chan panel.jpg", "Panel arqueológico de Chan Chan"),
    ],
    "ciudadela_kuelap": [
        ("Kuelap P7171312mod.jpg", "Vista de la ciudadela de Kuélap"),
        ("Kuelap puerta P7171271mod.jpg", "Acceso a la ciudadela de Kuélap"),
    ],
    "huaca_luna": [
        ("Huaca de la Luna - Août 2007.jpg", "Fachada pintada de la Huaca de la Luna"),
        ("Ausgrabungsstätte Huaca de la Luna 44.jpg", "Zona arqueológica de la Huaca de la Luna"),
    ],
    "huaca_pucllana": [
        ("Huaca Pucllana-nX-12.jpg", "Zona arqueológica de Huaca Pucllana"),
        ("Huaca Pucllana-nX-8.jpg", "Vista de Huaca Pucllana en Lima"),
    ],
    "lineas_nazca": [
        ("Líneas de Nazca, Nazca, Perú, 2015-07-29, DD 54.JPG", "Geoglifo de la araña en las Líneas de Nazca"),
        ("Líneas de Nazca, Nazca, Perú, 2015-07-29, DD 55.JPG", "Geoglifo del cóndor en las Líneas de Nazca"),
    ],
    "machu_picchu": [
        ("Machu Picchu, Perú, 2015-07-30, DD 47.JPG", "Viviendas antiguas de Machu Picchu"),
        ("Machu Picchu terraces.jpg", "Terrazas de Machu Picchu"),
    ],
    "museo_sipan": [
        ("Tumbas Reales de Sipán Museum 01.jpg", "Exterior del Museo Tumbas Reales de Sipán"),
        ("Tumbas Reales de Sipán Museum 02.jpg", "Museo Tumbas Reales de Sipán en Lambayeque"),
    ],
    "ollantaytambo": [
        ("Ollantaytambo Archaeological Site.jpg", "Sitio arqueológico de Ollantaytambo"),
        ("Ollantaytambo Archaeological site - bath.jpg", "Baño del sitio arqueológico de Ollantaytambo"),
    ],
    "parque_aguas": [
        ("El Circuito Mágico del Agua del Parque de la Reserva 02.jpg", "Fuentes del Circuito Mágico del Agua"),
        ("El Circuito Mágico del Agua del Parque de la Reserva 03.jpg", "Vista del Circuito Mágico del Agua de Lima"),
    ],
    "parque_huascaran": [
        ("Huascarán desde quebrada Llanganuco.jpg", "Nevado Huascarán desde Llanganuco"),
        ("Huascarán National Park - Peru 27.jpg", "Paisaje del Parque Nacional Huascarán"),
    ],
    "reserva_paracas": [
        ("Reserva Nacional de Paracas, Playa Supay, Ica, Perú.JPG", "Playa Supay en la Reserva Nacional de Paracas"),
        ("Desert of Paracas, Peru - Paracas National Reserve.jpg", "Desierto de la Reserva Nacional de Paracas"),
    ],
    "valle_colca": [
        ("Valle del Colca.jpg", "Paisaje del Valle del Colca"),
        ("Peru - Colca Canyon - Andean condor (Vultur gryphus) 01.jpg", "Cóndor andino en el Cañón del Colca"),
    ],
    "ventanillas_otuzco": [
        ("Ventanillas de Otuzco01.jpg", "Nichos funerarios de las Ventanillas de Otuzco"),
        ("Ventanillas de Otuzco02.jpg", "Vista de las Ventanillas de Otuzco"),
    ],
}


def commons_batch(titles):
    """Fetch file URLs, licenses, and authors in small API batches."""
    found = {}
    for start in range(0, len(titles), 14):
        chunk = titles[start:start + 14]
        params = urllib.parse.urlencode({
            "action": "query", "titles": "|".join(f"File:{title}" for title in chunk),
            "prop": "imageinfo", "iiprop": "url|size|extmetadata",
            "iiurlwidth": 1400, "format": "json",
        })
        request = urllib.request.Request(
            "https://commons.wikimedia.org/w/api.php?" + params,
            headers={"User-Agent": USER_AGENT},
        )
        for attempt in range(5):
            try:
                with urllib.request.urlopen(request, timeout=40) as response:
                    pages = json.load(response).get("query", {}).get("pages", {})
                break
            except urllib.error.HTTPError as error:
                if error.code != 429 or attempt == 4:
                    raise
                time.sleep(8 * (attempt + 1))
        for page in pages.values():
            if "imageinfo" not in page:
                continue
            info = page["imageinfo"][0]
            metadata = info.get("extmetadata", {})
            license_name = plain(metadata.get("LicenseShortName", {}).get("value"))
            artist = plain(metadata.get("Artist", {}).get("value"))
            if not re.fullmatch(r"CC BY(?:-SA)? [234]\.0", license_name) or not artist:
                raise ValueError(f"Missing author or unsupported license: {page['title']} ({license_name})")
            source = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(
                page["title"].replace(" ", "_"), safe=":()"
            )
            license_url = "https://creativecommons.org/licenses/" + license_name.lower().replace("cc ", "").replace(" ", "/") + "/"
            found[page["title"].removeprefix("File:").casefold()] = (
                info.get("thumburl") or info["url"], artist, license_name, license_url, source,
            )
    missing = [title for title in titles if title.casefold() not in found]
    if missing:
        raise ValueError(f"Commons files missing: {missing}")
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--db-port", type=int)
    args = parser.parse_args()
    settings = get_settings()
    if not settings.DATABASE_URL:
        raise SystemExit("DATABASE_URL is missing")
    db_url = make_url(settings.DATABASE_URL)
    if args.db_port:
        db_url = db_url.set(port=args.db_port)
    engine = create_engine(db_url, pool_pre_ping=True)
    with Session(engine) as db:
        places = {place.destination_id: place for place in db.scalars(select(Destination)).all()}
        missing = set(places) - set(GALLERY)
        if missing:
            raise SystemExit(f"No curated gallery for: {sorted(missing)}")
        if args.apply and not all((settings.CLOUDINARY_CLOUD_NAME, settings.CLOUDINARY_API_KEY, settings.CLOUDINARY_API_SECRET)):
            raise SystemExit("Cloudinary credentials are missing")
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        todo = []
        skipped = 0
        for destination_id, entries in GALLERY.items():
            if destination_id not in places:
                continue
            for position, (title, alt_text) in enumerate(entries, start=1):
                digest = hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]
                public_id = f"{settings.CLOUDINARY_FOLDER.strip('/')}/{destination_id}/gallery/commons-{digest}"
                existing = db.scalar(select(DestinationMedia).where(DestinationMedia.public_id == public_id))
                if existing:
                    skipped += 1
                    print(f"SKIP {destination_id} gallery {position}: already registered")
                    continue
                todo.append((destination_id, position, title, alt_text, public_id))
        print(f"Destinations={len(places)} gallery_to_add={len(todo)} skipped={skipped}", flush=True)
        if not todo:
            return
        info_by_title = commons_batch(list(dict.fromkeys(item[2] for item in todo)))
        print("Commons source, author, and license verified", flush=True)
        if not args.apply:
            for destination_id, position, title, _, _ in todo:
                print(f"READY {destination_id} gallery {position}: {title}")
            return
        uploaded = failed = 0
        for destination_id, position, title, alt_text, public_id in todo:
            uploaded_public_id = None
            try:
                image_url, artist, license_name, license_url, source = info_by_title[title.casefold()]
                image = image_bytes(image_url)
                result = cloudinary.uploader.upload(
                    io.BytesIO(image), public_id=public_id,
                    resource_type="image", overwrite=False, unique_filename=False,
                    context={"caption": title, "alt": alt_text},
                )
                uploaded_public_id = result["public_id"]
                db.add(DestinationMedia(
                    destination_id=destination_id, media_type="gallery", provider="cloudinary",
                    public_id=uploaded_public_id, url=result["secure_url"], position=position,
                    alt_text=alt_text, credit=artist,
                    license_note=f"{license_name} ({license_url}); fuente: {source}; imagen redimensionada",
                    is_active=True,
                ))
                db.commit()
                uploaded += 1
                print(f"UPLOADED {destination_id} gallery {position}", flush=True)
            except Exception as error:
                db.rollback()
                if uploaded_public_id:
                    try:
                        cloudinary.uploader.destroy(uploaded_public_id, resource_type="image")
                    except Exception as cleanup_error:
                        print(f"CLEANUP FAILED {destination_id}: {cleanup_error}", flush=True)
                failed += 1
                print(f"FAILED {destination_id} gallery {position}: {type(error).__name__}: {error}", flush=True)
        print(f"Result: uploaded={uploaded} skipped={skipped} failed={failed}", flush=True)
        if failed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
