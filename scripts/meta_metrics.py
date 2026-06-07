"""
Meta Ads Metrics → Google Sheets
Trae impresiones, clics, gasto y conversiones de la cuenta publicitaria de Meta.
Uso: python meta_metrics.py
Variables de entorno:
  META_ACCESS_TOKEN        — token de acceso de Meta
  META_AD_ACCOUNT_ID       — ID de la cuenta publicitaria (sin 'act_')
  GOOGLE_SERVICE_ACCOUNT_JSON
  SPREADSHEET_ID
"""

import json
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

META_API_VERSION = "v19.0"
META_BASE = f"https://graph.facebook.com/{META_API_VERSION}"

AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "1361105058247847")
ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")

SHEET_NAME_METRICS = "Metricas Meta"
DAYS_BACK = 30  # últimos 30 días

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

FIELDNAMES_METRICS = [
    "fecha_inicio", "fecha_fin",
    "campaign_name", "adset_name", "ad_name",
    "impresiones", "clics", "ctr", "cpc",
    "importe_gastado",
    "conversiones", "costo_por_conversion",
    "alcance",
]


# ---------------------------------------------------------------------------
# Meta API
# ---------------------------------------------------------------------------

def meta_get(endpoint, params=None):
    if params is None:
        params = {}
    params["access_token"] = ACCESS_TOKEN
    url = f"{META_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_meta_metrics():
    date_end = datetime.today().strftime("%Y-%m-%d")
    date_start = (datetime.today() - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")

    fields = ",".join([
        "campaign_name",
        "adset_name",
        "ad_name",
        "impressions",
        "clicks",
        "ctr",
        "cpc",
        "spend",
        "actions",
        "reach",
        "date_start",
        "date_stop",
    ])

    params = {
        "level": "ad",
        "fields": fields,
        "time_range": json.dumps({"since": date_start, "until": date_end}),
        "limit": 500,
    }

    print(f"  Trayendo métricas del {date_start} al {date_end}...")
    data = meta_get(f"act_{AD_ACCOUNT_ID}/insights", params)
    rows = data.get("data", [])

    # paginación
    while data.get("paging", {}).get("next"):
        next_url = data["paging"]["next"]
        with urllib.request.urlopen(next_url, timeout=30) as resp:
            data = json.loads(resp.read())
        rows.extend(data.get("data", []))
        time.sleep(0.3)

    print(f"  Total registros: {len(rows)}")
    return rows


def parse_conversions(actions):
    if not actions:
        return 0
    for action in actions:
        if action.get("action_type") in ("purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase"):
            return float(action.get("value", 0))
    return 0


def build_metrics_rows(raw_rows):
    rows = []
    for r in raw_rows:
        spend = float(r.get("spend", 0))
        conversions = parse_conversions(r.get("actions", []))
        costo_conv = round(spend / conversions, 2) if conversions > 0 else ""

        rows.append({
            "fecha_inicio": r.get("date_start", ""),
            "fecha_fin": r.get("date_stop", ""),
            "campaign_name": r.get("campaign_name", ""),
            "adset_name": r.get("adset_name", ""),
            "ad_name": r.get("ad_name", ""),
            "impresiones": r.get("impressions", 0),
            "clics": r.get("clicks", 0),
            "ctr": r.get("ctr", 0),
            "cpc": r.get("cpc", 0),
            "importe_gastado": spend,
            "conversiones": conversions,
            "costo_por_conversion": costo_conv,
            "alcance": r.get("reach", 0),
        })
    return rows


# ---------------------------------------------------------------------------
# Google Sheets
# ---------------------------------------------------------------------------

def write_metrics_to_sheets(rows):
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")

    if not sa_json or not spreadsheet_id:
        print("Skipping Sheets: faltan GOOGLE_SERVICE_ACCOUNT_JSON o SPREADSHEET_ID")
        return

    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)

    try:
        ws = sh.worksheet(SHEET_NAME_METRICS)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_NAME_METRICS, rows=5000, cols=len(FIELDNAMES_METRICS))

    data = [FIELDNAMES_METRICS] + [[row[f] for f in FIELDNAMES_METRICS] for row in rows]
    ws.clear()
    ws.update(data, value_input_option="RAW")
    print(f"Google Sheets actualizado: {len(rows)} filas en '{SHEET_NAME_METRICS}'")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not ACCESS_TOKEN:
        print("Error: falta META_ACCESS_TOKEN")
        return

    print("Trayendo métricas de Meta Ads...")
    raw = fetch_meta_metrics()

    print("Procesando datos...")
    rows = build_metrics_rows(raw)

    print("Subiendo a Google Sheets...")
    write_metrics_to_sheets(rows)

    print(f"\nListo: {len(rows)} registros de métricas.")


if __name__ == "__main__":
    main()
