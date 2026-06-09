"""
Parser de métricas de Meta Ads.
Normaliza conversiones y mapea al esquema de BigQuery con drill-down.
"""

ACTION_MAP = {
    "view_content":                              "view_content",
    "omni_view_content":                         "view_content",
    "offsite_conversion.fb_pixel_view_content":  "view_content",
    "add_to_cart":                               "add_to_cart",
    "omni_add_to_cart":                          "add_to_cart",
    "offsite_conversion.fb_pixel_add_to_cart":   "add_to_cart",
    "purchase":                                  "purchase",
    "omni_purchase":                             "purchase",
    "offsite_conversion.fb_pixel_purchase":      "purchase",
}


def extract_conversions(actions):
    result = {"view_content": 0.0, "add_to_cart": 0.0, "purchase": 0.0}
    for a in (actions or []):
        key = ACTION_MAP.get(a.get("action_type", ""))
        if key:
            result[key] += float(a.get("value", 0))
    return result


def extract_purchase_value(action_values):
    total = 0.0
    for a in (action_values or []):
        if ACTION_MAP.get(a.get("action_type", "")) == "purchase":
            total += float(a.get("value", 0))
    return total


def parse_product_field(raw_product_id):
    """
    Meta devuelve product_id como "123, Nombre del producto".
    Retorna (id, nombre) separados.
    """
    if not raw_product_id:
        return None, None
    parts = raw_product_id.split(",", 1)
    pid   = parts[0].strip()
    pname = parts[1].strip() if len(parts) > 1 else pid
    return pid, pname


def parse_row(raw, account_id, product_id=None):
    conversions    = extract_conversions(raw.get("actions"))
    purchase_value = extract_purchase_value(raw.get("action_values"))
    spend          = float(raw.get("spend", 0))
    roas           = round(purchase_value / spend, 4) if spend > 0 else 0.0

    pid, pname = parse_product_field(product_id)

    return {
        "date":           raw.get("date_start"),
        "account_id":     account_id,
        "campaign_id":    raw.get("campaign_id"),
        "campaign_name":  raw.get("campaign_name"),
        "adset_id":       raw.get("adset_id"),
        "adset_name":     raw.get("adset_name"),
        "ad_id":          raw.get("ad_id"),
        "ad_name":        raw.get("ad_name"),
        "product_id":      pid,
        "product_name":    pname,
        "product_url":     "",  # se enriquece después con el catálogo
        "destination_url": raw.get("destination_url", ""),
        "impressions":    int(raw.get("impressions", 0)),
        "reach":          int(raw.get("reach", 0)),
        "clicks":         int(raw.get("clicks", 0)),
        "ctr":            float(raw.get("ctr", 0)),
        "spend":          spend,
        "cpc":            float(raw.get("cpc", 0)),
        "cpm":            float(raw.get("cpm", 0)),
        "view_content":   conversions["view_content"],
        "add_to_cart":    conversions["add_to_cart"],
        "purchase":       conversions["purchase"],
        "purchase_value": purchase_value,
        "roas":           roas,
    }


def enrich_with_catalog(rows, catalog_url_map):
    """
    Enriquece filas de producto con la URL del catálogo.
    catalog_url_map: {family_id: product_url}
    """
    for row in rows:
        pid = row.get("product_id") or ""
        if pid and pid in catalog_url_map:
            row["product_url"] = catalog_url_map[pid]
    return rows


def parse_placements(raw_rows, account_id):
    rows = []
    for raw in raw_rows:
        conversions    = extract_conversions(raw.get("actions"))
        purchase_value = extract_purchase_value(raw.get("action_values"))
        spend          = float(raw.get("spend", 0))
        impressions    = int(raw.get("impressions", 0))
        clicks         = int(raw.get("clicks", 0))
        row = {
            "date":           raw.get("date_start"),
            "account_id":     account_id,
            "platform":       raw.get("publisher_platform", ""),
            "impressions":    impressions,
            "reach":          int(raw.get("reach", 0)),
            "clicks":         clicks,
            "ctr":            (clicks / impressions * 100) if impressions > 0 else 0,
            "spend":          spend,
            "cpc":            float(raw.get("cpc", 0)),
            "view_content":   conversions["view_content"],
            "add_to_cart":    conversions["add_to_cart"],
            "purchase":       conversions["purchase"],
            "purchase_value": purchase_value,
            "roas":           round(purchase_value / spend, 4) if spend > 0 else 0,
        }
        if row["date"]:
            rows.append(row)
    return rows


def parse_all(results_by_level, account_id):
    all_rows = []

    for level, raw_rows in results_by_level.items():
        for raw in raw_rows:
            product_id = raw.get("product_id") if level == "product" else None
            row = parse_row(raw, account_id, product_id)
            if row["date"]:
                all_rows.append(row)

    return all_rows
