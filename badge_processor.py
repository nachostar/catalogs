"""
Procesa imágenes de productos agregando badge "Revende por $XX.XXX".
Precio de reventa = 60% del precio original.
Sube las imágenes procesadas a GCS y retorna las nuevas URLs.
"""

import io
import json
import math
import os
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GCS_BUCKET = os.environ.get("GCS_BUCKET", "")
IMAGES_PREFIX = "product-images-tagged"
BADGE_COLOR_BG = (255, 255, 255, 184)   # blanco semitransparente
BADGE_COLOR_TEXT = (47, 143, 91)         # verde hereneo
BADGE_COLOR_BORDER = (215, 234, 222, 200)
RESALE_RATIO = 0.60


def format_price(price: int) -> str:
    return "$" + f"{price:,}".replace(",", ".")


def fetch_image(url: str) -> Image.Image:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return Image.open(io.BytesIO(resp.read())).convert("RGBA")


def get_font(size: int):
    font_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def add_badge(img: Image.Image, price: int, target_width: int = 800) -> Image.Image:
    # Redimensionar manteniendo proporción
    ratio = target_width / img.width
    new_h = int(img.height * ratio)
    img = img.resize((target_width, new_h), Image.LANCZOS).convert("RGBA")

    resale_price = math.floor(price * RESALE_RATIO)
    text = f"Revende por {format_price(resale_price)}"

    font_size = max(18, target_width // 28)
    font = get_font(font_size)

    # Medir texto
    dummy = Image.new("RGBA", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy)
    bbox = draw_dummy.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x, pad_y = 20, 10
    badge_w = text_w + pad_x * 2
    badge_h = text_h + pad_y * 2
    radius = badge_h // 2
    margin = int(target_width * 0.04)

    # Crear badge con esquinas redondeadas
    badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.rounded_rectangle([0, 0, badge_w - 1, badge_h - 1], radius=radius,
                         fill=BADGE_COLOR_BG, outline=BADGE_COLOR_BORDER, width=1)
    bd.text((pad_x, pad_y), text, font=font, fill=BADGE_COLOR_TEXT)

    # Posición: esquina inferior izquierda
    x = margin
    y = img.height - badge_h - margin

    result = img.copy()
    result.alpha_composite(badge, (x, y))
    return result.convert("RGB")


def upload_to_gcs(img: Image.Image, blob_name: str, credentials_json: str) -> str:
    from google.cloud import storage
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_info(json.loads(credentials_json))
    client = storage.Client(credentials=creds,
                            project=json.loads(credentials_json).get("project_id"))
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_name)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    blob.upload_from_file(buf, content_type="image/jpeg")

    return f"https://storage.googleapis.com/{GCS_BUCKET}/{blob_name}"


def process_product_image(prod_id: str, image_url: str, price: int,
                          credentials_json: str) -> str:
    """
    Descarga la imagen, agrega el badge y sube a GCS.
    Retorna la URL pública de la imagen procesada.
    """
    try:
        img = fetch_image(image_url)
        img_with_badge = add_badge(img, price)
        blob_name = f"{IMAGES_PREFIX}/{prod_id}.jpg"
        new_url = upload_to_gcs(img_with_badge, blob_name, credentials_json)
        return new_url
    except Exception as e:
        print(f"  [badge] Error en producto {prod_id}: {e}")
        return image_url  # fallback a imagen original


def process_all(products: list, credentials_json: str) -> dict:
    """
    Procesa todas las imágenes y retorna dict {prod_id: nueva_url}.
    """
    if not GCS_BUCKET or not credentials_json:
        print("Skipping badge: faltan GCS_BUCKET o credenciales")
        return {}

    url_map = {}
    total = len(products)
    for i, prod in enumerate(products, 1):
        prod_id = str(prod["id"])
        images = prod.get("images", [])
        if not images:
            continue
        image_url = images[0].get("url", "")
        price = prod.get("price", 0)
        if not image_url or not price:
            continue

        new_url = process_product_image(prod_id, image_url, price, credentials_json)
        url_map[prod_id] = new_url

        if i % 50 == 0 or i == total:
            print(f"  [{i}/{total}] procesadas")

    return url_map
