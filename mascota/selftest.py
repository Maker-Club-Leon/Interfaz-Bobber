"""Prueba breve: lógica, modelo, ventana 3D y cámara. Ejecuta: run.bat --selftest"""
import sys

from .behavior import GreetingLogic
from .config import load_config, resolve
from .modelio import inspect_glb

results = []


def step(name):
    def deco(fn):
        try:
            msg = fn() or ""
            results.append(True); print(f"[OK]    {name} {msg}")
        except Exception as e:
            results.append(False); print(f"[FALLO] {name}: {e}")
    return deco


def main():
    cfg = load_config()
    path = resolve(cfg["model"]["path"])

    @step("Versión de MediaPipe fijada (sin telemetría)")
    def _():
        import re
        from importlib.metadata import version
        req = resolve("requirements.txt").read_text(encoding="utf-8")
        m = re.search(r"^mediapipe==(\S+)", req, re.MULTILINE)
        assert m, "requirements.txt no fija la versión de mediapipe"
        installed = version("mediapipe")
        assert installed == m.group(1), (
            f"instalada {installed}, requirements.txt pide {m.group(1)}. Actualiza con: "
            ".venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return installed

    @step("Python 3.12 y versiones de requirements.txt")
    def _():
        import re
        from importlib.metadata import PackageNotFoundError, version
        assert sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32, (
            f"Python {sys.version.split()[0]}; el proyecto necesita Python 3.12 de 64 bits. "
            "Borra .venv e instala Python 3.12 antes de ejecutar run.bat")
        req = resolve("requirements.txt").read_text(encoding="utf-8")
        pins = re.findall(r"^([A-Za-z0-9_.-]+)==(\S+)", req, re.MULTILINE)
        wrong = []
        for name, want in pins:
            try:
                have = version(name)
            except PackageNotFoundError:
                have = "no instalado"
            if have != want:
                wrong.append(f"{name} {have} (pide {want})")
        assert not wrong, ("; ".join(wrong) + ". Actualiza con: "
                           ".venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return f"{len(pins)} paquetes coinciden"

    @step("Lógica de saludo")
    def _():
        g = GreetingLogic(1.0, 3.0)
        seq = [(True, 0.0), (True, 1.1), (True, 2.0), (False, 3.0), (False, 6.1), (True, 7.0), (True, 8.1)]
        assert [g.update(p, t) for p, t in seq] == [None, "greet", None, None, "reset", None, "greet"]

    @step("Lógica de gestos (confirmación, espera, rearme)")
    def _():
        from .behavior import GestureLogic
        g = GestureLogic(0.6, 3.0, 0.7)
        seq = [("palma_abierta", 0.0), ("palma_abierta", 0.7), ("palma_abierta", 2.0), (None, 2.1), (None, 2.9),
               ("palma_abierta", 3.0), ("palma_abierta", 3.8), ("puno_cerrado", 4.0), ("puno_cerrado", 4.7),
               ("puno_cerrado", 7.0), (None, 7.1), (None, 7.9), ("puno_cerrado", 8.0), ("puno_cerrado", 10.5)]
        out = [g.update(k, t) for k, t in seq]
        pa, pu = "palma_abierta", "puno_cerrado"
        # 0.7 actúa; 2.0 mano levantada sin repetir; 3.8 retirada+espera cumplida -> otra vez;
        # puño mantenido: espera a que acabe el cooldown (7.0); 10.5 tras retirar la mano.
        assert out == [None, pa, None, None, None, None, pa, None, None, pu, None, None, None, pu], out

    @step("Prioridad de acciones (manual > gesto > presencia)")
    def _():
        from .behavior import ActionArbiter
        a = ActionArbiter()
        assert a.request("saludo", "presence", 0, 2) and not a.request("saludo", "presence", 1, 2)
        assert a.request("caminar", "gesture", 1, 4) and not a.request("saludo", "gesture", 2, 2)
        assert not a.request("saludo", "presence", 3, 2) and a.request("saludo", "manual", 3, 2)
        assert a.request("saludo", "presence", 6, 2)

    @step("Modelo glTF/GLB")
    def _():
        i = inspect_glb(path)
        print(f"        {i['size_mb']:.1f} MB, {i['joints']} huesos, materiales: "
              f"{[(m[0], m[1]) for m in i['materials']]}")
        print(f"        texturas: {i['images']}  |  animaciones: {i['animations'] or 'NINGUNA'}")
        if not i["animations"]:
            return "(sin animaciones: se usará movimiento provisional)"

    @step("Ventana 3D y carga del modelo (sin mostrar ventana)")
    def _():
        from panda3d.core import loadPrcFileData
        loadPrcFileData("", "window-type offscreen\naudio-library-name null")
        from direct.showbase.ShowBase import ShowBase
        from .modelio import load_model
        base = None
        try:
            base = ShowBase()
            node, anims = load_model(base.loader, path)
            base.graphicsEngine.renderFrame()
            mn, mx = node.getTightBounds()
            return f"tamaño {mx - mn}, clips: {anims}"
        finally:
            if base is not None:
                base.destroy()

    @step("Cámara y detección")
    def _():
        from .detector import PoseAnalyzer, open_camera
        cam, det = cfg["camera"], cfg["detection"]
        cap = open_camera(cam["index"], cam["width"], cam["height"])
        try:
            ok, frame = cap.read()
        finally:
            cap.release()
        assert ok, "la cámara abrió pero no entrega imagen"
        an = PoseAnalyzer(resolve(det["pose_model"]), det["min_visibility"], det["min_shoulder_width"])
        try:
            info = an.analyze(frame)
        finally:
            an.close()
        extra = ""
        g = cfg["gestures"]
        if g["enabled"] and resolve(g["model"]).exists():
            from .detector import GestureAnalyzer
            ga = GestureAnalyzer(resolve(g["model"]), g["min_confidence"])
            try:
                h = ga.analyze(frame)
            finally:
                ga.close()
            extra = f", mano: {h['hand']}, gesto: {h['label']}"
        return f"imagen {frame.shape[1]}x{frame.shape[0]}, persona detectada: {info['present']}{extra}"

    @step("Reconocedor de gestos (carga del modelo)")
    def _():
        g = cfg["gestures"]
        if not g["enabled"]:
            return "(desactivado en config.toml)"
        import numpy as np
        from .detector import GestureAnalyzer
        ga = GestureAnalyzer(resolve(g["model"]), g["min_confidence"])
        try:
            ga.analyze(np.zeros((480, 640, 3), np.uint8))
        finally:
            ga.close()

    print("\nResultado:", "TODO CORRECTO" if all(results) else "hay fallos (ver arriba y README)")
    sys.exit(0 if all(results) else 1)
