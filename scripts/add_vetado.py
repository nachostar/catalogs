"""
Agrega un producto a product_vetados en BigQuery.
Uso: FAMILY_ID=189 REASON="desactivado" python scripts/add_vetado.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from outputs.bigquery import get_client

FAMILY_ID = os.environ.get("FAMILY_ID", "")
REASON    = os.environ.get("REASON", "desactivado manualmente")
VETOED_BY = os.environ.get("VETOED_BY", "ivargas")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "quetri")
DATASET     = "meta_ads"


def main():
    if not FAMILY_ID:
        print("Error: falta FAMILY_ID")
        sys.exit(1)

    client = get_client()
    table  = f"`{GCP_PROJECT}.{DATASET}.product_vetados`"

    # Verificar si ya existe
    check = list(client.query(
        f"SELECT family_id FROM {table} WHERE family_id = '{FAMILY_ID}'"
    ).result())
    if check:
        print(f"Producto {FAMILY_ID} ya está en product_vetados, no se duplica.")
        return

    client.query(f"""
        INSERT INTO {table} (family_id, reason, vetoed_at, vetoed_by)
        VALUES ('{FAMILY_ID}', '{REASON}', CURRENT_DATE(), '{VETOED_BY}')
    """).result()

    print(f"Producto {FAMILY_ID} agregado a product_vetados. Razón: {REASON}")


if __name__ == "__main__":
    main()
