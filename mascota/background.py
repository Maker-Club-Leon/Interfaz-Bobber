"""Fondo de la escena ([background] de config.toml): degradado con halo o una imagen.

Se dibuja en una región propia detrás de la escena 3D, a pantalla completa y sin deformarse: si la
proporción de la ventana no coincide con la del fondo, se recorta por los lados o por arriba y abajo
(como «rellenar» en un fondo de escritorio).
"""
import numpy as np
from direct.showbase.DirectObject import DirectObject
from panda3d.core import (Camera, CardMaker, Filename, NodePath, OrthographicLens, SamplerState,
                          Texture, TextureStage)

GRADIENT_SIZE = (1920, 1080)


def parse_color(value):
    """«#rrggbb» o [r, g, b] (0-1) -> (r, g, b) en 0-1."""
    if isinstance(value, str):
        v = value.strip().lstrip("#")
        if len(v) != 6:
            raise ValueError(f"color no válido: {value!r} (usa «#rrggbb»)")
        return tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))
    r, g, b = (float(c) for c in value)
    return r, g, b


def gradient_pixels(top, bottom, glow, strength, size=GRADIENT_SIZE, center=(0.5, 0.42)):
    """Imagen (alto x ancho x 3, uint8, fila 0 = arriba): degradado vertical, halo suave detrás de
    la mascota (center = posición relativa, desde arriba a la izquierda) y bordes algo más oscuros."""
    w, h = size
    y = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
    top, bottom, glow = (np.array(c, dtype=np.float32) for c in (top, bottom, glow))
    img = top * (1 - y[..., None]) + bottom * y[..., None]          # degradado de arriba a abajo
    aspect = w / h
    d2 = ((x - center[0]) * aspect) ** 2 + (y - center[1]) ** 2
    halo = np.exp(-d2 / (2 * 0.33 ** 2))[..., None] * float(strength)
    img = img * (1 - halo) + glow * halo
    vignette = 1 - 0.35 * np.clip(((x - 0.5) * aspect) ** 2 + (y - 0.5) ** 2 - 0.25, 0, None)[..., None]
    img = img * vignette
    # Un poco de ruido para que el degradado no se vea a escalones en pantallas de 8 bits.
    noise = np.random.default_rng(0).uniform(-0.5, 0.5, img.shape[:2])[..., None] / 255
    return (np.clip(img + noise, 0, 1) * 255 + 0.5).astype(np.uint8)


def _gradient_texture(top, bottom, glow, strength):
    px = gradient_pixels(top, bottom, glow, strength)
    h, w = px.shape[:2]
    tex = Texture("fondo")
    tex.setup2dTexture(w, h, Texture.T_unsigned_byte, Texture.F_rgb)
    # Panda3D guarda las filas de abajo arriba y los canales en orden BGR.
    tex.setRamImage(np.ascontiguousarray(px[::-1, :, ::-1]).tobytes())
    return tex


class Background(DirectObject):
    """Fondo a pantalla completa detrás de la escena. warning = aviso para mostrar (o "")."""

    def __init__(self, base, cfg):
        super().__init__()
        self.base, self.warning = base, ""
        tex = None
        image = cfg.get("image", "")
        if image:
            from .config import resolve
            path = resolve(image)
            if path.exists():
                tex = base.loader.loadTexture(Filename.fromOsSpecific(str(path)), okMissing=True)
            if not tex:
                self.warning = f"No se pudo cargar el fondo {image}; se usa el degradado."
        if tex is None:
            tex = _gradient_texture(parse_color(cfg["top"]), parse_color(cfg["bottom"]),
                                    parse_color(cfg["glow"]), cfg["glow_strength"])
        tex.setWrapU(SamplerState.WM_clamp); tex.setWrapV(SamplerState.WM_clamp)
        tex.setMinfilter(SamplerState.FT_linear); tex.setMagfilter(SamplerState.FT_linear)
        self.aspect = (tex.getOrigFileXSize() or tex.getXSize()) / max(tex.getOrigFileYSize() or tex.getYSize(), 1)

        root = NodePath("fondo")
        lens = OrthographicLens(); lens.setFilmSize(2, 2); lens.setNearFar(-10, 10)
        cam = root.attachNewNode(Camera("fondo-cam", lens))
        cm = CardMaker("fondo"); cm.setFrameFullscreenQuad(); cm.setUvRange((0, 0), (1, 1))
        self.card = root.attachNewNode(cm.generate())
        self.card.setPos(0, 1, 0)
        self.card.setTexture(tex)
        self.card.setDepthTest(False); self.card.setDepthWrite(False); self.card.setLightOff(1)
        self.region = base.win.makeDisplayRegion()
        self.region.setSort(-20)                     # antes que la escena 3D (que va encima)
        self.region.setCamera(cam)
        self.root = root
        self.fit()
        self.accept("window-event", lambda _win: self.fit())

    def fit(self):
        """Recorta el fondo para que llene la ventana sin deformarse."""
        w, h = self.base.win.getXSize(), self.base.win.getYSize()
        if not w or not h:
            return
        win_aspect = w / h
        su, sv = 1.0, 1.0
        if win_aspect > self.aspect:                 # ventana más ancha: se recorta arriba y abajo
            sv = self.aspect / win_aspect
        else:                                        # ventana más alta: se recortan los lados
            su = win_aspect / self.aspect
        ts = TextureStage.getDefault()
        self.card.setTexScale(ts, su, sv)
        self.card.setTexOffset(ts, (1 - su) / 2, (1 - sv) / 2)

    def destroy(self):
        self.ignoreAll()
        if self.region:
            self.base.win.removeDisplayRegion(self.region)
            self.region = None
