"""Calibración sin 3D: ventana de OpenCV con lo que detecta la cámara (solo en pantalla)."""
import cv2

from .config import load_config, resolve
from .detector import GestureAnalyzer, PoseAnalyzer, draw_overlay, open_camera


def main():
    cfg = load_config(); cam, det = cfg["camera"], cfg["detection"]
    cap = open_camera(cam["index"], cam["width"], cam["height"])
    an = ga = None
    try:
        an = PoseAnalyzer(resolve(det["pose_model"]), det["min_visibility"], det["min_shoulder_width"])
        g = cfg["gestures"]
        if g["enabled"]:
            try:
                ga = GestureAnalyzer(resolve(g["model"]), g["min_confidence"])
            except Exception as e:
                print("Gestos desactivados:", e)
        print("Calibración: pulsa Q o Esc para salir.")
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            info = an.analyze(frame)
            hand = ga.analyze(frame) if ga else None
            img = draw_overlay(frame, info, hand)
            txt = (f"{'PERSONA' if info['present'] else 'nadie'} | hombros {info['shoulder_width']:.2f} "
                   f"(min {det['min_shoulder_width']}) | visib. {info['visibility']:.2f} (min {det['min_visibility']})")
            cv2.putText(img, txt, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.imshow("Calibracion", img)
            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                break
    finally:
        cap.release()
        if an is not None:
            an.close()
        if ga is not None:
            ga.close()
        cv2.destroyAllWindows()
