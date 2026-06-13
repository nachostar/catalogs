"""
Procesa imágenes de productos específicos (por family_id):
  1. Descarga imagen original de Hereneo
  2. Crop cuadrado al centro (sin badge)
  3. Sube al bucket GCS
  4. Regenera el catálogo de Meta Ads en Sheets con las nuevas URLs

Variables de entorno necesarias:
  GOOGLE_SERVICE_ACCOUNT_JSON
  GCS_BUCKET
  SPREADSHEET_ID
"""

import io
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageOps
from google.cloud import storage
from google.oauth2.service_account import Credentials

from scrapers.hereneo import fetch_all
from parsers.hereneo_parser import build_meta_rows, FIELDNAMES_META
from outputs import sheets
from outputs.bigquery import get_bad_ctr_product_ids, get_vetados_ids

TARGET_FAMILY_IDS = {
    "1468", "1477", "1476", "1509", "1498", "1495", "1487", "1485",
    "1481", "1479", "1475", "1472", "1513", "1491", "737",  "1511",
    "1506", "1493", "1488", "796",  "1499", "1518", "1516",
}

GCS_BUCKET    = os.environ.get("GCS_BUCKET", "hereneo-catalogs")
IMAGES_PREFIX = "product-images-square"
SHEET_META    = "Catalogo"
TARGET_SIZE   = 800   # píxeles del lado del cuadrado resultante


def fetch_image(url: str) -> Image.Image:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return Image.open(io.BytesIO(resp.read())).convert("RGB")


def crop_square(img: Image.Image, size: int = TARGET_SIZE) -> Image.Image:
    """Recorta la imagen al cuadrado centrado exacto y redimensiona."""
    return ImageOps.fit(img, (size, size), Image.LANCZOS, centering=(0.5, 0.5))


def upload_to_gcs(img: Image.Image, blob_name: str, credentials_json: str) -> str:
    creds = Credentials.from_service_account_info(json.loads(credentials_json))
    client = storage.Client(
        credentials=creds,
        project=json.loads(credentials_json).get("project_id"),
    )
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_name)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    blob.upload_from_file(buf, content_type="image/jpeg")

    return f"https://storage.googleapis.com/{GCS_BUCKET}/{blob_name}"


def process_images(products: list, credentials_json: str) -> dict:
    """
    Filtra los productos de TARGET_FAMILY_IDS, procesa la imagen de cada variante
    y retorna {prod_id: nueva_url}.
    """
    url_map = {}
    targets = [
        p for p in products
        if str((p.get("family") or {}).get("id", "")) in TARGET_FAMILY_IDS
    ]
    print(f"Productos en familias objetivo: {len(targets)}")

    for i, prod in enumerate(targets, 1):
        prod_id = str(prod["id"])
        images  = prod.get("images") or []
        if not images:
            continue
        image_url = images[0].get("url", "")
        if not image_url:
            continue

        family_id = str((prod.get("family") or {}).get("id", ""))
        try:
            img = fetch_image(image_url)
            img_sq = crop_square(img)
            blob_name = f"{IMAGES_PREFIX}/{prod_id}.jpg"
            new_url = upload_to_gcs(img_sq, blob_name, credentials_json)
            url_map[prod_id] = new_url
            print(f"  [{i}/{len(targets)}] family={family_id} prod={prod_id} → {new_url}")
        except Exception as e:
            print(f"  [{i}/{len(targets)}] ERROR family={family_id} prod={prod_id}: {e}")

    return url_map


def main():
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        print("Error: falta GOOGLE_SERVICE_ACCOUNT_JSON")
        sys.exit(1)
    if not GCS_BUCKET:
        print("Error: falta GCS_BUCKET")
        sys.exit(1)

    print("=== Scraper Hereneo ===")
    products = fetch_all()
    print(f"Total productos: {len(products)}")

    print("\n=== Procesando imágenes cuadradas ===")
    url_map = process_images(products, sa_json)
    print(f"Imágenes procesadas: {len(url_map)}")

    print("\n=== Regenerando catálogo Meta Ads ===")
    rows_meta = build_meta_rows(products, url_map)

    bad_ctr_ids = get_bad_ctr_product_ids()
    vetados_ids = get_vetados_ids()
    excluded    = bad_ctr_ids | vetados_ids
    rows_meta_filtered = [r for r in rows_meta if r["sku"] not in excluded]
    print(f"Total: {len(rows_meta)} | Excluidos: {len(excluded)} | En Sheet: {len(rows_meta_filtered)}")

    print("\n=== Escribiendo Google Sheets ===")
    sheets.write(rows_meta_filtered, SHEET_META, FIELDNAMES_META)

    print("\nListo.")


if __name__ == "__main__":
    main()
