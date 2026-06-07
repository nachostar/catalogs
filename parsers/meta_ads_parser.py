"""
Parser de métricas de Meta Ads.
Normaliza conversiones y calcula métricas derivadas (ROAS, etc.)
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
    """Suma conversiones por tipo desde la lista de actions de Meta."""
    result = {"view_content": 0.0, "add_to_cart": 0.0, "purchase": 0.0}
    for a in (actions or []):
        key = ACTION_MAP.get(a.get("action_type", ""))
        if key:
            result[key] += float(a.get("value", 0))
    return result


def extract_purchase_value(action_values):
    """Suma el valor de compras desde action_values."""
    total = 0.0
    for a in (action_values or []):
        if ACTION_MAP.get(a.get("action_type", "")) == "purchase":
            total += float(a.get("value", 0))
    return total


def parse_row(raw, level, account_id, entity_id=None, entity_name=None):
    """Transforma una fila cruda de Meta API al esquema de BigQuery."""
    conversions = extract_conversions(raw.get("actions"))
    purchase_value = extract_purchase_value(raw.get("action_values"))
    spend = float(raw.get("spend", 0))
    roas = round(purchase_value / spend, 4) if spend > 0 else 0.0

    return {
        "date":           raw.get("date_start"),
        "account_id":     account_id,
        "level":          level,
        "entity_id":      entity_id or raw.get(f"{level}_id", ""),
        "entity_name":    entity_name or raw.get(f"{level}_name", raw.get("ad_name", "")),
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


def parse_all(results_by_level, account_id):
    """
    Parsea todos los niveles y retorna lista de filas para BigQuery.
    results_by_level: dict {level: [raw_rows]}
    """
    all_rows = []

    for level, raw_rows in results_by_level.items():
        for raw in raw_rows:
            if level == "campaign":
                eid   = raw.get("campaign_id")
                ename = raw.get("campaign_name")
            elif level == "adset":
                eid   = raw.get("adset_id")
                ename = raw.get("adset_name")
            elif level == "ad":
                eid   = raw.get("ad_id")
                ename = raw.get("ad_name")
            elif level == "product":
                eid   = raw.get("product_id", "")
                ename = eid  # product_id ya incluye el nombre en Meta
            else:
                eid   = None
                ename = None

            row = parse_row(raw, level, account_id, eid, ename)
            if row["date"]:
                all_rows.append(row)

    return all_rows
