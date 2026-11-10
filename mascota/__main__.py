import argparse


def main():
    ap = argparse.ArgumentParser(description="Mascota de la feria")
    ap.add_argument("--selftest", action="store_true", help="prueba breve de modelo, ventana y cámara")
    ap.add_argument("--calibrar", action="store_true", help="ver qué detecta la cámara (ventana OpenCV)")
    ap.add_argument("--manual", action="store_true", help="arrancar sin cámara")
    ap.add_argument("--ventana", action="store_true", help="no usar pantalla completa")
    ap.add_argument("--descargar-modelos", action="store_true", help="descarga los modelos de MediaPipe (poses y gestos)")
    a = ap.parse_args()
    if a.descargar_modelos:
        from .config import load_config
        from .detector import download_models
        return download_models(load_config())
    if a.selftest:
        from .selftest import main as run
        return run()
    if a.calibrar:
        from .calibrate import main as run
        return run()
    from .app import MascotaApp
    from .config import load_config
    MascotaApp(load_config(), start_manual=a.manual, windowed=a.ventana).run()


main()
