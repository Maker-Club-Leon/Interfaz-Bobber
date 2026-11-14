"""Lógica de saludo, independiente de cámara y gráficos (fácil de probar)."""


class GreetingLogic:
    """Saluda una vez por presencia continua y rearma tras una ausencia confirmada."""

    def __init__(self, detect_s: float, reset_s: float,
                 cooldown_s: float = 0.0, lost_tolerance_s: float = 0.5):
        self.detect_s = max(0.0, float(detect_s))
        self.reset_s = max(0.0, float(reset_s))
        self.cooldown_s = max(0.0, float(cooldown_s))
        self.lost_tolerance_s = max(0.0, float(lost_tolerance_s))
        self.clear()

    def clear(self):
        self.greeted = False
        self.present_since = None
        self.absent_since = None
        self.last_present = None
        self.last_greet = None
        self.reset_sent = False

    def update(self, present: bool, now: float):
        if present:
            self.absent_since = None
            self.reset_sent = False
            if self.present_since is None:
                self.present_since = now
            self.last_present = now
            cooldown_over = self.last_greet is None or now - self.last_greet >= self.cooldown_s
            if (not self.greeted and cooldown_over
                    and now - self.present_since >= self.detect_s):
                self.greeted = True
                self.last_greet = now
                return "greet"
        else:
            if self.absent_since is None:
                self.absent_since = now
            if (self.last_present is None
                    or now - self.last_present > self.lost_tolerance_s):
                self.present_since = None
                # Una ausencia confirmada inicia una visita nueva. No aplicar el
                # cooldown de la visita anterior a quien acaba de acercarse.
                self.greeted = False
                self.last_greet = None
            if not self.reset_sent and now - self.absent_since >= self.reset_s:
                self.reset_sent = True
                return "reset"
        return None

class GestureLogic:
    """Confirma un gesto estable y evita repeticiones.

    update(clave, now) recibe la clave del gesto con acción asignada (o None si no hay mano/gesto
    reconocido) y devuelve esa clave solo cuando hay que ejecutar la acción:
      - el gesto debe mantenerse `confirm_s` segundos;
      - entre dos acciones deben pasar `cooldown_s` segundos;
      - tras actuar, el MISMO gesto no se repite hasta que la mano se retire (o deje de haber un
        gesto reconocido) durante `release_s` segundos. Otro gesto distinto sí puede activarse.
    """

    def __init__(self, confirm_s: float, cooldown_s: float, release_s: float):
        self.confirm_s, self.cooldown_s, self.release_s = confirm_s, cooldown_s, release_s
        self.reset()

    def reset(self):
        self.candidate = self.since = self.blocked = self.idle_since = None
        self.last_fire = float("-inf")

    def update(self, key, now: float):
        if key is None:
            self.candidate = None
            self.idle_since = now if self.idle_since is None else self.idle_since
            if self.blocked and now - self.idle_since >= self.release_s:
                self.blocked = None                   # mano retirada: listo para el siguiente gesto
            return None
        self.idle_since = None
        if key == self.blocked:
            return None                               # misma mano sigue levantada
        if key != self.candidate:
            self.candidate, self.since = key, now
        if now - self.since < self.confirm_s or now - self.last_fire < self.cooldown_s:
            return None
        self.last_fire, self.blocked, self.candidate = now, key, None
        return key

    def pending(self, now: float):
        """Gesto que se está confirmando y que actuará si se mantiene: (clave, progreso 0-1) o None.

        No devuelve nada durante el cooldown (aunque haya candidato, no actuaría todavía) ni para
        un gesto bloqueado hasta retirar la mano."""
        if self.candidate is None or now - self.last_fire < self.cooldown_s:
            return None
        progress = 1.0 if self.confirm_s <= 0 else min(1.0, (now - self.since) / self.confirm_s)
        return self.candidate, progress


class AttractLogic:
    """Modo reclamo: pide una acción para llamar la atención en dos casos.

    A) `empty_s` segundos seguidos sin nadie delante (ni persona ni mano) y sin acciones en curso.
    B) `idle_s` segundos sin ninguna interacción (gesto o tecla), aunque haya gente pasando: quien pasa
       por delante sin mirar no cuenta. El saludo automático por presencia no es una interacción.

    Nunca actúa con una acción en curso ni con una mano a la vista (alguien puede estar haciendo un
    gesto). Tras cada reclamo, ambas cuentas empiezan de cero. Un valor <= 0 desactiva ese caso.
    update() devuelve "empty", "idle" o None; interaction(now) registra una interacción."""

    def __init__(self, empty_s: float, idle_s: float):
        self.empty_s, self.idle_s = float(empty_s), float(idle_s)
        self.reset()

    def reset(self):
        self.empty_since = self.last_interaction = None

    def interaction(self, now: float):
        self.last_interaction = now

    def update(self, someone: bool, hand: bool, busy: bool, now: float):
        if self.empty_s <= 0 and self.idle_s <= 0:
            return None
        if self.empty_since is None:
            self.empty_since = now
        if self.last_interaction is None:
            self.last_interaction = now
        if someone or busy:
            self.empty_since = now
        if busy or hand:
            return None
        reason = None
        if self.empty_s > 0 and not someone and now - self.empty_since >= self.empty_s:
            reason = "empty"
        elif self.idle_s > 0 and now - self.last_interaction >= self.idle_s:
            reason = "idle"
        if reason:
            self.empty_since = self.last_interaction = now
        return reason


class ActionArbiter:
    """Prioridades entre orígenes de acción: manual > gesto > presencia > reclamo.

    - 'manual' (botones/teclas): siempre se ejecuta.
    - 'gesture': se ejecuta salvo que otra acción de gesto siga en curso (puede interrumpir un saludo
      por presencia, porque es una petición deliberada).
    - 'presence': solo si no hay acción en curso, salvo un reclamo (alguien ha llegado: se le saluda).
    - 'attract': solo si no hay ninguna acción en curso (nunca interrumpe nada).
    """

    def __init__(self):
        self.clear()

    def clear(self):
        self.name = self.src = None
        self.until = 0.0

    def busy(self, now: float) -> bool:
        return self.name is not None and now < self.until

    def request(self, name: str, src: str, now: float, duration: float) -> bool:
        if src == "attract" and self.busy(now):
            return False
        if src == "presence" and self.busy(now) and self.src != "attract":
            return False
        if src == "gesture" and self.busy(now) and self.src in ("gesture", "manual"):
            return False
        self.name, self.src, self.until = name, src, now + duration
        return True
