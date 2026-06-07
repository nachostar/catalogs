"""
Scraper de catálogo Hereneo → CSV + Google Sheets para Meta Ads
Uso: python scraper_hereneo.py
Variables de entorno:
  GOOGLE_SERVICE_ACCOUNT_JSON  — contenido JSON de la service account (en GitHub Actions viene del secret)
  SPREADSHEET_ID               — ID del Google Sheet destino
"""

import json
import csv
import re
import time
import os
import urllib.request
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials
from google.cloud import storage

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

BASE_API = "https://hereneo-backend-5f8b4f49b88e.herokuapp.com"
BASE_URL = "https://www.hereneo.cl"
OUTPUT_FILE = Path(__file__).parent / "hereneo_meta_catalog.csv"
PAGE_SIZE = 100
SHEET_NAME = "Catalogo"
OUTPUT_FILE_GMC = Path(__file__).parent / "hereneo_gmc_catalog.csv"
GCS_BUCKET = os.environ.get("GCS_BUCKET", "")          # nombre del bucket
GCS_BLOB = os.environ.get("GCS_BLOB", "hereneo_gmc_catalog.csv")  # path dentro del bucket

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

FIELDNAMES = [
    "id", "title", "description", "availability", "condition",
    "price", "sale_price", "link", "image_link", "additional_image_link",
    "brand", "google_product_category", "product_type",
    "color", "size", "gender", "material", "sku", "custom_number_1",
]

FIELDNAMES_GMC = [
    "id", "title", "description", "link", "image_link", "additional_image_link",
    "availability", "price", "sale_price", "brand", "condition",
    "google_product_category", "product_type", "item_group_id",
    "color", "size", "gender", "age_group", "material",
    "identifier_exists", "mpn",
]

GENDER_MAP = {
    "niño": "male",
    "hombre": "male",
    "niña": "female",
    "mujer": "female",
    "unisex": "unisex",
    "bebe": "unisex",
    "bebé": "unisex",
}

# Detecta age_group desde el nombre del talle
def get_age_group(prod):
    size = (prod.get("size", {}) or {}).get("name", "").lower()
    if any(s in size for s in ["rn", "recien", "0m", "nb", "newborn"]):
        return "newborn"
    if any(s in size for s in ["3m", "6m", "9m", "12m"]):
        return "infant"
    if any(s in size for s in ["18m", "24m", "2t", "3t", "4t", "2a", "3a", "4a"]):
        return "toddler"
    if any(s in size for s in ["5", "6", "7", "8", "10", "12", "14"]):
        return "kids"
    return "kids"  # default para esta tienda de ropa infantil


def get_gender_gmc(prod):
    fam = prod.get("family", {}) or {}
    gender_raw = (fam.get("gender", {}) or {}).get("name", "").lower().strip()
    return GENDER_MAP.get(gender_raw, "unisex")


# ---------------------------------------------------------------------------
# Availability checker (genérico, reutilizable para otros sitios)
# ---------------------------------------------------------------------------

# Palabras clave que indican producto agotado — agregar más según el sitio
SOLD_OUT_KEYWORDS = ["agotado", "sold out", "out of stock", "sin stock", "no disponible"]

# Configura en True si quieres verificar disponibilidad vía HTML del PDP
# Requiere playwright (más lento, pero funciona para cualquier sitio web)
CHECK_AVAILABILITY_FROM_HTML = os.environ.get("CHECK_AVAILABILITY_FROM_HTML", "false").lower() == "true"


def is_sold_out_from_html(url, keywords=None, timeout_ms=15000):
    """
    Abre la URL con un browser headless y busca keywords de agotado en el HTML renderizado.
    Funciona para SPAs (React, Vue, etc.) y sitios estáticos.
    Retorna True si está agotado, False si está disponible.
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright no instalado. Corre: pip install playwright && playwright install chromium")

    if keywords is None:
        keywords = SOLD_OUT_KEYWORDS

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2000)  # esperar renderizado JS
            content = page.content().lower()
            return any(kw.lower() in content for kw in keywords)
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_page(page, retries=5):
    url = f"{BASE_API}/v1/productfamily/all?limit={PAGE_SIZE}&page={page}"
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt == retries:
                raise RuntimeError(f"No se pudo obtener la página {page} tras {retries} intentos: {e}")
            wait = attempt * 5
            print(f"  [intento {attempt}/{retries}] Error en página {page}: {e}. Reintentando en {wait}s...")
            time.sleep(wait)


def fetch_all_products():
    all_products = []
    page = 1
    total_pages = None

    while total_pages is None or page <= total_pages:
        data = fetch_page(page)
        pagination = data.get("pagination", {})
        total_pages = pagination.get("totalPages", 1)
        products = data.get("products", [])
        all_products.extend(products)
        print(f"  Página {page}/{total_pages} — {len(products)} productos (total: {len(all_products)})")
        page += 1
        time.sleep(0.3)

    return all_products


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

def build_product_url(prod):
    fam = prod.get("family", {}) or {}
    subfamily = prod.get("product_subfamily", {}) or {}
    condition = subfamily.get("condition", "New")
    family_id = fam.get("id", "")
    family_slug = fam.get("slug", str(family_id))
    query = ""
    if condition and condition != "New":
        query = f"?condition={condition}"
        if condition == "Used":
            query += f"&productId={prod['id']}"
    return f"{BASE_URL}/products/{family_id}/{family_slug}{query}"


def get_availability(prod, url=None):
    # Primero chequeo rápido vía API
    api_status = "in stock" if prod.get("commercial_status") == "in_stock" else "out of stock"

    # Si está habilitado, verificar también el HTML del PDP
    if CHECK_AVAILABILITY_FROM_HTML and url:
        try:
            sold_out = is_sold_out_from_html(url)
            return "out of stock" if sold_out else "in stock"
        except Exception as e:
            print(f"  [availability] Error verificando {url}: {e} — usando dato de API")

    return api_status


def get_condition(prod):
    cond = (prod.get("product_subfamily", {}) or {}).get("condition", "New")
    return "used" if cond == "Used" else "new"


def build_title(prod):
    fam = prod.get("family", {}) or {}
    parts = [p for p in [
        (fam.get("brand", {}) or {}).get("name", ""),
        fam.get("name", ""),
        (prod.get("color", {}) or {}).get("name", ""),
        (prod.get("size", {}) or {}).get("name", ""),
    ] if p]
    return " - ".join(parts)[:150]


def get_image_url(prod):
    images = prod.get("images", [])
    return images[0].get("url", "") if images else ""


def get_additional_images(prod):
    images = prod.get("images", [])
    return ",".join(img.get("url", "") for img in images[1:5] if img.get("url"))


def get_description(prod):
    desc = (prod.get("family", {}) or {}).get("description", "") or ""
    return re.sub(r"<[^>]+>", "", desc)[:5000]


MATERIAL_REPLACEMENTS = [
    # Algodón y variantes con typos
    (r'\bald[oó]d[oó]n\b', 'Algodón'),
    (r'\balg[oó]d[oó]n\b', 'Algodón'),
    (r'\balgd[oó]n\b', 'Algodón'),
    (r'\bALGOD[OÓ]N\b', 'Algodón'),
    (r'\bAlgod[oó]n\b', 'Algodón'),
    # Orgánico — con y sin espacio antes de siguiente palabra
    (r'[Oo]rg[aá]nico', 'Orgánico'),
    # Poliéster
    (r'\bpoliester\b', 'Poliéster'),
    (r'\bPoliester\b', 'Poliéster'),
    (r'\bPOLIESTER\b', 'Poliéster'),
    # Poliamida
    (r'\bpoliamida\b', 'Poliamida'),
    # Elastano
    (r'\belastano\b', 'Elastano'),
    # Viscosa
    (r'\bviscosa\b', 'Viscosa'),
    # Acrílico
    (r'\bacrilico\b', 'Acrílico'),
    (r'\bAcrilico\b', 'Acrílico'),
    # Lino
    (r'\blino\b', 'Lino'),
    # Lana
    (r'\blana\b', 'Lana'),
    # Liocel
    (r'\bliocel\b', 'Liocel'),
    # Poliuretano
    (r'\bpoliuretano\b', 'Poliuretano'),
]

def normalize_material(text):
    if not text:
        return text
    # Colapsar saltos de línea y espacios múltiples
    text = re.sub(r'[\n\r]+', ' ', text)
    text = re.sub(r' {2,}', ' ', text).strip()
    for pattern, replacement in MATERIAL_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # Si el resultado es solo "100% Algodón" (con variantes de espacios), simplificar
    if re.fullmatch(r'100\s*%\s*Algodón', text.strip()):
        return 'Algodón'
    return text


def build_rows(products):
    rows = []
    seen_ids = set()

    for prod in products:
        prod_id = str(prod["id"])
        if prod_id in seen_ids:
            continue
        seen_ids.add(prod_id)

        title = build_title(prod)
        image_url = get_image_url(prod)
        if not title or not image_url:
            continue

        fam = prod.get("family", {}) or {}
        price = prod.get("price", 0)
        discount = prod.get("discount")
        sale_price = None
        if isinstance(discount, dict) and discount.get("percentage"):
            sale_price = round(price * (1 - discount["percentage"] / 100))

        url = build_product_url(prod)
        family_id = str(fam.get("id", ""))
        rows.append({
            "id": family_id,
            "title": title,
            "description": get_description(prod),
            "availability": get_availability(prod, url=url),
            "condition": get_condition(prod),
            "price": f"{price} CLP",
            "sale_price": f"{sale_price} CLP" if sale_price else "",
            "link": build_product_url(prod),
            "image_link": image_url,
            "additional_image_link": get_additional_images(prod),
            "brand": (fam.get("brand", {}) or {}).get("name", ""),
            "google_product_category": "",
            "product_type": (fam.get("category", {}) or {}).get("name", ""),
            "color": (prod.get("color", {}) or {}).get("name", ""),
            "size": (prod.get("size", {}) or {}).get("name", ""),
            "gender": (fam.get("gender", {}) or {}).get("name", ""),
            "material": normalize_material(fam.get("materials", "") or ""),
            "sku": str(fam.get("id", "")),
            "custom_number_1": (prod.get("sku", {}) or {}).get("value", prod.get("external_sku", "")),
        })

    return rows


# ---------------------------------------------------------------------------
# GMC rows
# ---------------------------------------------------------------------------

def build_gmc_rows(products):
    rows = []
    seen_ids = set()

    for prod in products:
        prod_id = str(prod["id"])
        if prod_id in seen_ids:
            continue
        seen_ids.add(prod_id)

        title = build_title(prod)
        image_url = get_image_url(prod)
        if not title or not image_url:
            continue

        fam = prod.get("family", {}) or {}
        price = prod.get("price", 0)
        discount = prod.get("discount")
        sale_price = None
        if isinstance(discount, dict) and discount.get("percentage"):
            sale_price = round(price * (1 - discount["percentage"] / 100))

        url = build_product_url(prod)
        family_id = str(fam.get("id", ""))
        mpn = (prod.get("sku", {}) or {}).get("value", prod.get("external_sku", ""))

        rows.append({
            "id": f"{family_id}_{prod_id}",
            "title": title,
            "description": get_description(prod),
            "link": url,
            "image_link": image_url,
            "additional_image_link": get_additional_images(prod),
            "availability": get_availability(prod, url=url),
            "price": f"{price} CLP",
            "sale_price": f"{sale_price} CLP" if sale_price else "",
            "brand": (fam.get("brand", {}) or {}).get("name", ""),
            "condition": get_condition(prod),
            "google_product_category": "",
            "product_type": (fam.get("category", {}) or {}).get("name", ""),
            "item_group_id": family_id,
            "color": (prod.get("color", {}) or {}).get("name", ""),
            "size": (prod.get("size", {}) or {}).get("name", ""),
            "gender": get_gender_gmc(prod),
            "age_group": get_age_group(prod),
            "material": normalize_material(fam.get("materials", "") or ""),
            "identifier_exists": "no",
            "mpn": mpn,
        })

    return rows


# ---------------------------------------------------------------------------
# Write CSV
# ---------------------------------------------------------------------------

def write_csv(rows):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV guardado: {OUTPUT_FILE}")


def write_gmc_csv(rows):
    with open(OUTPUT_FILE_GMC, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES_GMC)
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV GMC guardado: {OUTPUT_FILE_GMC}")


def upload_gmc_to_gcs():
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json or not GCS_BUCKET:
        print("Skipping GCS: faltan GOOGLE_SERVICE_ACCOUNT_JSON o GCS_BUCKET")
        return

    creds = Credentials.from_service_account_info(json.loads(sa_json))
    client = storage.Client(credentials=creds, project=json.loads(sa_json).get("project_id"))
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB)
    blob.upload_from_filename(str(OUTPUT_FILE_GMC), content_type="text/csv")
    print(f"GMC subido a GCS: gs://{GCS_BUCKET}/{GCS_BLOB}")
    print(f"URL pública: https://storage.googleapis.com/{GCS_BUCKET}/{GCS_BLOB}")


# ---------------------------------------------------------------------------
# Write Google Sheets
# ---------------------------------------------------------------------------

def write_google_sheets(rows, sheet_name=SHEET_NAME, fieldnames=FIELDNAMES):
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")

    if not sa_json or not spreadsheet_id:
        print("Skipping Google Sheets: faltan GOOGLE_SERVICE_ACCOUNT_JSON o SPREADSHEET_ID")
        return

    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)

    try:
        ws = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=2000, cols=len(fieldnames))

    data = [fieldnames] + [[row[f] for f in fieldnames] for row in rows]
    ws.clear()
    ws.update(data, value_input_option="RAW")
    print(f"Google Sheets actualizado: {len(rows)} filas en '{sheet_name}'")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("VERSION: 2026-06-07-v2")
    print(f"Playwright disponible: {PLAYWRIGHT_AVAILABLE}")
    print(f"Check HTML activado: {CHECK_AVAILABILITY_FROM_HTML}")
    print("Descargando productos de Hereneo...")
    products = fetch_all_products()
    print(f"Total descargado: {len(products)} productos\n")

    print("Transformando datos (Meta Ads)...")
    rows_meta = build_rows(products)
    print("Guardando CSV Meta Ads...")
    write_csv(rows_meta)
    print("Subiendo Meta Ads a Google Sheets...")
    write_google_sheets(rows_meta, sheet_name=SHEET_NAME, fieldnames=FIELDNAMES)

    print("\nTransformando datos (Google Merchant Center)...")
    rows_gmc = build_gmc_rows(products)
    print("Guardando CSV GMC...")
    write_gmc_csv(rows_gmc)
    print("Subiendo GMC a Google Cloud Storage...")
    upload_gmc_to_gcs()

    print(f"\nListo: {len(rows_meta)} productos Meta Ads | {len(rows_gmc)} productos GMC")


if __name__ == "__main__":
    main()
