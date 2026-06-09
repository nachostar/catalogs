"""
Orquestador diario: scraper + parser → Sheets (Meta) + GCS (GMC) + BigQuery
"""

import os
from pathlib import Path

from scrapers.hereneo import fetch_all
from parsers.hereneo_parser import (
    build_meta_rows, build_gmc_rows,
    FIELDNAMES_META, FIELDNAMES_GMC,
)
from outputs import sheets, gcs
from outputs.bigquery import write_catalog, get_bad_ctr_product_ids, get_vetados_ids

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

    print("=== BigQuery: catálogo completo ===")
    write_catalog(products)

    print("\n=== Parser ===")
    rows_meta = build_meta_rows(products, badge_url_map)
    rows_gmc  = build_gmc_rows(products, badge_url_map)
    print(f"Meta: {len(rows_meta)} filas | GMC: {len(rows_gmc)} filas")

    print("\n=== Filtros para Sheets ===")
    bad_ctr_ids = get_bad_ctr_product_ids()
    vetados_ids = get_vetados_ids()
    excluded_ids = bad_ctr_ids | vetados_ids
    rows_meta_filtered = [r for r in rows_meta if r["sku"] not in excluded_ids]
    print(f"Total: {len(rows_meta)} | Excluidos mal_ctr: {len(bad_ctr_ids)} | Vetados: {len(vetados_ids)} | En Sheet: {len(rows_meta_filtered)}")

    print("\n=== Outputs ===")
    sheets.write(rows_meta_filtered, SHEET_META, FIELDNAMES_META)
    gcs.upload_csv(rows_gmc, FIELDNAMES_GMC, GMC_BLOB, GMC_LOCAL)

    print("\nListo.")


if __name__ == "__main__":
    main()
