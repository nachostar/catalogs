"""
Veta automáticamente productos con mal CTR en los últimos N días.

Criterio: CTR < MAX_CTR% con al menos MIN_IMPRESSIONS impresiones.
Inserta en product_vetados solo los que no estén ya vetados.

Variables de entorno:
  GOOGLE_SERVICE_ACCOUNT_JSON
  MAX_CTR          (default: 6.0)
  MIN_IMPRESSIONS  (default: 50)
  DAYS             (default: 7)
  VETOED_BY        (default: auto)
  DRY_RUN          (default: false) — si es true, solo muestra sin insertar
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from outputs.bigquery import get_client

GCP_PROJECT     = os.environ.get("GCP_PROJECT", "quetri")
DATASET         = "meta_ads"
MAX_CTR         = float(os.environ.get("MAX_CTR", "6.0"))
MIN_IMPRESSIONS = int(os.environ.get("MIN_IMPRESSIONS", "50"))
DAYS            = int(os.environ.get("DAYS", "7"))
VETOED_BY       = os.environ.get("VETOED_BY", "auto")
DRY_RUN         = os.environ.get("DRY_RUN", "false").lower() == "true"


def main():
    client = get_client()
    metrics_table = f"`{GCP_PROJECT}.{DATASET}.daily_metrics`"
    vetados_table = f"`{GCP_PROJECT}.{DATASET}.product_vetados`"

    # Productos con mal CTR en los últimos DAYS días
    bad_ctr_query = f"""
        SELECT product_id
        FROM {metrics_table}
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {DAYS} DAY)
          AND product_id IS NOT NULL
        GROUP BY product_id
        HAVING SUM(impressions) >= {MIN_IMPRESSIONS}
           AND SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions), 0)) * 100 < {MAX_CTR}
        ORDER BY SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions), 0)) * 100
    """
    bad_ids = {r.product_id for r in client.query(bad_ctr_query).result()}
    print(f"Productos con CTR < {MAX_CTR}% (>={MIN_IMPRESSIONS} impresiones, últimos {DAYS} días): {len(bad_ids)}")

    if not bad_ids:
        print("No hay productos para vetar.")
        return

    # Filtrar los que ya están en product_vetados
    already_vetados = {
        r.family_id
        for r in client.query(f"SELECT family_id FROM {vetados_table}").result()
    }
    new_ids = bad_ids - already_vetados
    print(f"Ya vetados: {len(already_vetados & bad_ids)} | Nuevos a vetar: {len(new_ids)}")

    if not new_ids:
        print("Todos ya estaban vetados.")
        return

    for pid in sorted(new_ids):
        print(f"  → {pid}")

    if DRY_RUN:
        print("\nDRY_RUN=true — no se insertó nada.")
        return

    # Insertar los nuevos
    reason = f"CTR < {MAX_CTR}% en últimos {DAYS} días (auto)"
    values = ", ".join(
        f"('{pid}', '{reason}', CURRENT_DATE(), '{VETOED_BY}')"
        for pid in sorted(new_ids)
    )
    client.query(f"""
        INSERT INTO {vetados_table} (family_id, reason, vetoed_at, vetoed_by)
        VALUES {values}
    """).result()

    print(f"\n{len(new_ids)} productos vetados correctamente.")


if __name__ == "__main__":
    main()
