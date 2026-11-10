"""Pruebas sin ventana ni cámara: python -m unittest discover -s tests -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mascota.behavior import GreetingLogic  # noqa: E402
from mascota.config import load_config, resolve  # noqa: E402
from mascota.modelio import inspect_glb, resolve_clips  # noqa: E402


class GreetingLogicTests(unittest.TestCase):
    def setUp(self):
        self.logic = GreetingLogic(detect_s=0.8, reset_s=4.0,
                                   cooldown_s=8.0, lost_tolerance_s=0.5)

    def test_saluda_solo_despues_de_presencia_estable(self):
        self.assertIsNone(self.logic.update(True, 0.0))
        self.assertIsNone(self.logic.update(True, 0.4))
        self.assertIsNone(self.logic.update(True, 0.79))
        self.assertEqual(self.logic.update(True, 0.8), "greet")

    def test_no_repite_mientras_sigue_la_persona(self):
        events = [self.logic.update(True, t / 10) for t in range(101)]
        self.assertEqual(events.count("greet"), 1)

    def test_hueco_breve_no_reinicia_confirmacion(self):
        self.logic.update(True, 0.0)
        self.logic.update(True, 0.3)
        self.logic.update(False, 0.4)
        self.logic.update(False, 0.7)  # 0,4 s desde la última detección
        self.assertEqual(self.logic.update(True, 0.8), "greet")

    def test_ausencia_rearma_el_saludo(self):
        logic = GreetingLogic(detect_s=0.8, reset_s=4.0,
                              cooldown_s=0.0, lost_tolerance_s=0.5)
        logic.update(True, 0.0)
        self.assertEqual(logic.update(True, 0.8), "greet")
        self.assertIsNone(logic.update(False, 1.0))
        self.assertEqual(logic.update(False, 5.0), "reset")
        logic.update(True, 5.1)
        self.assertEqual(logic.update(True, 6.0), "greet")

    def test_ausencia_confirmada_permite_saludar_antes_del_cooldown(self):
        self.logic.update(True, 0.0)
        self.assertEqual(self.logic.update(True, 0.8), "greet")
        self.logic.update(False, 1.0)
        self.assertEqual(self.logic.update(False, 5.0), "reset")
        self.assertIsNone(self.logic.update(True, 5.1))
        self.assertEqual(self.logic.update(True, 5.9), "greet")


class ClipAndModelTests(unittest.TestCase):
    def test_resuelve_clips_sin_distinguir_mayusculas(self):
        resolved = resolve_clips(
            ["idle", "jump", "walk"],
            {"reposo": ["Idle"], "saludo": ["Saludo", "JUMP"], "caminar": ["WALK"]},
        )
        self.assertEqual(resolved, {"reposo": "idle", "saludo": "jump", "caminar": "walk"})

    def test_configuracion_apunta_a_modelo_existente_y_clips(self):
        cfg = load_config()
        self.assertEqual(cfg["animations"]["reposo"], ["reposo", "idle"])
        self.assertTrue(resolve(cfg["model"]["path"]).is_file())

    def test_glb_y_gltf_del_proyecto_se_inspeccionan(self):
        gltf = inspect_glb(ROOT / "assets" / "mascota.gltf")
        glb = inspect_glb(ROOT / "assets" / "mascota.glb")
        self.assertEqual(gltf["animations"], ["idle", "jump", "walk"])
        self.assertTrue(gltf["materials"])
        self.assertTrue(gltf["images"])
        self.assertEqual(glb["animations"], [])
        self.assertTrue(glb["materials"])


if __name__ == "__main__":
    unittest.main()
