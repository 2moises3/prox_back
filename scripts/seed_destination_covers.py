"""Load curated Wikimedia Commons covers into Cloudinary and destination_media.

Run from proxvel_backend. Dry run by default; pass --apply to upload.
Use --db-port 5435 when connecting to the local Docker PostgreSQL from Windows.
"""

import argparse
import html
import io
import re
import sys
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


# Each title was checked against the corresponding place and its Commons file page.
FILES = {
    "catarata_ahuashiyacu": "Cataras de Ahuashiyacu.jpg",
    "chan_chan": "Chan Chan 02.jpg",
    "ciudadela_kuelap": "Kuelap P7171324mod.jpg",
    "huaca_luna": "Huaca de la luna vue site.jpg",
    "huaca_pucllana": "Huaca Pucllana-nX-1.jpg",
    "lineas_nazca": "Líneas de Nazca, Nazca, Perú, 2015-07-29, DD 52.JPG",
    "machu_picchu": "Machu Picchu, Perú, 2015-07-30, DD 60.JPG",
    "museo_sipan": "Tumbas Reales Señor de Sipan - panoramio.jpg",
    "ollantaytambo": "Ollantaytambo Archaeological site - terraces.jpg",
    "parque_aguas": "El Circuito Mágico del Agua del Parque de la Reserva 01.jpg",
    "parque_huascaran": "Huascarán en laguna Chinancocha Llanganuco.jpg",
    "reserva_paracas": "Paracas National Reserve.jpg",
    "valle_colca": "Valle del Colca, Perú, 2015-08-02, DD 64.JPG",
    "ventanillas_otuzco": "Ventanas de Otuzco.jpg",
}

USER_AGENT = "PROXVEL/1.0 (destination cover curation)"


def plain(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def commons_info(title):
    params = urllib.parse.urlencode({
        "action": "query", "titles": f"File:{title}", "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": 1400, "format": "json",
    })
    req = urllib.request.Request(
        f"https://commons.wikimedia.org/w/api.php?{params}",
        headers={"User-Agent": USER_AGENT},
    )
    import json
    with urllib.request.urlopen(req, timeout=30) as response:
        pages = json.load(response).get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    if "imageinfo" not in page:
        raise ValueError(f"Commons file missing: {title}")
    info = page["imageinfo"][0]
    meta = info.get("extmetadata", {})
    license_name = plain(meta.get("LicenseShortName", {}).get("value"))
    if not re.fullmatch(r"CC BY(?:-SA)? [234]\.0", license_name):
        raise ValueError(f"Unsupported license for {title}: {license_name}")
    artist = plain(meta.get("Artist", {}).get("value"))
    if not artist:
        raise ValueError(f"Missing author for {title}")
    source = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(
        page["title"].replace(" ", "_"), safe=":()"
    )
    license_url = "https://creativecommons.org/licenses/" + license_name.lower().replace("cc ", "").replace(" ", "/") + "/"
    return info.get("thumburl") or info["url"], artist, license_name, license_url, source


def image_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=40) as response:
        content_type = response.headers.get("Content-Type", "")
        data = response.read(5 * 1024 * 1024 + 1)
    if not content_type.startswith("image/") or len(data) > 5 * 1024 * 1024:
        raise ValueError("Downloaded file is not an image under 5 MB")
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--db-port", type=int)
    args = parser.parse_args()
    settings = get_settings()
    if not settings.DATABASE_URL:
        raise SystemExit("DATABASE_URL is missing")
    url = make_url(settings.DATABASE_URL)
    if args.db_port:
        url = url.set(port=args.db_port)
    engine = create_engine(url, pool_pre_ping=True)
    with Session(engine) as db:
        places = {d.destination_id: d for d in db.scalars(select(Destination)).all()}
        missing = set(places) - set(FILES)
        if missing:
            raise SystemExit(f"No curated file for: {sorted(missing)}")
        print(f"Destinations in database: {len(places)}")
        if args.apply and not all((settings.CLOUDINARY_CLOUD_NAME, settings.CLOUDINARY_API_KEY, settings.CLOUDINARY_API_SECRET)):
            raise SystemExit("Cloudinary credentials are missing")
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        uploaded = skipped = failed = 0
        for destination_id, title in FILES.items():
            if destination_id not in places:
                continue
            cover = db.scalar(select(DestinationMedia).where(
                DestinationMedia.destination_id == destination_id,
                DestinationMedia.media_type == "cover",
                DestinationMedia.is_active.is_(True),
            ))
            if cover:
                skipped += 1
                print(f"SKIP {destination_id}: active cover exists")
                continue
            if not args.apply:
                print(f"READY {destination_id}: {title}")
                continue
            uploaded_public_id = None
            try:
                image_url, artist, license_name, license_url, source = commons_info(title)
                data = image_bytes(image_url)
                public_id = f"{settings.CLOUDINARY_FOLDER.strip('/')}/{destination_id}/cover/wikimedia"
                result = cloudinary.uploader.upload(
                    io.BytesIO(data), public_id=public_id,
                    resource_type="image", overwrite=False, unique_filename=False,
                    context={"caption": title, "alt": places[destination_id].destination},
                )
                uploaded_public_id = result["public_id"]
                db.add(DestinationMedia(
                    destination_id=destination_id, media_type="cover", provider="cloudinary",
                    public_id=result["public_id"], url=result["secure_url"], position=0,
                    alt_text=places[destination_id].destination,
                    credit=artist,
                    license_note=f"{license_name} ({license_url}); fuente: {source}; imagen redimensionada",
                    is_active=True,
                ))
                db.commit()
                uploaded += 1
                print(f"UPLOADED {destination_id}: {result['secure_url']}")
            except Exception as exc:
                db.rollback()
                if uploaded_public_id:
                    try:
                        cloudinary.uploader.destroy(uploaded_public_id, resource_type="image")
                    except Exception as cleanup_error:
                        print(f"CLEANUP FAILED {destination_id}: {cleanup_error}")
                failed += 1
                print(f"FAILED {destination_id}: {type(exc).__name__}: {exc}")
        print(f"Result: uploaded={uploaded} skipped={skipped} failed={failed}")
        if failed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
