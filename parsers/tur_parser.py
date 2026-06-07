"""
Parser de tur.com — transforma tours/experiencias al formato de catálogos.
"""

BASE_URL = "https://www.tur.com"
BASE_MEDIA = "https://d6myp1633h7qr.cloudfront.net/products/"

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


def get_image_url(prod):
    thumbnail = prod.get("thumbnail", "")
    ext = prod.get("mediaExtension", ".webp")
    base = prod.get("baseMedia", BASE_MEDIA)
    if thumbnail:
        return f"{base}{thumbnail}{ext}"
    media = prod.get("media", [])
    if media:
        return f"{base}{media[0]}{ext}"
    return ""


def get_additional_images(prod):
    media = prod.get("media", [])
    ext = prod.get("mediaExtension", ".webp")
    base = prod.get("baseMedia", BASE_MEDIA)
    urls = [f"{base}{m}{ext}" for m in media[1:5] if m]
    return ",".join(urls)


def get_product_url(prod):
    slug = prod.get("slug", "")
    dest = next((d for d in prod.get("destinations", []) if d.get("isDefault")), None)
    dest_slug = dest.get("slug", "") if dest else ""
    if dest_slug and slug:
        return f"{BASE_URL}/es/{dest_slug}/{slug}"
    return f"{BASE_URL}/es/search"


def get_destination(prod):
    dest = next((d for d in prod.get("destinations", []) if d.get("family") == "city"), None)
    if not dest:
        dest = next((d for d in prod.get("destinations", []) if d.get("isDefault")), None)
    return dest.get("name", "") if dest else ""


def get_country(prod):
    dest = next((d for d in prod.get("destinations", []) if d.get("family") == "country"), None)
    return dest.get("name", "") if dest else ""


def get_price(prod):
    price = prod.get("price", {}) or {}
    return price.get("retail") or price.get("original") or 0


def get_availability(prod):
    return "in stock" if prod.get("publish", False) else "in stock"


def get_description(prod):
    return (
        prod.get("shortDescription")
        or prod.get("longDescription")
        or prod.get("internalName")
        or ""
    )[:5000]


def build_meta_rows(products, badge_url_map=None):
    rows = []
    seen_ids = set()

    for prod in products:
        prod_id = str(prod.get("id", ""))
        if prod_id in seen_ids or not prod_id:
            continue
        seen_ids.add(prod_id)

        title = prod.get("name") or prod.get("internalName", "")
        image_url = get_image_url(prod)
        if not title or not image_url:
            continue

        price = get_price(prod)
        internal_id = str(prod.get("internalId", prod_id))
        url = get_product_url(prod)
        final_image = (badge_url_map or {}).get(prod_id, image_url)

        rows.append({
            "id": internal_id,
            "title": title,
            "description": get_description(prod),
            "availability": get_availability(prod),
            "condition": "new",
            "price": f"{price} CLP",
            "sale_price": "",
            "link": url,
            "image_link": final_image,
            "additional_image_link": get_additional_images(prod),
            "brand": "Tur",
            "google_product_category": "",
            "product_type": get_destination(prod),
            "color": "",
            "size": "",
            "gender": "",
            "material": "",
            "sku": internal_id,
            "custom_number_1": prod_id,
        })

    return rows


def build_gmc_rows(products, badge_url_map=None):
    rows = []
    seen_ids = set()

    for prod in products:
        prod_id = str(prod.get("id", ""))
        if prod_id in seen_ids or not prod_id:
            continue
        seen_ids.add(prod_id)

        title = prod.get("name") or prod.get("internalName", "")
        image_url = get_image_url(prod)
        if not title or not image_url:
            continue

        price = get_price(prod)
        internal_id = str(prod.get("internalId", prod_id))
        url = get_product_url(prod)
        final_image = (badge_url_map or {}).get(prod_id, image_url)

        rows.append({
            "id": internal_id,
            "title": title,
            "description": get_description(prod),
            "link": url,
            "image_link": final_image,
            "additional_image_link": get_additional_images(prod),
            "availability": get_availability(prod),
            "price": f"{price} CLP",
            "sale_price": "",
            "brand": "Tur",
            "condition": "new",
            "google_product_category": "",
            "product_type": get_destination(prod),
            "item_group_id": internal_id,
            "color": "",
            "size": "",
            "gender": "",
            "age_group": "adult",
            "material": "",
            "identifier_exists": "no",
            "mpn": prod_id,
        })

    return rows
