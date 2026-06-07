"""
Métricas de Meta Ads → BigQuery
Trae datos por campaña, anuncio y producto para la cuenta de Hereneo.

Variables de entorno:
  META_ACCESS_TOKEN
  META_AD_ACCOUNT_ID
  GOOGLE_SERVICE_ACCOUNT_JSON
  GCP_PROJECT (default: quetri)
  DATE_FROM   (default: ayer)
  DATE_TO     (default: ayer)
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.meta_ads import fetch_all
from parsers.meta_ads_parser import parse_all
from outputs.bigquery import write_metrics

TOKEN      = os.environ.get("META_ACCESS_TOKEN", "")
ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "1361105058247847")

yesterday  = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
DATE_FROM  = os.environ.get("DATE_FROM", yesterday)
DATE_TO    = os.environ.get("DATE_TO", yesterday)

LEVELS = ("campaign", "ad", "product")


def main():
    if not TOKEN:
        print("Error: falta META_ACCESS_TOKEN")
        return

    print(f"=== Meta Ads Metrics ===")
    print(f"Cuenta: {ACCOUNT_ID}")
    print(f"Período: {DATE_FROM} → {DATE_TO}\n")

    print("=== Scraper ===")
    raw = fetch_all(ACCOUNT_ID, TOKEN, DATE_FROM, DATE_TO, levels=LEVELS)

    print("\n=== Parser ===")
    rows = parse_all(raw, ACCOUNT_ID)
    print(f"Total filas: {len(rows)}")

    print("\n=== BigQuery ===")
    write_metrics(rows, table_name="daily_metrics", date_str=DATE_FROM)

    print("\nListo.")


if __name__ == "__main__":
    main()
