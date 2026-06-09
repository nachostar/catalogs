"""
Output: escribe datos en Google BigQuery.
Crea el dataset y tabla si no existen.
Usa WRITE_TRUNCATE por partición de fecha para evitar duplicados.
"""

import json
import os

from google.cloud import bigquery
from google.oauth2.service_account import Credentials

GCP_PROJECT = os.environ.get("GCP_PROJECT", "quetri")
DATASET     = "meta_ads"

SCHEMA_PLACEMENTS = [
    bigquery.SchemaField("date",            "DATE",    mode="REQUIRED"),
    bigquery.SchemaField("account_id",      "STRING",  mode="REQUIRED"),
    bigquery.SchemaField("platform",        "STRING"),
    bigquery.SchemaField("age",             "STRING"),
    bigquery.SchemaField("breakdown_type",  "STRING"),
    bigquery.SchemaField("impressions",     "INTEGER"),
    bigquery.SchemaField("reach",           "INTEGER"),
    bigquery.SchemaField("clicks",          "INTEGER"),
    bigquery.SchemaField("ctr",             "FLOAT"),
    bigquery.SchemaField("spend",           "FLOAT"),
    bigquery.SchemaField("cpc",             "FLOAT"),
    bigquery.SchemaField("view_content",    "FLOAT"),
    bigquery.SchemaField("add_to_cart",     "FLOAT"),
    bigquery.SchemaField("purchase",        "FLOAT"),
    bigquery.SchemaField("purchase_value",  "FLOAT"),
    bigquery.SchemaField("roas",            "FLOAT"),
]

SCHEMA_HERENEO_CATALOG = [
    bigquery.SchemaField("product_id",    "STRING",  mode="REQUIRED"),
    bigquery.SchemaField("family_id",     "STRING"),
    bigquery.SchemaField("title",         "STRING"),
    bigquery.SchemaField("brand",         "STRING"),
    bigquery.SchemaField("category",      "STRING"),
    bigquery.SchemaField("color",         "STRING"),
    bigquery.SchemaField("size",          "STRING"),
    bigquery.SchemaField("price",         "FLOAT"),
    bigquery.SchemaField("availability",  "STRING"),
    bigquery.SchemaField("condition",     "STRING"),
    bigquery.SchemaField("link",          "STRING"),
    bigquery.SchemaField("image_link",    "STRING"),
    bigquery.SchemaField("sku",           "STRING"),
    bigquery.SchemaField("updated_at",    "TIMESTAMP"),
]

SCHEMA_DAILY_METRICS = [
    bigquery.SchemaField("date",            "DATE",    mode="REQUIRED"),
    bigquery.SchemaField("account_id",      "STRING",  mode="REQUIRED"),
    bigquery.SchemaField("campaign_id",     "STRING"),
    bigquery.SchemaField("campaign_name",   "STRING"),
    bigquery.SchemaField("adset_id",        "STRING"),
    bigquery.SchemaField("adset_name",      "STRING"),
    bigquery.SchemaField("ad_id",           "STRING"),
    bigquery.SchemaField("ad_name",         "STRING"),
    bigquery.SchemaField("product_id",       "STRING"),
    bigquery.SchemaField("product_name",     "STRING"),
    bigquery.SchemaField("product_url",      "STRING"),
    bigquery.SchemaField("destination_url",  "STRING"),
    bigquery.SchemaField("thumbnail_url",    "STRING"),
    bigquery.SchemaField("impressions",     "INTEGER"),
    bigquery.SchemaField("reach",           "INTEGER"),
    bigquery.SchemaField("clicks",          "INTEGER"),
    bigquery.SchemaField("ctr",             "FLOAT"),
    bigquery.SchemaField("spend",           "FLOAT"),
    bigquery.SchemaField("cpc",             "FLOAT"),
    bigquery.SchemaField("cpm",             "FLOAT"),
    bigquery.SchemaField("view_content",    "FLOAT"),
    bigquery.SchemaField("add_to_cart",     "FLOAT"),
    bigquery.SchemaField("purchase",        "FLOAT"),
    bigquery.SchemaField("purchase_value",  "FLOAT"),
    bigquery.SchemaField("roas",            "FLOAT"),
]


def get_client():
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        creds = Credentials.from_service_account_info(json.loads(sa_json))
        return bigquery.Client(project=GCP_PROJECT, credentials=creds)
    return bigquery.Client(project=GCP_PROJECT)


def ensure_dataset(client):
    dataset_ref = bigquery.Dataset(f"{GCP_PROJECT}.{DATASET}")
    dataset_ref.location = "US"
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        client.create_dataset(dataset_ref, exists_ok=True)
        print(f"Dataset creado: {GCP_PROJECT}.{DATASET}")


def ensure_table(client, table_name, schema):
    table_id = f"{GCP_PROJECT}.{DATASET}.{table_name}"
    table = bigquery.Table(table_id, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="date",
    )
    client.create_table(table, exists_ok=True)
    return table_id


def write_placements(rows, table_name="placement_metrics", date_from=None, date_to=None):
    """Guarda métricas por placement en BigQuery."""
    if not rows:
        return

    import json as _json, io
    from collections import defaultdict

    client = get_client()
    ensure_dataset(client)
    table_id = ensure_table(client, table_name, SCHEMA_PLACEMENTS)

    by_date = defaultdict(list)
    for row in rows:
        by_date[row["date"]].append(row)

    total = 0
    for date_str, date_rows in sorted(by_date.items()):
        partition_id = date_str.replace("-", "")
        job_config = bigquery.LoadJobConfig(
            schema=SCHEMA_PLACEMENTS,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )
        ndjson = "\n".join(_json.dumps(r, default=str) for r in date_rows)
        job = client.load_table_from_file(
            io.BytesIO(ndjson.encode()),
            f"{table_id}${partition_id}",
            job_config=job_config,
        )
        job.result()
        total += len(date_rows)

    print(f"BigQuery: {total} filas en {table_id}")


def write_catalog(products, table_name="hereneo_catalog"):
    """
    Guarda el catálogo completo de productos en BigQuery.
    Reemplaza la tabla completa en cada carga (WRITE_TRUNCATE).
    """
    import json as _json
    import io
    from datetime import datetime, timezone

    if not products:
        print("No hay productos para insertar.")
        return

    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        print("Skipping BQ catalog: falta GOOGLE_SERVICE_ACCOUNT_JSON")
        return

    client = get_client()
    ensure_dataset(client)
    table_id = f"{GCP_PROJECT}.{DATASET}.{table_name}"
    table = bigquery.Table(table_id, schema=SCHEMA_HERENEO_CATALOG)
    client.create_table(table, exists_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for p in products:
        fam = p.get("family", {}) or {}
        brand = (fam.get("brand", {}) or {}).get("name", "")
        category = (fam.get("category", {}) or {}).get("name", "")
        family_id = str(fam.get("id", ""))
        price = p.get("price", 0)

        rows.append({
            "product_id":   str(p["id"]),
            "family_id":    family_id,
            "title":        f"{brand} - {fam.get('name', '')}".strip(" -"),
            "brand":        brand,
            "category":     category,
            "color":        (p.get("color", {}) or {}).get("name", ""),
            "size":         (p.get("size", {}) or {}).get("name", ""),
            "price":        float(price),
            "availability": p.get("commercial_status", ""),
            "condition":    (p.get("product_subfamily", {}) or {}).get("condition", "New"),
            "link":         f"https://www.hereneo.cl/products/{family_id}/{fam.get('slug', family_id)}",
            "image_link":   (p.get("images", [{}]) or [{}])[0].get("url", "") if p.get("images") else "",
            "sku":          family_id,
            "updated_at":   now,
        })

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA_HERENEO_CATALOG,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    ndjson = "\n".join(_json.dumps(r, default=str) for r in rows)
    job = client.load_table_from_file(
        io.BytesIO(ndjson.encode()),
        table_id,
        job_config=job_config,
    )
    job.result()
    print(f"BigQuery: {len(rows)} productos en {table_id}")


def enrich_product_urls(date_from=None, date_to=None, metrics_table="daily_metrics", catalog_table="hereneo_catalog"):
    """
    UPDATE daily_metrics.product_url usando JOIN con hereneo_catalog.
    Se ejecuta después de write_metrics.
    """
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        print("Skipping enrich: falta GOOGLE_SERVICE_ACCOUNT_JSON")
        return

    client = get_client()
    m = f"`{GCP_PROJECT}.{DATASET}.{metrics_table}`"
    c = f"`{GCP_PROJECT}.{DATASET}.{catalog_table}`"

    where = ""
    if date_from and date_to:
        where = f"AND m.date BETWEEN '{date_from}' AND '{date_to}'"

    query = f"""
        UPDATE {m} m
        SET m.product_url = c.link
        FROM {c} c
        WHERE m.product_id = c.family_id
          AND m.product_id IS NOT NULL
          {where}
    """
    try:
        client.query(query).result()
        print(f"product_url enriquecido desde {catalog_table}")
    except Exception as e:
        print(f"[warning] No se pudo enriquecer product_url: {e}")


def write_metrics(rows, table_name="daily_metrics", date_from=None, date_to=None):
    """
    Inserta filas en BigQuery usando load jobs por partición (no streaming).
    WRITE_TRUNCATE por partición evita duplicados sin necesitar DELETE.
    Funciona para carga diaria y masiva.
    """
    if not rows:
        print("No hay filas para insertar en BigQuery.")
        return

    import json as _json
    from collections import defaultdict

    client = get_client()
    ensure_dataset(client)
    table_id = ensure_table(client, table_name, SCHEMA_DAILY_METRICS)

    # Agrupar filas por fecha para escribir partición por partición
    by_date = defaultdict(list)
    for row in rows:
        by_date[row["date"]].append(row)

    total_inserted = 0
    for date_str, date_rows in sorted(by_date.items()):
        partition_id = date_str.replace("-", "")
        partition_table = f"{table_id}${partition_id}"

        job_config = bigquery.LoadJobConfig(
            schema=SCHEMA_DAILY_METRICS,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            schema_update_options=[
                bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
            ],
        )

        ndjson = "\n".join(_json.dumps(r, default=str) for r in date_rows)
        import io
        job = client.load_table_from_file(
            io.BytesIO(ndjson.encode()),
            partition_table,
            job_config=job_config,
        )
        job.result()
        total_inserted += len(date_rows)
        print(f"  {date_str}: {len(date_rows)} filas cargadas")

    print(f"BigQuery: {total_inserted} filas totales en {table_id}")
