"""
Backfill de métricas Meta Ads → BigQuery.
Re-corre cada día en el rango y sobreescribe con datos limpios.
Uso: DATE_FROM=2026-06-07 DATE_TO=2026-06-09 python scripts/backfill_metrics.py
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.meta_ads import fetch_all
from parsers.meta_ads_parser import parse_all, parse_placements
from outputs.bigquery import write_metrics, enrich_product_urls, write_placements

TOKEN      = os.environ.get("META_ACCESS_TOKEN", "")
ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "1361105058247847")

yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
DATE_FROM = os.environ.get("DATE_FROM", "2026-06-07")
DATE_TO   = os.environ.get("DATE_TO", yesterday)


def run_day(date_str):
    print(f"\n{'='*50}")
    print(f"Procesando: {date_str}")
    print(f"{'='*50}")

    raw = fetch_all(ACCOUNT_ID, TOKEN, date_str, date_str)

    rows = parse_all(raw, ACCOUNT_ID)
    print(f"Filas parseadas: {len(rows)}")

    write_metrics(rows, date_from=date_str, date_to=date_str)

    placement_rows = parse_placements(raw.get("placement", []), ACCOUNT_ID)
    write_placements(placement_rows, date_from=date_str, date_to=date_str)

    enrich_product_urls(date_from=date_str, date_to=date_str)


def main():
    if not TOKEN:
        print("Error: falta META_ACCESS_TOKEN")
        sys.exit(1)

    start = datetime.strptime(DATE_FROM, "%Y-%m-%d")
    end   = datetime.strptime(DATE_TO,   "%Y-%m-%d")

    dates = []
    d = start
    while d <= end:
        dates.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)

    print(f"Backfill: {DATE_FROM} → {DATE_TO} ({len(dates)} días)")
    print(f"Cuenta: {ACCOUNT_ID}")

    for i, date_str in enumerate(dates, 1):
        run_day(date_str)
        if i < len(dates):
            time.sleep(2)  # pausa entre días para no saturar la API

    print(f"\nBackfill completo: {len(dates)} días procesados.")


if __name__ == "__main__":
    main()
