"""
Scraper genérico de Meta Ads API.
Soporta niveles: account, campaign, adset, ad, product.
Configurable por cuenta, fechas y campos.
"""

import json
import os
import time
import urllib.request
import urllib.parse

API_VERSION = "v19.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"

CONVERSION_ACTIONS = [
    "view_content",
    "add_to_cart",
    "purchase",
    "omni_view_content",
    "omni_add_to_cart",
    "omni_purchase",
    "offsite_conversion.fb_pixel_view_content",
    "offsite_conversion.fb_pixel_add_to_cart",
    "offsite_conversion.fb_pixel_purchase",
]

DEFAULT_FIELDS = [
    "campaign_id",
    "campaign_name",
    "adset_id",
    "adset_name",
    "ad_id",
    "ad_name",
    "impressions",
    "reach",
    "clicks",
    "ctr",
    "spend",
    "cpc",
    "cpm",
    "actions",
    "action_values",
    "date_start",
    "date_stop",
]


def _get(endpoint, params, token):
    params["access_token"] = token
    url = f"{BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _fetch_insights(account_id, token, level, extra_fields=None,
                    date_from=None, date_to=None,
                    date_preset=None, breakdowns=None):
    """Fetch paginado de insights de Meta Ads."""
    fields = DEFAULT_FIELDS.copy()
    if extra_fields:
        fields.extend(extra_fields)

    params = {
        "level": level,
        "fields": ",".join(fields),
        "time_increment": 1,  # un registro por día
        "limit": 500,
    }

    if date_preset:
        params["time_range"] = json.dumps({"since": date_from, "until": date_to}) if date_from else date_preset
    elif date_from and date_to:
        params["time_range"] = json.dumps({"since": date_from, "until": date_to})

    if breakdowns:
        params["breakdowns"] = breakdowns

    all_rows = []
    data = _get(f"act_{account_id}/insights", params, token)
    all_rows.extend(data.get("data", []))

    while data.get("paging", {}).get("next"):
        next_url = data["paging"]["next"]
        req = urllib.request.Request(next_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        all_rows.extend(data.get("data", []))
        time.sleep(0.2)

    return all_rows


def _build_url_from_creative(creative):
    """Construye URL de destino desde el creative."""
    if not creative:
        return ""
    # Desde effective_object_story_id → permalink de post FB/IG
    story_id = creative.get("effective_object_story_id", "")
    if story_id and "_" in story_id:
        parts = story_id.split("_", 1)
        return f"https://www.facebook.com/{parts[0]}/posts/{parts[1]}"
    return ""


def fetch_ad_urls(account_id, token):
    """Fetch de URLs de destino y thumbnails por ad_id."""
    params = {
        "fields": "id,creative{effective_object_story_id,thumbnail_url}",
        "limit": 500,
        "access_token": token,
    }
    url = f"{BASE}/act_{account_id}/ads?{urllib.parse.urlencode(params)}"
    url_map = {}
    try:
        while url:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            for ad in data.get("data", []):
                creative = ad.get("creative") or {}
                url_map[ad["id"]] = {
                    "destination_url": _build_url_from_creative(creative),
                    "thumbnail_url":   creative.get("thumbnail_url", ""),
                }
            url = data.get("paging", {}).get("next")
            time.sleep(0.2)
        print(f"  URLs de destino: {len(url_map)} ads")
    except Exception as e:
        print(f"  [warning] No se pudieron obtener URLs: {e}")
    return url_map


def fetch_ads(account_id, token, date_from, date_to):
    """Fetch a nivel de ad con campaign + adset incluidos + URL de destino."""
    print(f"  Fetching ads...")
    rows = _fetch_insights(account_id, token, level="ad",
                           date_from=date_from, date_to=date_to)
    print(f"  ads: {len(rows)} registros")

    print(f"  Fetching URLs de destino...")
    url_map = fetch_ad_urls(account_id, token)
    for row in rows:
        ad_info = url_map.get(row.get("ad_id"), {})
        row["destination_url"] = ad_info.get("destination_url", "") if isinstance(ad_info, dict) else ""
        row["thumbnail_url"]   = ad_info.get("thumbnail_url", "")   if isinstance(ad_info, dict) else ""

    return rows


def fetch_products(account_id, token, date_from, date_to):
    """Fetch a nivel de ad con breakdown por product_id."""
    print(f"  Fetching product breakdown...")
    rows = _fetch_insights(account_id, token, level="ad",
                           date_from=date_from, date_to=date_to,
                           breakdowns="product_id")
    print(f"  products: {len(rows)} registros")
    return rows


def fetch_placements(account_id, token, date_from, date_to):
    """Fetch de métricas por publisher_platform y por age, con detalle de campaña/adset/ad."""
    print(f"  Fetching placements by platform...")
    by_platform = _fetch_insights(
        account_id, token, level="ad",
        date_from=date_from, date_to=date_to,
        breakdowns="publisher_platform",
    )
    for r in by_platform:
        r["breakdown_type"] = "platform"

    print(f"  Fetching placements by age...")
    by_age = _fetch_insights(
        account_id, token, level="ad",
        date_from=date_from, date_to=date_to,
        breakdowns="age",
    )
    for r in by_age:
        r["breakdown_type"] = "age"
        r["publisher_platform"] = ""

    rows = by_platform + by_age
    print(f"  placements: {len(rows)} registros")
    return rows


def fetch_all(account_id, token, date_from, date_to,
              levels=("ad", "product", "placement")):
    """Fetch de los niveles solicitados."""
    results = {}
    if "ad" in levels:
        results["ad"] = fetch_ads(account_id, token, date_from, date_to)
    if "product" in levels:
        results["product"] = fetch_products(account_id, token, date_from, date_to)
    if "placement" in levels:
        results["placement"] = fetch_placements(account_id, token, date_from, date_to)
    return results
