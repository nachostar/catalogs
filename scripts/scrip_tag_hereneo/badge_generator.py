"""
Generador de imagenes de producto con badge "Revende por ...".

El tag se superpone en la esquina INFERIOR IZQUIERDA de la imagen, que se
muestra a tamano original (sin marco ni padding).

Requisitos del sistema:
  - wkhtmltoimage instalado (paquete: wkhtmltopdf)
  - Una fuente .ttf sans-serif (por defecto Liberation Sans, paquete fonts-liberation).

Uso rapido:
  from badge_generator import generar_png
  generar_png("ruta/producto.jpg", 26994, "salida.png", alt="Mi producto")
  generar_png("ruta/producto.jpg", "$26.994", "salida.png")
"""

import base64
import html as html_lib
import subprocess
import tempfile
import os


FUENTE_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FUENTE_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def _b64_archivo(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _formatear_precio(precio) -> str:
    """22794 -> '$22.794'. Si ya es string lo devuelve tal cual."""
    if isinstance(precio, (int, float)):
        return "$" + f"{int(precio):,}".replace(",", ".")
    return str(precio)


def construir_html(url_imagen: str, precio, alt: str = "Producto",
                   ancho_img: int = 280, incrustar_fuente: bool = True) -> str:
    """
    Devuelve el HTML del componente: imagen a tamano original con el badge
    superpuesto en la esquina inferior izquierda.

    url_imagen        : URL/ruta o data-uri de la imagen.
    precio            : numero (22794) o string ('$22.794').
    alt               : texto alternativo.
    ancho_img         : ancho de la imagen en px (mantiene su proporcion original).
                        Pone None para no forzar ancho y usar el tamano natural.
    incrustar_fuente  : True para meter la fuente via @font-face (necesario para
                        que wkhtmltoimage renderice bien la tipografia).
    """
    precio_fmt = html_lib.escape(_formatear_precio(precio))
    alt = html_lib.escape(alt)

    bloque_fuente = ""
    familia = "system-ui, -apple-system, Arial, sans-serif"
    if incrustar_fuente:
        reg = _b64_archivo(FUENTE_REGULAR)
        bold = _b64_archivo(FUENTE_BOLD)
        bloque_fuente = (
            "<style>"
            f"@font-face{{font-family:'BadgeSans';font-weight:400;"
            f"src:url(data:font/ttf;base64,{reg}) format('truetype');}}"
            f"@font-face{{font-family:'BadgeSans';font-weight:700;"
            f"src:url(data:font/ttf;base64,{bold}) format('truetype');}}"
            "</style>"
        )
        familia = "'BadgeSans', sans-serif"

    estilo_ancho = f"width: {ancho_img}px;" if ancho_img else ""

    return f"""{bloque_fuente}
<div style="position: relative; display: inline-block;">
  <img src="{url_imagen}" alt="{alt}" style="display: block; {estilo_ancho} border-radius: 8px;">
  <span style="position: absolute; bottom: 14px; left: 14px; background: rgba(255,255,255,0.72); color: #2f8f5b; font-family: {familia}; font-size: 13px; font-weight: 700; padding: 5px 12px; border-radius: 999px; border: 1px solid rgba(215,234,222,0.8); display: inline-flex; align-items: center; gap: 6px;">
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="#2f8f5b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M7 19H4.815a1.83 1.83 0 0 1-1.57-.881 1.785 1.785 0 0 1-.004-1.784L7.196 9.5"/>
      <path d="M11 19h8.203a1.83 1.83 0 0 0 1.556-.89 1.784 1.784 0 0 0 0-1.775l-1.226-2.12"/>
      <path d="m14 16-3 3 3 3"/>
      <path d="M8.293 13.596 7.196 9.5 3.1 10.598"/>
      <path d="m9.344 5.811 1.093-1.892A1.83 1.83 0 0 1 11.985 3a1.784 1.784 0 0 1 1.546.888l3.943 6.843"/>
      <path d="m13.378 9.633 4.096 1.098 1.097-4.096"/>
    </svg>
    Revende por {precio_fmt}
  </span>
</div>"""


def generar_png(ruta_imagen: str, precio, ruta_salida: str,
                alt: str = "Producto", ancho_img: int = 280,
                zoom: int = 3) -> str:
    """
    Renderiza el componente a PNG. La imagen va a tamano original (ancho_img)
    y el badge en la esquina inferior izquierda.
    """
    ext = os.path.splitext(ruta_imagen)[1].lstrip(".").lower() or "jpeg"
    if ext == "jpg":
        ext = "jpeg"
    data_uri = f"data:image/{ext};base64,{_b64_archivo(ruta_imagen)}"

    comp = construir_html(data_uri, precio, alt, ancho_img=ancho_img,
                          incrustar_fuente=True)
    page = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0;background:#ffffff}"
        ".wrap{display:inline-block}</style></head>"
        f"<body><div class='wrap'>{comp}</div></body></html>"
    )

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as tmp:
        tmp.write(page)
        ruta_html = tmp.name

    try:
        subprocess.run([
            "wkhtmltoimage", "--quality", "100",
            "--zoom", str(zoom), "--width", str(ancho_img or 320),
            "--enable-local-file-access",
            ruta_html, ruta_salida,
        ], check=True, capture_output=True)
    finally:
        os.unlink(ruta_html)

    return ruta_salida


def generar_lote(productos: list, carpeta_salida: str) -> list:
    """
    Genera un PNG por producto.
    productos: lista de dicts con 'imagen', 'precio' y opcional 'alt', 'nombre_archivo'.
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    rutas = []
    for i, p in enumerate(productos):
        nombre = p.get("nombre_archivo") or f"producto_{i+1}.png"
        salida = os.path.join(carpeta_salida, nombre)
        generar_png(p["imagen"], p["precio"], salida, alt=p.get("alt", "Producto"))
        rutas.append(salida)
    return rutas


if __name__ == "__main__":
    generar_png(
        "/mnt/user-data/uploads/1222_77.jpg",
        "$26.994",
        "/mnt/user-data/outputs/producto_con_badge.png",
        alt="Saco de dormir ergoPouch Jersey 2.5 tog - Willow",
    )
    print("Listo: producto_con_badge.png")
