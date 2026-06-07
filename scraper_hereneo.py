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

BASE_API = "https://hereneo-backend-5f8b4f49b88e.herokuapp.com"
BASE_URL = "https://www.hereneo.cl"
OUTPUT_FILE = Path(__file__).parent / "hereneo_meta_catalog.csv"
PAGE_SIZE = 100
SHEET_NAME = "Catalogo"

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


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_page(page, retries=5):
    url = f"{BASE_API}/v1/productfamily/all?limit={PAGE_SIZE}&page={page}"
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            wait = attempt * 10
            print(f"  [intento {attempt}/{retries}] Error en página {page}: {e}. Reintentando en {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"No se pudo obtener la página {page} tras {retries} intentos.")


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


def get_availability(prod):
    return "in stock" if prod.get("commercial_status") == "in_stock" else "out of stock"


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

        rows.append({
            "id": prod_id,
            "title": title,
            "description": get_description(prod),
            "availability": get_availability(prod),
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
            "material": fam.get("materials", "") or "",
            "sku": str(fam.get("id", "")),
            "custom_number_1": (prod.get("sku", {}) or {}).get("value", prod.get("external_sku", "")),
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


# ---------------------------------------------------------------------------
# Write Google Sheets
# ---------------------------------------------------------------------------

def write_google_sheets(rows):
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")

    if not sa_json or not spreadsheet_id:
        print("Skipping Google Sheets: faltan GOOGLE_SERVICE_ACCOUNT_JSON o SPREADSHEET_ID")
        return

    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)

    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_NAME, rows=2000, cols=len(FIELDNAMES))

    data = [FIELDNAMES] + [[row[f] for f in FIELDNAMES] for row in rows]
    ws.clear()
    ws.update(data, value_input_option="RAW")
    print(f"Google Sheets actualizado: {len(rows)} filas en '{SHEET_NAME}'")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Descargando productos de Hereneo...")
    products = fetch_all_products()
    print(f"Total descargado: {len(products)} productos\n")

    print("Transformando datos...")
    rows = build_rows(products)

    print("Guardando CSV...")
    write_csv(rows)

    print("Subiendo a Google Sheets...")
    write_google_sheets(rows)

    print(f"\nListo: {len(rows)} productos procesados.")


if __name__ == "__main__":
    main()
