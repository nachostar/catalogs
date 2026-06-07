"""
Orquestador tur.com — scraper + parser → CSV local
"""

import csv
from pathlib import Path

from scrapers.tur import fetch_all
from parsers.tur_parser import (
    build_meta_rows, build_gmc_rows,
    FIELDNAMES_META, FIELDNAMES_GMC,
)

OUTPUT_DIR = Path(__file__).parent / "output" / "tur"


def write_csv(rows, fieldnames, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Guardado: {path} ({len(rows)} filas)")


def main():
    print("=== Scraper tur.com ===")
    products = fetch_all()
    print(f"Total: {len(products)} productos\n")

    print("=== Parser ===")
    rows_meta = build_meta_rows(products)
    rows_gmc  = build_gmc_rows(products)
    print(f"Meta: {len(rows_meta)} filas | GMC: {len(rows_gmc)} filas\n")

    print("=== Guardando CSVs ===")
    write_csv(rows_meta, FIELDNAMES_META, OUTPUT_DIR / "tur_meta_catalog.csv")
    write_csv(rows_gmc,  FIELDNAMES_GMC,  OUTPUT_DIR / "tur_gmc_catalog.csv")

    print("\nListo.")


if __name__ == "__main__":
    main()
