"""
Scraper de tur.com — obtiene productos (tours/experiencias) desde la API.
Interfaz compatible con scrapers/hereneo.py: retorna lista de dicts.
"""

import json
import time
import urllib.request
import urllib.parse

BASE_API = "https://www.tur.com/tur/api"
PAGE_SIZE = 100
LOCALE = "es"
CURRENCY = "CLP"


def fetch_page(cursor=None, retries=5):
    params = {
        "locale": LOCALE,
        "currency": CURRENCY,
        "perPage": PAGE_SIZE,
    }
    if cursor:
        params["cursor"] = cursor

    url = f"{BASE_API}/v1/marketplace/octo/products?{urllib.parse.urlencode(params)}"

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt == retries:
                raise RuntimeError(f"No se pudo obtener página (cursor={cursor}) tras {retries} intentos: {e}")
            wait = attempt * 5
            print(f"  [intento {attempt}/{retries}] Error: {e}. Reintentando en {wait}s...")
            time.sleep(wait)


def fetch_all():
    """Retorna lista de productos crudos desde la API de tur.com."""
    all_products = []
    cursor = None
    page = 1

    while True:
        data = fetch_page(cursor)
        products = data.get("data", [])
        meta = data.get("meta", {})
        total = meta.get("total", "?")
        all_products.extend(products)

        print(f"  Página {page} — {len(products)} productos (total: {len(all_products)}/{total})")

        cursor = meta.get("cursor")
        if not cursor or not products:
            break

        page += 1
        time.sleep(0.3)

    return all_products
