"""Genera el icono de la app a partir del logo del Maker Club León.

Uso (con el Python del proyecto):

    .venv\\Scripts\\python.exe tools\\hacer_icono.py ruta\\al\\logo.(png|webp|jpg)

Del logo completo (isotipo + texto «MAKER CLUB LEÓN») recorta el isotipo, el engranaje de la
izquierda, y quita solo el fondo blanco exterior: el blanco de dentro (la llave y los números)
se conserva. Escribe:
  - assets/logo-maker.png  isotipo cuadrado de 512 px con fondo transparente
  - assets/bobber.ico      icono de Windows con varios tamaños (16 a 256 px)

Pillow y OpenCV ya vienen con las dependencias fijadas del proyecto; no hace falta instalar nada.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def isotype(path: Path) -> Image.Image:
    src = Image.open(path).convert("RGBA")
    flat = Image.new("RGBA", src.size, (255, 255, 255, 255))   # los huecos transparentes del logo
    flat.alpha_composite(src)                                   # (llave, números) pasan a ser blancos
    rgba = np.array(flat)
    h, w = rgba.shape[:2]
    left = rgba[:, : w // 2]                     # el isotipo está en la mitad izquierda
    ink = (left[..., :3].min(axis=2) < 235) & (left[..., 3] > 0)
    ys, xs = np.nonzero(ink)
    if not len(xs):
        raise SystemExit("No encuentro el isotipo en la mitad izquierda de la imagen")
    crop = left[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1].copy()

    # Fondo transparente: fuera de la silueta del engranaje. La silueta es el contorno exterior
    # de la tinta, con los huecos rellenos; así el blanco interior (llave, números) se conserva
    # aunque los números blancos lleguen a tocar el borde del engranaje.
    ch, cw = crop.shape[:2]
    ink_c = ((crop[..., :3].min(axis=2) < 235) & (crop[..., 3] > 0)).astype(np.uint8) * 255
    k = max(3, min(ch, cw) // 40) | 1           # cierra las muescas que dejan los números en el borde
    closed = cv2.morphologyEx(ink_c, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    silhouette = np.zeros((ch, cw), np.uint8)
    cv2.drawContours(silhouette, contours, -1, 255, thickness=cv2.FILLED)
    silhouette = cv2.GaussianBlur(silhouette, (3, 3), 0)    # borde suavizado
    crop[..., 3] = silhouette

    side = max(ch, cw)                           # cuadrado y centrado, con un pequeño margen
    margin = side // 20
    square = np.zeros((side + 2 * margin, side + 2 * margin, 4), np.uint8)
    y0, x0 = (square.shape[0] - ch) // 2, (square.shape[1] - cw) // 2
    square[y0: y0 + ch, x0: x0 + cw] = crop
    return Image.fromarray(square, "RGBA")


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    img = isotype(Path(sys.argv[1]))
    png = ROOT / "assets" / "logo-maker.png"
    ico = ROOT / "assets" / "bobber.ico"
    img.resize((512, 512), Image.LANCZOS).save(png)
    img.resize((256, 256), Image.LANCZOS).save(ico, sizes=ICO_SIZES)
    print(f"OK {png.relative_to(ROOT)} y {ico.relative_to(ROOT)} ({len(ICO_SIZES)} tamaños)")


if __name__ == "__main__":
    main()
