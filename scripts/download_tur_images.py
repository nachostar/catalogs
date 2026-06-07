"""
Descarga imágenes de tur.com usando Playwright (browser real).
El CDN bloquea requests programáticos pero no browsers reales.

Uso: python scripts/download_tur_images.py
"""

import sys
import csv
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.tur_parser import get_image_url

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "tur" / "images"
CATALOG_CSV = Path(__file__).parent.parent / "output" / "tur" / "tur_meta_catalog.csv"
BATCH_SIZE = 50  # páginas por contexto de browser antes de reiniciar


def load_image_urls():
    """Lee las URLs de imagen del CSV ya generado."""
    rows = []
    with open(CATALOG_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("image_link"):
                rows.append({
                    "id": row["id"],
                    "url": row["image_link"],
                    "title": row["title"][:50],
                })
    return rows


def download_images(items):
    from playwright.sync_api import sync_playwright

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    already_done = {f.stem for f in OUTPUT_DIR.glob("*")}
    pending = [i for i in items if i["id"] not in already_done]
    total = len(pending)
    print(f"Total: {len(items)} | Ya descargadas: {len(already_done)} | Pendientes: {total}")

    if not pending:
        print("Todas las imágenes ya están descargadas.")
        return

    downloaded = 0
    errors = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for i, item in enumerate(pending):
            # Reiniciar contexto cada BATCH_SIZE para evitar memory leaks
            if i % BATCH_SIZE == 0:
                if i > 0:
                    context.close()
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    extra_http_headers={"Referer": "https://www.tur.com/"},
                )

            try:
                response = context.request.get(item["url"], timeout=20000)
                if response.ok:
                    content_type = response.headers.get("content-type", "")
                    ext = ".webp" if "webp" in content_type else ".jpg"
                    filename = OUTPUT_DIR / f"{item['id']}{ext}"
                    filename.write_bytes(response.body())
                    downloaded += 1
                    if downloaded % 100 == 0 or downloaded == total:
                        print(f"  [{downloaded}/{total}] descargadas — {item['title']}")
                else:
                    print(f"  [ERROR {response.status}] {item['id']}: {item['url']}")
                    errors += 1
            except Exception as e:
                print(f"  [ERROR] {item['id']}: {e}")
                errors += 1

            time.sleep(0.05)

        context.close()
        browser.close()

    print(f"\nListo: {downloaded} descargadas, {errors} errores.")
    print(f"Carpeta: {OUTPUT_DIR}")


def main():
    print("Leyendo catálogo...")
    items = load_image_urls()
    print(f"Productos en catálogo: {len(items)}")
    download_images(items)


if __name__ == "__main__":
    main()
