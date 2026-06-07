"""
Scraper de Hereneo — obtiene productos crudos desde la API.
Adaptable: para otro sitio crear scrapers/otro_sitio.py con la misma interfaz.
"""

import json
import time
import urllib.request

BASE_API = "https://hereneo-backend-5f8b4f49b88e.herokuapp.com"
PAGE_SIZE = 100


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


def fetch_all():
    """Retorna lista de productos crudos desde la API de Hereneo."""
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
