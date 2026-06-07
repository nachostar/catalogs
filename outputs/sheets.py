"""
Output: escribe filas a Google Sheets.
"""

import json
import os

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def write(rows, sheet_name, fieldnames):
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")

    if not sa_json or not spreadsheet_id:
        print(f"Skipping Sheets '{sheet_name}': faltan credenciales")
        return

    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)

    try:
        ws = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=2000, cols=len(fieldnames))

    data = [fieldnames] + [[row[f] for f in fieldnames] for row in rows]
    ws.clear()
    ws.update(data, value_input_option="RAW")
    print(f"Google Sheets: {len(rows)} filas en '{sheet_name}'")
