"""Pruebas sin ventana ni cámara: python -m unittest discover -s tests -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mascota.behavior import ActionArbiter, AttractLogic, GestureLogic, GreetingLogic  # noqa: E402
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

    def test_pending_indica_progreso_de_confirmacion(self):
        self.assertIsNone(self.logic.pending(0.0))
        self.logic.update("palma_abierta", 0.0)
        self.assertEqual(self.logic.pending(0.3), ("palma_abierta", 0.5))
        self.assertEqual(self.logic.pending(5.0), ("palma_abierta", 1.0))

    def test_pending_vacio_tras_actuar_y_con_mano_bloqueada(self):
        self.logic.update("palma_abierta", 0.0)
        self.logic.update("palma_abierta", 0.6)
        self.logic.update("palma_abierta", 4.0)  # misma mano sigue levantada: bloqueada
        self.assertIsNone(self.logic.pending(4.0))

    def test_pending_vacio_durante_cooldown(self):
        self.logic.update("palma_abierta", 0.0)
        self.logic.update("palma_abierta", 0.6)
        self.logic.update("puno_cerrado", 1.0)   # otro gesto, pero aún en cooldown
        self.assertIsNone(self.logic.pending(2.0))
        self.assertEqual(self.logic.pending(3.6)[0], "puno_cerrado")

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

    def test_reclamo_solo_si_no_hay_nada_en_curso(self):
        for src in ("attract", "presence", "gesture", "manual"):
            arb = ActionArbiter()
            arb.request("caminar", src, 0.0, 4.0)
            self.assertFalse(arb.request("saludo", "attract", 1.0, 1.0))
        self.assertTrue(ActionArbiter().request("saludo", "attract", 0.0, 1.0))

    def test_cualquier_origen_interrumpe_un_reclamo(self):
        for src in ("presence", "gesture", "manual"):
            arb = ActionArbiter()
            arb.request("caminar", "attract", 0.0, 4.0)
            self.assertTrue(arb.request("saludo", src, 1.0, 1.0))
            self.assertEqual(arb.src, src)

    def test_presencia_sigue_sin_interrumpir_gesto_ni_manual(self):
        for src in ("gesture", "manual"):
            arb = ActionArbiter()
            arb.request("caminar", src, 0.0, 4.0)
            self.assertFalse(arb.request("saludo", "presence", 1.0, 1.0))

    def test_clear_libera_el_arbitro(self):
        self.arb.request("caminar", "manual", 0.0, 4.0)
        self.arb.clear()
        self.assertFalse(self.arb.busy(1.0))
        self.assertTrue(self.arb.request("saludo", "presence", 1.0, 2.0))


class AttractLogicTests(unittest.TestCase):
    """Caso A: 15 s sin nadie. Caso B: 45 s sin interacción aunque pase gente."""

    def setUp(self):
        self.logic = AttractLogic(empty_s=15.0, idle_s=45.0)

    def up(self, t, someone=False, hand=False, busy=False):
        return self.logic.update(someone, hand, busy, t)

    def test_a_actua_tras_15_s_sin_nadie(self):
        self.assertIsNone(self.up(0.0))
        self.assertIsNone(self.up(14.9))
        self.assertEqual(self.up(15.0), "empty")

    def test_a_repite_cada_15_s_mientras_no_haya_nadie(self):
        self.up(0.0)
        self.assertEqual(self.up(15.0), "empty")
        self.assertIsNone(self.up(25.0))
        self.assertEqual(self.up(30.0), "empty")

    def test_a_alguien_que_pasa_reinicia_la_cuenta_de_vacio(self):
        self.up(0.0)
        self.up(10.0, someone=True)
        self.assertIsNone(self.up(20.0))
        self.assertEqual(self.up(25.0), "empty")

    def test_b_gente_pasando_sin_interactuar_45_s(self):
        self.up(0.0)
        for t in range(1, 45):                   # siempre hay alguien delante: el caso A no actúa
            self.assertIsNone(self.up(float(t), someone=True))
        self.assertEqual(self.up(45.0, someone=True), "idle")

    def test_b_un_gesto_o_tecla_reinicia_la_cuenta(self):
        self.up(0.0, someone=True)
        self.logic.interaction(30.0)
        self.assertIsNone(self.up(60.0, someone=True))
        self.assertEqual(self.up(75.0, someone=True), "idle")

    def test_b_el_saludo_por_presencia_no_cuenta_como_interaccion(self):
        self.up(0.0, someone=True)
        self.up(1.0, someone=True, busy=True)     # saludo automático en curso
        self.assertIsNone(self.up(2.0, someone=True))
        self.assertEqual(self.up(45.0, someone=True), "idle")

    def test_nunca_con_accion_en_curso(self):
        self.up(0.0)
        self.assertIsNone(self.up(100.0, busy=True))

    def test_nunca_con_una_mano_a_la_vista(self):
        self.up(0.0, someone=True)
        self.assertIsNone(self.up(60.0, someone=True, hand=True))
        self.assertEqual(self.up(61.0, someone=True), "idle")

    def test_accion_en_curso_reinicia_la_cuenta_de_vacio(self):
        self.up(0.0)
        self.up(14.0, busy=True)                 # p. ej. el personal pulsó 3
        self.assertIsNone(self.up(20.0))
        self.assertEqual(self.up(29.0), "empty")

    def test_cada_caso_se_desactiva_con_cero(self):
        solo_b = AttractLogic(0, 45.0)
        self.assertIsNone(solo_b.update(False, False, False, 0.0))
        self.assertIsNone(solo_b.update(False, False, False, 30.0))
        self.assertEqual(solo_b.update(False, False, False, 45.0), "idle")
        nada = AttractLogic(0, 0)
        self.assertFalse(any(nada.update(False, False, False, t) for t in range(0, 1000, 10)))


class StandStatsTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from datetime import datetime
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "estadisticas" / "bobber.csv"
        self.now = datetime(2026, 11, 20, 10, 15)
        self.clock = lambda: self.now

    def tearDown(self):
        self.tmp.cleanup()

    def stats(self):
        from mascota.stats import StandStats
        return StandStats(self.path, save_every_s=60.0, clock=self.clock)

    def read(self):
        import csv
        with open(self.path, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f, delimiter=";"))

    def test_columnas_por_origen(self):
        from mascota.stats import column_for
        self.assertEqual(column_for("saludo", "presence"), "saludos_por_presencia")
        self.assertEqual(column_for("saludo", "gesture"), "gestos_saludo")
        self.assertEqual(column_for("caminar", "gesture"), "gestos_caminar")
        self.assertEqual(column_for("caminar", "attract", "empty"), "reclamos_sin_nadie")
        self.assertEqual(column_for("saludo", "attract", "idle"), "reclamos_sin_interaccion")
        self.assertEqual(column_for("caminar", "manual"), "teclas")

    def test_cuenta_por_hora_y_guarda_csv(self):
        from datetime import datetime
        s = self.stats()
        s.record("saludos_por_presencia"); s.record("saludos_por_presencia"); s.record("gestos_saludo")
        self.now = datetime(2026, 11, 20, 11, 5)
        s.record("reclamos_sin_nadie")
        s.save()
        rows = self.read()
        self.assertEqual([(r["fecha"], r["hora"]) for r in rows],
                         [("2026-11-20", "10:00"), ("2026-11-20", "11:00")])
        self.assertEqual(rows[0]["saludos_por_presencia"], "2")
        self.assertEqual(rows[0]["gestos_saludo"], "1")
        self.assertEqual(rows[1]["reclamos_sin_nadie"], "1")
        self.assertEqual(rows[1]["saludos_por_presencia"], "0")

    def test_reiniciar_la_app_sigue_sumando(self):
        s = self.stats(); s.record("teclas"); s.save()
        s2 = self.stats(); s2.record("teclas"); s2.save()
        self.assertEqual(self.read()[0]["teclas"], "2")

    def test_guarda_como_mucho_cada_intervalo(self):
        s = self.stats()
        s.maybe_save(0.0)
        s.record("gestos_caminar")
        s.maybe_save(30.0)
        self.assertFalse(self.path.exists())
        s.maybe_save(60.0)
        self.assertTrue(self.path.exists())

    def test_fallo_al_guardar_no_se_repite_en_cada_fotograma(self):
        s = self.stats()
        s.maybe_save(0.0)
        s.record("teclas")
        s.save = lambda: (_ for _ in ()).throw(PermissionError("abierto en Excel"))
        with self.assertRaises(PermissionError):
            s.maybe_save(60.0)
        s.maybe_save(60.1)                       # no lo vuelve a intentar hasta el siguiente intervalo
        self.assertTrue(s.dirty)

    def test_columna_desconocida_se_ignora(self):
        s = self.stats(); s.record(None); s.record("otra")
        self.assertFalse(s.dirty)

    def test_solo_contiene_numeros(self):
        """Privacidad: el CSV solo tiene fecha, hora y recuentos."""
        s = self.stats(); s.record("saludos_por_presencia"); s.save()
        row = self.read()[0]
        self.assertTrue(all(v.isdigit() for k, v in row.items() if k not in ("fecha", "hora")))


class ConfigTests(unittest.TestCase):
    def test_mensajes_usados_por_la_app_tienen_valor_por_defecto(self):
        """Un mensaje sin valor por defecto lanza KeyError y cierra la app (pasó con 'walk')."""
        import re
        from mascota.config import DEFAULTS
        source = (ROOT / "mascota" / "app.py").read_text(encoding="utf-8")
        used = set(re.findall(r"msgs\[[\"'](\w+)[\"']\]", source))
        self.assertTrue({"walk", "hint", "hold"} <= used)
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
