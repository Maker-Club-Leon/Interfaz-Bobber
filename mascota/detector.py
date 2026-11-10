"""Detección local de presencia: OpenCV + MediaPipe Pose Landmarker (API Tasks).
Los fotogramas solo viven en memoria; nada se guarda ni se envía. La única
conexión a internet es la descarga única del modelo de pose si falta."""
import os
import threading
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

POSE_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
            "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task")
NOSE, L_SHOULDER, R_SHOULDER = 0, 11, 12
GESTURE_URL = ("https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
               "gesture_recognizer/float16/latest/gesture_recognizer.task")
# etiqueta de MediaPipe -> (clave en config.toml, nombre para mostrar)
GESTURE_LABELS = {
    "Open_Palm": ("palma_abierta", "palma abierta"), "Closed_Fist": ("puno_cerrado", "puño cerrado"),
    "Pointing_Up": ("dedo_arriba", "dedo hacia arriba"), "Thumb_Up": ("pulgar_arriba", "pulgar arriba"),
    "Thumb_Down": ("pulgar_abajo", "pulgar abajo"), "Victory": ("victoria", "victoria (V)"),
    "ILoveYou": ("te_quiero", "te quiero"),
}


def download_models(cfg):
    """Descarga (solo si faltan) los modelos de MediaPipe. Es el único paso que necesita internet."""
    from .config import resolve
    for name, url, rel in [("poses", POSE_URL, cfg["detection"]["pose_model"]),
                           ("gestos", GESTURE_URL, cfg["gestures"]["model"])]:
        path = resolve(rel)
        if path.exists():
            print(f"[OK] modelo de {name} ya presente: {path}")
            continue
        try:
            os.makedirs(path.parent, exist_ok=True)
            urllib.request.urlretrieve(url, path)
            print(f"[OK] modelo de {name} descargado: {path}")
        except Exception as e:
            print(f"[FALLO] modelo de {name}: {e}\n        Descárgalo a mano desde {url}\n        y guárdalo en {path}")


def ensure_pose_model(path) -> str:
    if not os.path.exists(path):
        print("Descargando modelo de pose (una sola vez)...")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(POSE_URL, path)
    return str(path)


def open_camera(index: int, width: int, height: int):
    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
    cap = cv2.VideoCapture(index, backend)
    try:
        if not cap.isOpened():
            raise RuntimeError(f"no se pudo abrir la cámara {index} (ocupada, desconectada o sin permiso)")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        return cap
    except Exception:
        cap.release()
        raise


class PoseAnalyzer:
    """Convierte un fotograma BGR en {present, shoulder_width, visibility, points}."""

    def __init__(self, model_path, min_visibility, min_shoulder_width):
        opts = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=ensure_pose_model(model_path)),
            running_mode=vision.RunningMode.VIDEO, num_poses=1)
        self.landmarker = vision.PoseLandmarker.create_from_options(opts)
        self.min_vis, self.min_sw = min_visibility, min_shoulder_width
        self._last_ts = -1

    def analyze(self, bgr, ts_ms=None) -> dict:
        ts = int(ts_ms if ts_ms is not None else time.monotonic() * 1000)
        ts = max(ts, self._last_ts + 1)       # MediaPipe exige marcas de tiempo crecientes
        self._last_ts = ts
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        res = self.landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
        out = {"present": False, "shoulder_width": 0.0, "visibility": 0.0, "points": []}
        if res.pose_landmarks:
            lm = res.pose_landmarks[0]
            key = [lm[NOSE], lm[L_SHOULDER], lm[R_SHOULDER]]
            out["visibility"] = min((p.visibility or 0.0) for p in key)
            out["shoulder_width"] = abs(lm[L_SHOULDER].x - lm[R_SHOULDER].x)
            out["points"] = [(p.x, p.y) for p in key]
            out["present"] = out["visibility"] >= self.min_vis and out["shoulder_width"] >= self.min_sw
        return out

    def close(self):
        self.landmarker.close()


class GestureAnalyzer:
    """MediaPipe Gesture Recognizer (una mano). Devuelve {hand, label, score, points}.
    `label` es la etiqueta de MediaPipe solo si supera min_confidence y es un gesto conocido."""

    def __init__(self, model_path, min_confidence):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"falta el modelo de gestos en {model_path} (ejecuta run.bat --descargar-modelos)")
        c = min_confidence
        opts = vision.GestureRecognizerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO, num_hands=1,
            min_hand_detection_confidence=c, min_hand_presence_confidence=c, min_tracking_confidence=c)
        self.rec = vision.GestureRecognizer.create_from_options(opts)
        self.min_conf, self._last_ts = min_confidence, -1

    def analyze(self, bgr, ts_ms=None) -> dict:
        ts = max(int(ts_ms if ts_ms is not None else time.monotonic() * 1000), self._last_ts + 1)
        self._last_ts = ts
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        res = self.rec.recognize_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
        out = {"hand": False, "label": None, "score": 0.0, "points": []}
        if res.hand_landmarks:
            out["hand"], out["points"] = True, [(p.x, p.y) for p in res.hand_landmarks[0]]
            if res.gestures and res.gestures[0]:
                cat = res.gestures[0][0]
                out["score"] = cat.score
                if cat.score >= self.min_conf and cat.category_name in GESTURE_LABELS:
                    out["label"] = cat.category_name
        return out

    def close(self):
        self.rec.close()


def draw_overlay(bgr, info, hand=None):
    """Devuelve una copia en espejo con los puntos detectados (para calibrar)."""
    img = cv2.flip(bgr, 1)
    h, w = img.shape[:2]
    color = (0, 200, 0) if info["present"] else (0, 0, 220)
    for x, y in info["points"]:
        cv2.circle(img, (int((1 - x) * w), int(y * h)), 6, color, -1)
    if hand and hand["hand"]:                      # mano en cian; el texto va en ASCII (OpenCV no admite tildes)
        for x, y in hand["points"]:
            cv2.circle(img, (int((1 - x) * w), int(y * h)), 3, (255, 200, 0), -1)
        txt = f"{hand['label'] or 'sin gesto'} {hand['score']:.2f}"
        cv2.putText(img, txt, (8, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)
    return img


class PresenceDetector(threading.Thread):
    """Hilo que lee la cámara y mantiene `present` actualizado."""

    def __init__(self, cfg):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.status, self.error = "starting", ""
        self.present, self.shoulder_width, self.visibility, self.fps = False, 0.0, 0.0, 0.0
        self.preview_enabled = False
        # Estado de manos/gestos (lo escribe este hilo, lo lee la interfaz)
        self.gesture_status, self.gesture_error = "off", ""   # off | ready | error
        self.hand_present, self.gesture, self.gesture_label, self.gesture_score = False, None, None, 0.0
        self._preview = None
        self._halt = threading.Event()

    def take_preview(self):
        p, self._preview = self._preview, None
        return p

    def stop(self):
        self._halt.set()

    def run(self):
        cam, det = self.cfg["camera"], self.cfg["detection"]
        analyzer = cap = ga = None
        try:
            from .config import resolve
            analyzer = PoseAnalyzer(resolve(det["pose_model"]), det["min_visibility"], det["min_shoulder_width"])
            cap = open_camera(cam["index"], cam["width"], cam["height"])
            gcfg = self.cfg["gestures"]      # si fallan los gestos, sigue la detección de personas
            if gcfg["enabled"]:
                try:
                    ga = GestureAnalyzer(resolve(gcfg["model"]), gcfg["min_confidence"])
                    self.gesture_status = "ready"
                except Exception as e:
                    self.gesture_status, self.gesture_error = "error", str(e)
            self.status, fails, last = "running", 0, 0.0
            while not self._halt.is_set():
                time.sleep(0.01)
                now = time.monotonic()
                if now - last < det["interval_ms"] / 1000:
                    continue
                ok, frame = cap.read()
                if not ok:
                    fails += 1
                    if fails > 30:
                        self.status, self.error = "error", "se perdió la señal de la cámara"
                        return
                    continue
                fails = 0
                info = analyzer.analyze(frame)
                hand = None
                if ga:                              # mismo fotograma y misma cámara que la detección de personas
                    try:
                        hand = ga.analyze(frame)
                        self.hand_present, self.gesture_label, self.gesture_score = hand["hand"], hand["label"], hand["score"]
                        self.gesture = GESTURE_LABELS[hand["label"]][0] if hand["label"] else None
                    except Exception as e:
                        try:
                            ga.close()
                        except Exception:
                            pass
                        ga = None
                        self.gesture_status, self.gesture_error = "error", f"fallo al analizar gestos: {e}"
                        self.hand_present, self.gesture = False, None
                self.fps = 1.0 / max(now - last, 1e-3) if last else 0.0
                last = now
                self.present, self.shoulder_width, self.visibility = (
                    info["present"], info["shoulder_width"], info["visibility"])
                if self.preview_enabled:
                    small = cv2.resize(draw_overlay(frame, info, hand), (320, 240))
                    self._preview = (320, 240, cv2.flip(small, 0).tobytes())  # Panda: origen abajo
        except Exception as e:
            self.status, self.error = "error", str(e)
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            if analyzer is not None:
                try:
                    analyzer.close()
                except Exception:
                    pass
            if ga:
                try:
                    ga.close()
                except Exception:
                    pass
            if self.status != "error":
                self.status = "stopped"
