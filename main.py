"""
Orquestador diario: scraper + parser → Sheets (Meta) + GCS (GMC)
"""

import os
from pathlib import Path

from scrapers.hereneo import fetch_all
from parsers.hereneo_parser import (
    build_meta_rows, build_gmc_rows,
    FIELDNAMES_META, FIELDNAMES_GMC,
)
from outputs import sheets, gcs

SHEET_META     = "Catalogo"
GMC_BLOB       = os.environ.get("GCS_BLOB", "hereneo_gmc_catalog.csv")
GMC_LOCAL      = Path(__file__).parent / "hereneo_gmc_catalog.csv"
PROCESS_BADGES = os.environ.get("PROCESS_BADGES", "false").lower() == "true"


def main():
    print("=== Scraper ===")
    products = fetch_all()
    print(f"Total: {len(products)} productos\n")

    badge_url_map = {}
    if PROCESS_BADGES:
        print("=== Badges ===")
        from badge_processor import process_all
        sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        badge_url_map = process_all(products, sa_json)
        print(f"Imágenes procesadas: {len(badge_url_map)}\n")

    print("=== Parser ===")
    rows_meta = build_meta_rows(products, badge_url_map)
    rows_gmc  = build_gmc_rows(products, badge_url_map)
    print(f"Meta: {len(rows_meta)} filas | GMC: {len(rows_gmc)} filas\n")

    print("=== Outputs ===")
    sheets.write(rows_meta, SHEET_META, FIELDNAMES_META)
    gcs.upload_csv(rows_gmc, FIELDNAMES_GMC, GMC_BLOB, GMC_LOCAL)

    print("\nListo.")


if __name__ == "__main__":
    main()
