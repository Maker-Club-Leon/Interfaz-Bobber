"""Carga config.toml mezclándolo con valores por defecto (requiere Python 3.11+)."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "model": {"path": "assets/mascota.gltf", "heading_degrees": 180},
    "animations": {"reposo": ["reposo", "idle"],
                    "saludo": ["saludo", "jump", "waving"],
                    "caminar": ["walk", "walking"]},
    "camera": {"index": 0, "width": 640, "height": 480, "starting_timeout_seconds": 10.0},
    "detection": {"auto_start": True, "interval_ms": 150, "min_visibility": 0.5,
                  "min_shoulder_width": 0.10, "pose_model": "assets/pose_landmarker_lite.task"},
    "timing": {"detect_seconds": 0.8, "reset_seconds": 4.0,
               "greeting_cooldown_seconds": 8.0, "lost_tolerance_seconds": 0.5},
    "gestures": {
        "enabled": True, "model": "assets/gesture_recognizer.task", "min_confidence": 0.6,
        "confirm_seconds": 0.6, "cooldown_seconds": 3.0, "release_seconds": 0.7, "walk_seconds": 4.0,
        "actions": {"palma_abierta": "saludo", "puno_cerrado": "caminar", "dedo_arriba": "ninguna",
                    "pulgar_arriba": "ninguna", "pulgar_abajo": "ninguna", "victoria": "ninguna",
                    "te_quiero": "ninguna"},
    },
    "window": {"fullscreen": True, "font": ""},
    "render": {"ambient": 0.9, "directional": 0.4},
    "messages": {"idle": "Acércate para saludar", "hello": "¡Hola!",
                 "after": "¡Disfruta de la feria!", "manual": "Modo manual",
                 "walk": "¡Vamos a dar un paseo!",
                 "hint": "Saluda con la mano abierta  ·  Cierra el puño para que camine",
                 "hold": "¡Mantén el gesto!"},
}


def load_config(path: Path | None = None) -> dict:
    cfg = {k: dict(v) for k, v in DEFAULTS.items()}
    path = path or ROOT / "config.toml"
    if path.exists():
        with open(path, "rb") as f:
            for section, values in tomllib.load(f).items():
                cfg.setdefault(section, {}).update(values)
    return cfg


def resolve(rel: str) -> Path:
    """Convierte una ruta relativa de config.toml en absoluta (respecto a la carpeta del proyecto)."""
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p
