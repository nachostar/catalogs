"""
Output: sube archivos a Google Cloud Storage.
"""

import csv
import json
import os
from pathlib import Path

from google.cloud import storage
from google.oauth2.service_account import Credentials

GCS_BUCKET = os.environ.get("GCS_BUCKET", "")


def upload_csv(rows, fieldnames, blob_name, local_path):
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json or not GCS_BUCKET:
        print(f"Skipping GCS '{blob_name}': faltan GCS_BUCKET o credenciales")
        return

    with open(local_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    creds = Credentials.from_service_account_info(json.loads(sa_json))
    client = storage.Client(credentials=creds,
                            project=json.loads(sa_json).get("project_id"))
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path), content_type="text/csv")

    url = f"https://storage.googleapis.com/{GCS_BUCKET}/{blob_name}"
    print(f"GCS: {blob_name} → {url}")
    return url
