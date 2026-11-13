"""Aplicación Panda3D: muestra el GLB, reproduce reposo/saludo y reacciona a la cámara."""
import os
import time
import traceback

from direct.actor.Actor import Actor  # noqa: F401  (asegura que el módulo esté disponible)
from direct.gui.DirectGui import DirectButton, OnscreenText
from direct.interval.IntervalGlobal import Func, LerpHprInterval, LerpPosInterval, Parallel, Sequence
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (AmbientLight, CardMaker, DirectionalLight, Texture, TextNode,
                          WindowProperties, loadPrcFileData)

from .behavior import ActionArbiter, GestureLogic, GreetingLogic
from .config import resolve
from .detector import GESTURE_LABELS, PresenceDetector
from .modelio import inspect_glb, load_model

FONTS = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]


class MascotaApp(ShowBase):
    def __init__(self, cfg, start_manual=False, windowed=False):
        loadPrcFileData("", "window-title Mascota de la feria\nwin-size 1280 720\n"
                            "multisamples 4\nframebuffer-multisample 1\naudio-library-name null")
        super().__init__()
        self.cfg, self.msgs = cfg, cfg["messages"]
        self.disableMouse()
        self.setBackgroundColor(0.09, 0.2, 0.3)
        self.logic = GreetingLogic(
            cfg["timing"]["detect_seconds"], cfg["timing"]["reset_seconds"],
            cfg["timing"].get("greeting_cooldown_seconds", 0.0),
            cfg["timing"].get("lost_tolerance_seconds", 0.5))
        g = cfg["gestures"]                  # gestos: confirmación, espera entre acciones y prioridades
        self.glogic = GestureLogic(g["confirm_seconds"], g["cooldown_seconds"], g["release_seconds"])
        self.arbiter = ActionArbiter()
        self.gesture_actions = {k: v for k, v in g["actions"].items() if v not in ("", "ninguna")}
        self._gesture_err_shown = False
        self.detector, self.mode, self.debug, self._last_ui = None, "manual", False, 0.0
        self._detector_started_at = 0.0
        self._last_error, self._last_error_at = "", 0.0
        self.kiosk = cfg["window"]["fullscreen"] and not windowed
        self.exitFunc = self._cleanup

        self._load_font()
        self._build_scene()
        self._build_ui()
        self._set_window()
        self._ensure_idle_started()

        for key, fn in [("escape", self.userExit), ("q", self.userExit), ("f11", self.toggle_window),
                        ("1", self.idle), ("2", self.greet), ("3", self.walk), ("m", self.toggle_mode), ("c", self.toggle_debug)]:
            self.accept(key, self._safe(fn))
        self.taskMgr.add(self._safe_tick, "tick")
        if cfg["detection"]["auto_start"] and not start_manual:
            self.start_auto()
        else:
            self._say(self.msgs["manual"])

    # ---------- errores ----------
    def _safe(self, fn, where=None):
        """Envuelve una tecla, botón o temporizador: un fallo se avisa en pantalla y no cierra la app."""
        where = where or getattr(fn, "__name__", "acción")
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                self._handle_error(where, e)
        return wrapper

    def _safe_tick(self, task):
        try:
            return self._tick(task)
        except Exception as e:
            self._handle_error("bucle principal", e)
            return task.cont

    def _handle_error(self, where, e):
        """Registra el error en consola, avisa en pantalla y devuelve a la mascota a reposo."""
        now, text = time.monotonic(), f"{type(e).__name__}: {e}"
        if text == self._last_error and now - self._last_error_at < 5.0:
            return                                # el mismo fallo repetido: se vuelve a avisar cada 5 s
        self._last_error, self._last_error_at = text, now
        print(f"[ERROR] en {where}:\n{traceback.format_exc()}", flush=True)
        try:
            self.idle(announce=False)
        except Exception:
            pass                                  # si ni el reposo funciona, al menos la ventana sigue viva
        try:
            self._flash(f"Error interno en {where}: {text}. Bobber vuelve a reposo; "
                        "los controles siguen disponibles.")
        except Exception:
            pass

    # ---------- escena y modelo ----------
    def _build_scene(self):
        self.pivot = self.render.attachNewNode("pivot")     # lo que se anima en el modo provisional
        self.holder = self.pivot.attachNewNode("holder")
        self.model, anims, self.warning = None, [], ""
        path = resolve(self.cfg["model"]["path"])
        if not path.exists():
            self.warning = f"No encuentro el modelo: {path}. Colócalo ahí (ver README)."
        else:
            try:
                info = inspect_glb(path)
                self.model, anims = load_model(self.loader, path)
                self.model.reparentTo(self.holder)
            except Exception as e:
                self.warning = f"No se pudo cargar el modelo: {e}"
        self.anim_names = anims
        self.clip = {k: self._find_clip(self.cfg["animations"][k]) for k in ("reposo", "saludo", "caminar")}
        missing = [self.cfg["animations"][k] for k in ("reposo", "saludo") if self.clip[k] is None]
        if self.model and missing:
            self.warning = (f"Faltan animaciones {missing}. Clips en el modelo: {anims or 'ninguno'}. "
                            "Se usa un movimiento provisional. Ver README (Blender).")
        if (self.model and self.cfg["gestures"]["enabled"] and self.clip["caminar"] is None
                and "caminar" in self.gesture_actions.values()):
            self.warning = (self.warning + " " if self.warning else "") + (
                f"El modelo no tiene la animación '{self.cfg['animations']['caminar']}': "
                "el gesto que la activa no hará nada.")
        self._frame_model()
        amb, sun = AmbientLight("amb"), DirectionalLight("sun")
        a, d = self.cfg["render"]["ambient"], self.cfg["render"]["directional"]
        amb.setColor((a, a, a, 1)); sun.setColor((d, d, d, 1))
        self.render.setLight(self.render.attachNewNode(amb))
        s = self.render.attachNewNode(sun); s.setHpr(-30, -35, 0); self.render.setLight(s)
        self._build_fallback_intervals()

    def _find_clip(self, wanted):
        aliases = [wanted] if isinstance(wanted, str) else list(wanted)
        for alias in aliases:
            low = str(alias).lower()
            for n in self.anim_names:
                if n == alias: return n
            for n in self.anim_names:
                if n.lower() == low or low in n.lower(): return n
        return None

    def _frame_model(self):
        """Centra el modelo y coloca la cámara según su tamaño real."""
        self.height = 1.0
        if not self.model:
            return
        self.holder.setH(self.cfg["model"]["heading_degrees"])
        bounds = self.model.getTightBounds(self.pivot)
        if not bounds:
            self.warning = "El modelo no tiene geometría visible."
            return
        mn, mx = bounds
        size, center = mx - mn, (mx + mn) / 2
        self.holder.setPos(-center)
        self.height = max(size.z, 1e-3)
        import math
        vfov = math.radians(self.camLens.getVfov())
        dist = (max(size.z, size.x / max(self.camLens.getAspectRatio(), 0.1)) / 2) / math.tan(vfov / 2) * 1.4
        self.camera.setPos(0, -(dist + size.y / 2), 0)
        self.camera.lookAt(0, 0, 0)

    # ---------- animaciones ----------
    def _build_fallback_intervals(self):
        h, p = self.height, self.pivot
        self.fb_idle = Sequence(
            LerpPosInterval(p, 1.5, (0, 0, h * 0.02), startPos=(0, 0, 0), blendType="easeInOut"),
            LerpPosInterval(p, 1.5, (0, 0, 0), blendType="easeInOut"))
        hop = lambda: Sequence(LerpPosInterval(p, 0.15, (0, 0, h * 0.07), blendType="easeOut"),
                               LerpPosInterval(p, 0.15, (0, 0, 0), blendType="easeIn"))
        self.fb_greet = Sequence(
            Parallel(hop(), LerpHprInterval(p, 0.3, (8, 0, 0))),
            Parallel(hop(), LerpHprInterval(p, 0.3, (-8, 0, 0))),
            LerpHprInterval(p, 0.3, (0, 0, 0)), Func(self._after_greet))

    def _ensure_idle_started(self):
        self.idle(announce=False)

    def _stop_all(self):
        self.taskMgr.remove("after-greet")
        self.fb_idle.pause(); self.fb_greet.pause()
        self.pivot.setPosHpr(0, 0, 0, 0, 0, 0)
        if self.anim_names and isinstance(self.model, Actor):
            self.model.stop()

    def idle(self, announce=True):
        self.arbiter.clear()
        self._stop_all()
        if self.clip["reposo"] and isinstance(self.model, Actor):
            self.model.loop(self.clip["reposo"])
        else:
            self.fb_idle.loop()
        if announce:
            self._say(self.msgs["idle"] if self.mode == "auto" else self.msgs["manual"])

    def greet(self, src="manual"):
        """Saludo. src: 'manual' (botón/tecla), 'gesture' o 'presence' (ver ActionArbiter)."""
        has_clip = self.clip["saludo"] and isinstance(self.model, Actor)
        dur = self.model.getDuration(self.clip["saludo"]) if has_clip else 1.0
        if not self.arbiter.request("saludo", src, time.monotonic(), dur):
            return False                      # hay una acción de mayor prioridad en curso
        self._stop_all()
        self._say(self.msgs["hello"])
        if has_clip:
            self.model.play(self.clip["saludo"])
            self.taskMgr.doMethodLater(dur, self._safe(lambda t: self._after_greet(), "fin del saludo"), "after-greet")
        else:
            self.fb_greet.start()
        return True

    def _after_greet(self):
        self.idle(announce=False)
        self._say(self.msgs["after"])

    def walk(self, src="manual"):
        """Caminar: solo si el GLB tiene el clip. No se inventa ninguna animación."""
        if not (self.clip["caminar"] and isinstance(self.model, Actor)):
            self._flash(f"El modelo no tiene la animación '{self.cfg['animations']['caminar']}'. "
                        f"Clips en el modelo: {self.anim_names or 'ninguno'}. Ver README (Blender).")
            return False
        dur = self.cfg["gestures"]["walk_seconds"]
        if not self.arbiter.request("caminar", src, time.monotonic(), dur):
            return False
        self._stop_all()
        self._say(self.msgs["walk"])
        self.model.loop(self.clip["caminar"])
        self.taskMgr.doMethodLater(dur, self._safe(lambda t: self._after_walk(), "fin del paseo"), "after-greet")
        return True

    def _after_walk(self):
        self.idle(announce=True)

    def _run_gesture(self, key):
        action = self.gesture_actions.get(key)
        if action == "saludo": self.greet("gesture")
        elif action == "caminar": self.walk("gesture")
        elif action == "reposo": self.idle()
        else: self._flash(f"Acción desconocida '{action}' para el gesto {key} (usa saludo, caminar, reposo o ninguna).")

    def _flash(self, text, secs=5.0):
        """Mensaje temporal de error/aviso; después vuelve al aviso permanente (si lo hay)."""
        self.err_text.setText(text)
        self.taskMgr.remove("flash")
        self.taskMgr.doMethodLater(secs, lambda t: self.err_text.setText(self.warning), "flash")

    # ---------- cámara / modos ----------
    def start_auto(self):
        if self.detector is not None:
            if self.detector.is_alive():
                self._flash("La cámara aún se está cerrando. Espera unos segundos antes de volver a activar el modo automático.")
                return
            self.detector = None
        self.logic.clear(); self.glogic.reset()
        self.detector = PresenceDetector(self.cfg)
        self.detector.preview_enabled = self.debug
        self._detector_started_at = time.monotonic()
        self.detector.start()
        self.mode = "auto"
        self._say(self.msgs["idle"])

    def to_manual(self, reason=""):
        detector = self.detector
        if detector:
            detector.stop()
            if detector.is_alive():
                detector.join(timeout=0.25)
            self.detector = detector if detector.is_alive() else None
            if detector.is_alive():
                reason = (reason + " " if reason else "") + (
                    "La cámara sigue cerrándose; no se iniciará otra captura hasta que termine el hilo.")
        self.mode = "manual"
        self.glogic.reset()
        self._say(self.msgs["manual"])
        self.err_text.setText(reason)

    def toggle_mode(self):
        if self.mode == "auto": self.to_manual("")
        else: self.err_text.setText(""); self.start_auto()

    def toggle_debug(self):
        self.debug = not self.debug
        if self.detector: self.detector.preview_enabled = self.debug
        for n in (self.debug_text, self.preview_card):
            n.show() if self.debug else n.hide()
        self._apply_controls_visibility()

    def _controls_visible(self):
        """En modo stand (pantalla completa) el público solo ve la mascota; C o F11 muestran los controles."""
        return not (self.kiosk and self.cfg["window"]["hide_controls"]) or self.debug

    def _apply_controls_visibility(self):
        visible = self._controls_visible()
        for n in self.buttons + [self.status]:
            n.show() if visible else n.hide()
        # Sin botones, los avisos bajan al hueco que dejan; con botones, van por encima
        self.err_text.setPos(0, 0.37 if visible else 0.12)
        if hasattr(self.win, "requestProperties"):      # un buffer sin ventana no tiene cursor
            wp = WindowProperties(); wp.setCursorHidden(not visible)
            self.win.requestProperties(wp)

    def _tick(self, task):
        now = time.monotonic()
        if self.mode == "manual" and self.detector and not self.detector.is_alive():
            self.detector = None
        d = self.detector
        if self.mode == "auto" and d:
            if d.status == "error":
                self.to_manual(f"Cámara no disponible: {d.error}. Modo manual activo.")
            elif (d.status == "starting" and now - self._detector_started_at
                  >= self.cfg["camera"].get("starting_timeout_seconds", 10.0)):
                self.to_manual("La cámara no responde. Modo manual activo; comprueba el permiso o la conexión.")
            elif d.status == "running":
                # Prioridad: gesto > presencia. La presencia nunca interrumpe una acción en curso.
                ev = self.logic.update(d.present, now)
                if ev == "greet": self.greet("presence")
                elif ev == "reset" and not self.arbiter.busy(now): self.idle()
                if d.gesture_status == "ready":
                    key = d.gesture if d.gesture in self.gesture_actions else None
                    fired = self.glogic.update(key, now)
                    if fired: self._run_gesture(fired)
                elif d.gesture_status == "error" and not self._gesture_err_shown:
                    self._gesture_err_shown = True
                    self.warning = (f"Gestos desactivados: {d.gesture_error}. "
                                    "La detección de personas y el modo manual siguen activos.")
                    self.err_text.setText(self.warning)
        if now - self._last_ui > 0.1:
            self._last_ui = now
            self._refresh_ui()
        return task.cont

    # ---------- interfaz ----------
    def _load_font(self):
        self.font = None
        for p in ([self.cfg["window"]["font"]] if self.cfg["window"]["font"] else []) + FONTS:
            if p and os.path.exists(p):
                from panda3d.core import Filename
                self.font = self.loader.loadFont(Filename.fromOsSpecific(p).getFullpath())
                self.font.setPixelsPerUnit(64)
                break

    def _text(self, parent, **kw):
        return OnscreenText(parent=parent, font=self.font, shadow=(0, 0, 0, 0.6), mayChange=True, **kw)

    def _build_ui(self):
        self.msg = self._text(self.a2dTopCenter, pos=(0, -0.2), scale=0.13, fg=(1, 1, 1, 1))
        self.status = self._text(self.a2dTopLeft, pos=(0.03, -0.06), scale=0.04, fg=(1, 1, 1, 0.7), align=TextNode.ALeft)
        self.err_text = self._text(self.a2dBottomCenter, pos=(0, 0.37), scale=0.045, fg=(1, 0.7, 0.6, 1), wordwrap=40)
        self.err_text.setText(self.warning)
        # Ayuda para el visitante: qué gestos hay y, mientras se confirma uno, una barra de progreso
        self.hint_text = self._text(self.a2dBottomCenter, pos=(0, 0.235), scale=0.06, fg=(1, 1, 1, 0.9))
        cm = CardMaker("hold-bg"); cm.setFrame(-0.3, 0.3, -0.008, 0.008)
        self.hold_bar = self.a2dBottomCenter.attachNewNode("hold-bar")
        self.hold_bar.setPos(0, 0, 0.205)
        bg = self.hold_bar.attachNewNode(cm.generate()); bg.setColor(1, 1, 1, 0.25)
        cm = CardMaker("hold-fill"); cm.setFrame(0, 0.6, -0.008, 0.008)
        self.hold_fill = self.hold_bar.attachNewNode(cm.generate())
        self.hold_fill.setPos(-0.3, 0, 0); self.hold_fill.setColor(1, 0.85, 0.3, 1)
        self.hold_bar.setTransparency(True); self.hold_bar.hide()
        self.debug_text = self._text(self.a2dTopRight, pos=(-0.05, -0.75), scale=0.04, align=TextNode.ARight, fg=(1, 1, 1, 1))
        cm = CardMaker("preview"); cm.setFrame(-0.4, 0.4, -0.3, 0.3)
        self.preview_card = self.a2dTopRight.attachNewNode(cm.generate())
        self.preview_card.setPos(-0.45, 0, -0.35)
        self.preview_tex = Texture(); self.preview_card.setTexture(self.preview_tex)
        self.debug_text.hide(); self.preview_card.hide()

        buttons = [("Reposo (1)", self.idle), ("Saludo (2)", self.greet), ("Caminar (3)", self.walk), ("Auto/Manual (M)", self.toggle_mode),
                   ("Calibración (C)", self.toggle_debug), ("Pantalla (F11)", self.toggle_window)]
        widths = [len(t) * 0.5 + 1.6 for t, _ in buttons]
        gap, sc = 0.7, 0.05
        x = -(sum(widths) + gap * (len(widths) - 1)) * sc / 2
        self.buttons = []
        for (label, cmd), w in zip(buttons, widths):
            btn = DirectButton(parent=self.a2dBottomCenter, text=label, text_font=self.font, command=self._safe(cmd), scale=sc,
                         pos=(x + w * sc / 2, 0, 0.1), frameSize=(-w / 2, w / 2, -0.5, 1.1), text_pos=(0, 0),
                         frameColor=(1, 1, 1, 0.18), text_fg=(1, 1, 1, 1), relief=1, pressEffect=1)
            self.buttons.append(btn)
            x += (w + gap) * sc

    def _refresh_ui(self):
        d = self.detector
        cam = "cerrando cámara…" if self.mode == "manual" and d and d.is_alive() else (
            {"starting": "iniciando cámara…", "running": "cámara activa", "error": "cámara con error",
               "stopped": "detenida"}.get(d.status, "") if d else "sin cámara"
        )
        hand = self._hand_text(d)
        self.status.setText(f"Modo {self.mode} · {cam}" + (f" · {hand}" if hand else ""))
        self._refresh_hint(d)
        if self.debug and d:
            self.debug_text.setText(
                f"persona: {'SÍ' if d.present else 'no'}\nanchura hombros: {d.shoulder_width:.2f} "
                f"(mín {self.cfg['detection']['min_shoulder_width']})\nvisibilidad: {d.visibility:.2f} "
                f"(mín {self.cfg['detection']['min_visibility']})\nanálisis/s: {d.fps:.1f}\n"
                f"{self._hand_text(d) or 'gestos desactivados'} (conf. {d.gesture_score:.2f}, "
                f"mín {self.cfg['gestures']['min_confidence']})")
            p = d.take_preview()
            if p:
                w, h, data = p
                if self.preview_tex.getXSize() != w:
                    self.preview_tex.setup2dTexture(w, h, Texture.T_unsigned_byte, Texture.F_rgb)
                self.preview_tex.setRamImageAs(data, "BGR")

    def _refresh_hint(self, d):
        """Muestra qué gestos hay; mientras se mantiene uno que va a actuar, pide sostenerlo."""
        gestures_ready = (self.mode == "auto" and d is not None and d.status == "running"
                          and d.gesture_status == "ready" and bool(self.gesture_actions))
        pending = self.glogic.pending(time.monotonic()) if gestures_ready else None
        if pending and self.msgs["hold"]:
            _key, progress = pending
            self.hint_text.setFg((1, 0.85, 0.3, 1))
            self.hint_text.setText(self.msgs["hold"])
            self.hold_fill.setSx(max(progress, 0.001))
            self.hold_bar.show()
        else:
            self.hold_bar.hide()
            self.hint_text.setFg((1, 1, 1, 0.9))
            self.hint_text.setText(self.msgs["hint"] if gestures_ready else "")

    def _hand_text(self, d):
        """Texto de estado de la mano, p. ej. 'Mano detectada: palma abierta'."""
        if not d or not self.cfg["gestures"]["enabled"] or d.gesture_status != "ready":
            return ""
        if not d.hand_present:
            return "Sin mano"
        name = GESTURE_LABELS[d.gesture_label][1] if d.gesture_label else "sin gesto reconocido"
        return f"Mano detectada: {name}"

    def _say(self, text):
        self.msg.setText(text)

    # ---------- ventana ----------
    def _set_window(self):
        wp = WindowProperties()
        if self.kiosk:
            wp.setUndecorated(True); wp.setOrigin(0, 0)
            wp.setSize(self.pipe.getDisplayWidth(), self.pipe.getDisplayHeight())
        else:
            wp.setUndecorated(False); wp.setOrigin(80, 80); wp.setSize(1280, 720)
        self.win.requestProperties(wp)
        self._apply_controls_visibility()

    def toggle_window(self):
        self.kiosk = not self.kiosk
        self._set_window()

    def _cleanup(self):
        if self.detector:
            self.detector.stop()
            if self.detector.is_alive():
                self.detector.join(timeout=0.5)
