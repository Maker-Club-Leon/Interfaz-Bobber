"""Pruebas sin ventana ni cámara: python -m unittest discover -s tests -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mascota.behavior import ActionArbiter, GestureLogic, GreetingLogic  # noqa: E402
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


class GestureLogicTests(unittest.TestCase):
    """Valores iguales a config.toml: confirmar 0,6 s, cooldown 3 s, liberar 0,7 s."""

    def setUp(self):
        self.logic = GestureLogic(confirm_s=0.6, cooldown_s=3.0, release_s=0.7)

    def test_gesto_se_confirma_tras_mantenerlo(self):
        self.assertIsNone(self.logic.update("palma_abierta", 0.0))
        self.assertIsNone(self.logic.update("palma_abierta", 0.3))
        self.assertIsNone(self.logic.update("palma_abierta", 0.59))
        self.assertEqual(self.logic.update("palma_abierta", 0.6), "palma_abierta")

    def test_cambiar_de_gesto_reinicia_la_confirmacion(self):
        self.logic.update("palma_abierta", 0.0)
        self.assertIsNone(self.logic.update("puno_cerrado", 0.4))
        self.assertIsNone(self.logic.update("puno_cerrado", 0.9))
        self.assertEqual(self.logic.update("puno_cerrado", 1.0), "puno_cerrado")

    def test_perder_la_mano_reinicia_la_confirmacion(self):
        self.logic.update("palma_abierta", 0.0)
        self.logic.update(None, 0.4)
        self.assertIsNone(self.logic.update("palma_abierta", 0.5))
        self.assertIsNone(self.logic.update("palma_abierta", 1.0))
        self.assertEqual(self.logic.update("palma_abierta", 1.1), "palma_abierta")

    def test_gesto_sostenido_no_se_repite(self):
        events = [self.logic.update("palma_abierta", t / 10) for t in range(0, 201)]
        self.assertEqual(events.count("palma_abierta"), 1)

    def test_liberar_la_mano_rearma_el_mismo_gesto(self):
        self.logic.update("palma_abierta", 0.0)
        self.assertEqual(self.logic.update("palma_abierta", 0.6), "palma_abierta")
        self.logic.update(None, 1.0)
        self.logic.update(None, 2.0)  # 1 s sin gesto > release_s
        self.assertIsNone(self.logic.update("palma_abierta", 3.0))
        self.assertEqual(self.logic.update("palma_abierta", 3.6), "palma_abierta")

    def test_retirada_breve_no_rearma(self):
        self.logic.update("palma_abierta", 0.0)
        self.assertEqual(self.logic.update("palma_abierta", 0.6), "palma_abierta")
        self.logic.update(None, 1.0)
        self.logic.update(None, 1.5)  # solo 0,5 s sin gesto
        for t in (1.6, 4.0, 6.0):
            self.assertIsNone(self.logic.update("palma_abierta", t))

    def test_liberacion_necesita_ausencia_continua(self):
        self.logic.update("palma_abierta", 0.0)
        self.logic.update("palma_abierta", 0.6)
        self.logic.update(None, 1.0)
        self.logic.update("palma_abierta", 1.4)  # vuelve antes de liberar
        self.logic.update(None, 1.5)
        self.logic.update(None, 2.0)  # 0,5 s desde la nueva retirada
        self.assertIsNone(self.logic.update("palma_abierta", 5.0))
        self.assertIsNone(self.logic.update("palma_abierta", 6.0))

    def test_cooldown_aplica_a_otro_gesto(self):
        self.logic.update("palma_abierta", 0.0)
        self.assertEqual(self.logic.update("palma_abierta", 0.6), "palma_abierta")
        self.assertIsNone(self.logic.update("puno_cerrado", 1.0))
        self.assertIsNone(self.logic.update("puno_cerrado", 2.0))
        self.assertIsNone(self.logic.update("puno_cerrado", 3.5))   # confirmado, pero en cooldown
        self.assertEqual(self.logic.update("puno_cerrado", 3.6), "puno_cerrado")

    def test_cooldown_aplica_al_mismo_gesto_tras_liberar(self):
        self.logic.update("palma_abierta", 0.0)
        self.logic.update("palma_abierta", 0.6)
        self.logic.update(None, 0.7)
        self.logic.update(None, 1.5)  # liberada
        self.logic.update("palma_abierta", 1.6)
        self.assertIsNone(self.logic.update("palma_abierta", 2.5))  # confirmado, cooldown activo
        self.assertEqual(self.logic.update("palma_abierta", 3.6), "palma_abierta")

    def test_reset_olvida_bloqueo_y_cooldown(self):
        self.logic.update("palma_abierta", 0.0)
        self.logic.update("palma_abierta", 0.6)
        self.logic.reset()
        self.assertIsNone(self.logic.update("palma_abierta", 1.0))
        self.assertEqual(self.logic.update("palma_abierta", 1.6), "palma_abierta")


class ActionArbiterTests(unittest.TestCase):
    """Prioridad: manual > gesto > presencia."""

    def setUp(self):
        self.arb = ActionArbiter()

    def test_sin_accion_en_curso_acepta_cualquier_origen(self):
        for src in ("presence", "gesture", "manual"):
            arb = ActionArbiter()
            self.assertFalse(arb.busy(0.0))
            self.assertTrue(arb.request("saludo", src, 0.0, 2.0))
            self.assertTrue(arb.busy(1.0))

    def test_accion_termina_al_cumplir_su_duracion(self):
        self.arb.request("saludo", "presence", 0.0, 2.0)
        self.assertTrue(self.arb.busy(1.99))
        self.assertFalse(self.arb.busy(2.0))

    def test_presencia_no_interrumpe_nada(self):
        for src in ("presence", "gesture", "manual"):
            arb = ActionArbiter()
            arb.request("caminar", src, 0.0, 4.0)
            self.assertFalse(arb.request("saludo", "presence", 1.0, 2.0))
            self.assertEqual((arb.name, arb.src), ("caminar", src))

    def test_presencia_actua_cuando_termina_la_accion(self):
        self.arb.request("caminar", "gesture", 0.0, 4.0)
        self.assertTrue(self.arb.request("saludo", "presence", 4.0, 2.0))
        self.assertEqual(self.arb.src, "presence")

    def test_gesto_interrumpe_saludo_por_presencia(self):
        self.arb.request("saludo", "presence", 0.0, 2.0)
        self.assertTrue(self.arb.request("caminar", "gesture", 0.5, 4.0))
        self.assertEqual((self.arb.name, self.arb.src), ("caminar", "gesture"))
        self.assertTrue(self.arb.busy(4.0))

    def test_gesto_no_interrumpe_otro_gesto_ni_manual(self):
        for src in ("gesture", "manual"):
            arb = ActionArbiter()
            arb.request("saludo", src, 0.0, 2.0)
            self.assertFalse(arb.request("caminar", "gesture", 1.0, 4.0))
            self.assertEqual((arb.name, arb.src), ("saludo", src))
            self.assertTrue(arb.request("caminar", "gesture", 2.0, 4.0))

    def test_manual_interrumpe_cualquier_accion(self):
        for src in ("presence", "gesture", "manual"):
            arb = ActionArbiter()
            arb.request("caminar", src, 0.0, 4.0)
            self.assertTrue(arb.request("reposo", "manual", 1.0, 0.5))
            self.assertEqual((arb.name, arb.src), ("reposo", "manual"))

    def test_clear_libera_el_arbitro(self):
        self.arb.request("caminar", "manual", 0.0, 4.0)
        self.arb.clear()
        self.assertFalse(self.arb.busy(1.0))
        self.assertTrue(self.arb.request("saludo", "presence", 1.0, 2.0))


class ConfigTests(unittest.TestCase):
    def test_mensajes_usados_por_la_app_tienen_valor_por_defecto(self):
        """Un mensaje sin valor por defecto lanza KeyError y cierra la app (pasó con 'walk')."""
        import re
        from mascota.config import DEFAULTS
        source = (ROOT / "mascota" / "app.py").read_text(encoding="utf-8")
        used = set(re.findall(r"msgs\[\"(\w+)\"\]", source))
        self.assertIn("walk", used)
        self.assertEqual(used - set(DEFAULTS["messages"]), set())

    def test_config_toml_define_los_mismos_mensajes(self):
        import tomllib
        from mascota.config import DEFAULTS
        with open(ROOT / "config.toml", "rb") as f:
            toml_msgs = tomllib.load(f)["messages"]
        self.assertEqual(set(toml_msgs), set(DEFAULTS["messages"]))


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
