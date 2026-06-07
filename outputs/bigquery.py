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

SCHEMA_DAILY_METRICS = [
    bigquery.SchemaField("date",           "DATE",    mode="REQUIRED"),
    bigquery.SchemaField("account_id",     "STRING",  mode="REQUIRED"),
    bigquery.SchemaField("level",          "STRING",  mode="REQUIRED"),
    bigquery.SchemaField("entity_id",      "STRING"),
    bigquery.SchemaField("entity_name",    "STRING"),
    bigquery.SchemaField("impressions",    "INTEGER"),
    bigquery.SchemaField("reach",          "INTEGER"),
    bigquery.SchemaField("clicks",         "INTEGER"),
    bigquery.SchemaField("ctr",            "FLOAT"),
    bigquery.SchemaField("spend",          "FLOAT"),
    bigquery.SchemaField("cpc",            "FLOAT"),
    bigquery.SchemaField("cpm",            "FLOAT"),
    bigquery.SchemaField("view_content",   "FLOAT"),
    bigquery.SchemaField("add_to_cart",    "FLOAT"),
    bigquery.SchemaField("purchase",       "FLOAT"),
    bigquery.SchemaField("purchase_value", "FLOAT"),
    bigquery.SchemaField("roas",           "FLOAT"),
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


def write_metrics(rows, table_name="daily_metrics", date_str=None):
    """
    Inserta filas en BigQuery.
    Si date_str se especifica, borra esa partición antes de insertar (evita duplicados).
    """
    if not rows:
        print("No hay filas para insertar en BigQuery.")
        return

    client = get_client()
    ensure_dataset(client)
    table_id = ensure_table(client, table_name, SCHEMA_DAILY_METRICS)

    # Borrar la partición del día para evitar duplicados
    if date_str:
        partition_id = date_str.replace("-", "")
        delete_query = f"DELETE FROM `{table_id}` WHERE date = '{date_str}'"
        client.query(delete_query).result()
        print(f"Partición {date_str} limpiada.")

    errors = client.insert_rows_json(table_id, rows)
    if errors:
        print(f"Errores al insertar: {errors[:3]}")
    else:
        print(f"BigQuery: {len(rows)} filas insertadas en {table_id}")
