"""
Parser de Hereneo — transforma productos crudos aplicando reglas de negocio.
Aquí se definen todas las reglas: qué mostrar, cómo formatear, qué excluir.
"""

import re

BASE_URL = "https://www.hereneo.cl"

# ---------------------------------------------------------------------------
# Campos de salida
# ---------------------------------------------------------------------------

FIELDNAMES_META = [
    "id", "title", "description", "availability", "condition",
    "price", "sale_price", "link", "image_link", "additional_image_link",
    "brand", "google_product_category", "product_type",
    "color", "size", "gender", "material", "sku", "custom_number_1",
]

FIELDNAMES_GMC = [
    "id", "title", "description", "link", "image_link", "additional_image_link",
    "availability", "price", "sale_price", "brand", "condition",
    "google_product_category", "product_type", "item_group_id",
    "color", "size", "gender", "age_group", "material",
    "identifier_exists", "mpn",
]

# ---------------------------------------------------------------------------
# Reglas: materiales
# ---------------------------------------------------------------------------

MATERIAL_REPLACEMENTS = [
    (r'\bald[oó]d[oó]n\b', 'Algodón'),
    (r'\balg[oó]d[oó]n\b', 'Algodón'),
    (r'\balgd[oó]n\b', 'Algodón'),
    (r'\bALGOD[OÓ]N\b', 'Algodón'),
    (r'\bAlgod[oó]n\b', 'Algodón'),
    (r'[Oo]rg[aá]nico', 'Orgánico'),
    (r'\bpoliester\b', 'Poliéster'),
    (r'\bPoliester\b', 'Poliéster'),
    (r'\bPOLIESTER\b', 'Poliéster'),
    (r'\bpoliamida\b', 'Poliamida'),
    (r'\belastano\b', 'Elastano'),
    (r'\bviscosa\b', 'Viscosa'),
    (r'\bacrilico\b', 'Acrílico'),
    (r'\bAcrilico\b', 'Acrílico'),
    (r'\blino\b', 'Lino'),
    (r'\blana\b', 'Lana'),
    (r'\bliocel\b', 'Liocel'),
    (r'\bpoliuretano\b', 'Poliuretano'),
]

GENDER_MAP = {
    "niño": "male", "hombre": "male",
    "niña": "female", "mujer": "female",
    "unisex": "unisex", "bebe": "unisex", "bebé": "unisex",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_product_url(prod):
    fam = prod.get("family", {}) or {}
    subfamily = prod.get("product_subfamily", {}) or {}
    condition = subfamily.get("condition", "New")
    family_id = fam.get("id", "")
    family_slug = fam.get("slug", str(family_id))
    query = ""
    if condition and condition != "New":
        query = f"?condition={condition}"
        if condition == "Used":
            query += f"&productId={prod['id']}"
    return f"{BASE_URL}/products/{family_id}/{family_slug}{query}"


def get_availability(prod):
    # Regla: usar dato de API (in_stock / out of stock)
    return "in stock" if prod.get("commercial_status") == "in_stock" else "out of stock"


def get_condition(prod):
    cond = (prod.get("product_subfamily", {}) or {}).get("condition", "New")
    return "used" if cond == "Used" else "new"


def build_title(prod):
    fam = prod.get("family", {}) or {}
    parts = [p for p in [
        (fam.get("brand", {}) or {}).get("name", ""),
        fam.get("name", ""),
        (prod.get("color", {}) or {}).get("name", ""),
        (prod.get("size", {}) or {}).get("name", ""),
    ] if p]
    return " - ".join(parts)[:150]


def get_image_url(prod):
    images = prod.get("images", [])
    return images[0].get("url", "") if images else ""


def get_additional_images(prod):
    images = prod.get("images", [])
    return ",".join(img.get("url", "") for img in images[1:5] if img.get("url"))


def get_description(prod):
    desc = (prod.get("family", {}) or {}).get("description", "") or ""
    return re.sub(r"<[^>]+>", "", desc)[:5000]


def normalize_material(text):
    if not text:
        return text
    text = re.sub(r'[\n\r]+', ' ', text)
    text = re.sub(r' {2,}', ' ', text).strip()
    for pattern, replacement in MATERIAL_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    if re.fullmatch(r'100\s*%\s*Algodón', text.strip()):
        return 'Algodón'
    return text


def get_age_group(prod):
    size = (prod.get("size", {}) or {}).get("name", "").lower()
    if any(s in size for s in ["rn", "recien", "0m", "nb", "newborn"]):
        return "newborn"
    if any(s in size for s in ["3m", "6m", "9m", "12m"]):
        return "infant"
    if any(s in size for s in ["18m", "24m", "2t", "3t", "4t", "2a", "3a", "4a"]):
        return "toddler"
    return "kids"


def get_gender_gmc(prod):
    fam = prod.get("family", {}) or {}
    gender_raw = (fam.get("gender", {}) or {}).get("name", "").lower().strip()
    return GENDER_MAP.get(gender_raw, "unisex")


# ---------------------------------------------------------------------------
# Builders principales
# ---------------------------------------------------------------------------

def build_meta_rows(products, badge_url_map=None):
    """Genera filas para el catálogo de Meta Ads."""
    rows = []
    seen_ids = set()

    for prod in products:
        prod_id = str(prod["id"])
        if prod_id in seen_ids:
            continue
        seen_ids.add(prod_id)

        title = build_title(prod)
        image_url = get_image_url(prod)
        if not title or not image_url:
            continue

        fam = prod.get("family", {}) or {}
        price = prod.get("price", 0)
        family_id = str(fam.get("id", ""))
        url = build_product_url(prod)
        final_image = (badge_url_map or {}).get(prod_id, image_url)

        rows.append({
            "id": family_id,
            "title": title,
            "description": get_description(prod),
            "availability": get_availability(prod),
            "condition": get_condition(prod),
            "price": f"{price} CLP",
            "sale_price": "",
            "link": url,
            "image_link": final_image,
            "additional_image_link": get_additional_images(prod),
            "brand": (fam.get("brand", {}) or {}).get("name", ""),
            "google_product_category": "",
            "product_type": (fam.get("category", {}) or {}).get("name", ""),
            "color": (prod.get("color", {}) or {}).get("name", ""),
            "size": (prod.get("size", {}) or {}).get("name", ""),
            "gender": (fam.get("gender", {}) or {}).get("name", ""),
            "material": normalize_material(fam.get("materials", "") or ""),
            "sku": family_id,
            "custom_number_1": (prod.get("sku", {}) or {}).get("value", prod.get("external_sku", "")),
        })

    return rows


def build_gmc_rows(products, badge_url_map=None):
    """Genera filas para el catálogo de Google Merchant Center."""
    rows = []
    seen_ids = set()
    seen_families = set()

    for prod in products:
        prod_id = str(prod["id"])
        if prod_id in seen_ids:
            continue
        seen_ids.add(prod_id)

        title = build_title(prod)
        image_url = get_image_url(prod)
        if not title or not image_url:
            continue

        fam = prod.get("family", {}) or {}
        price = prod.get("price", 0)
        family_id = str(fam.get("id", ""))
        url = build_product_url(prod)
        final_image = (badge_url_map or {}).get(prod_id, image_url)
        mpn = (prod.get("sku", {}) or {}).get("value", prod.get("external_sku", ""))

        gmc_id = family_id if family_id not in seen_families else f"{family_id}_{prod_id}"
        seen_families.add(family_id)

        rows.append({
            "id": gmc_id,
            "title": title,
            "description": get_description(prod),
            "link": url,
            "image_link": final_image,
            "additional_image_link": get_additional_images(prod),
            "availability": get_availability(prod),
            "price": f"{price} CLP",
            "sale_price": "",
            "brand": (fam.get("brand", {}) or {}).get("name", ""),
            "condition": get_condition(prod),
            "google_product_category": "",
            "product_type": (fam.get("category", {}) or {}).get("name", ""),
            "item_group_id": family_id,
            "color": (prod.get("color", {}) or {}).get("name", ""),
            "size": (prod.get("size", {}) or {}).get("name", ""),
            "gender": get_gender_gmc(prod),
            "age_group": get_age_group(prod),
            "material": normalize_material(fam.get("materials", "") or ""),
            "identifier_exists": "no",
            "mpn": mpn,
        })

    return rows
