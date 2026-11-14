"""Contador anónimo del stand: cuántas acciones hubo en cada hora, sin imágenes ni personas.

Guarda un CSV local (separado por «;» y con BOM, para abrirlo directamente en Excel en español)
con una fila por hora. Si la app se reinicia el mismo día, sigue sumando sobre lo guardado.
"""
import csv
import os
from datetime import datetime
from pathlib import Path

# Columna del CSV -> descripción. El orden es el de las columnas.
COLUMNS = {
    "saludos_por_presencia": "saludo automático al detectar a alguien",
    "gestos_saludo": "saludo por gesto (palma abierta)",
    "gestos_caminar": "paseo por gesto (puño cerrado)",
    "reclamos_sin_nadie": "modo reclamo con el stand vacío",
    "reclamos_sin_interaccion": "modo reclamo con gente que no interactúa",
    "teclas": "acciones lanzadas por el personal con el teclado o los botones",
}
HEADER = ["fecha", "hora"] + list(COLUMNS)


def column_for(action: str, src: str, attract_reason: str | None = None):
    """Traduce una acción aceptada a su columna, o None si no se cuenta."""
    if src == "presence":
        return "saludos_por_presencia"
    if src == "gesture":
        return {"saludo": "gestos_saludo", "caminar": "gestos_caminar"}.get(action)
    if src == "attract":
        return "reclamos_sin_interaccion" if attract_reason == "idle" else "reclamos_sin_nadie"
    if src == "manual":
        return "teclas"
    return None


class StandStats:
    def __init__(self, path, save_every_s: float = 60.0, clock=datetime.now):
        self.path = Path(path)
        self.save_every_s = save_every_s
        self.clock = clock
        self.rows: dict[tuple[str, str], dict[str, int]] = {}
        self.dirty, self._last_save = False, None
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        with open(self.path, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=";"):
                key = (r.get("fecha", ""), r.get("hora", ""))
                self.rows[key] = {c: int(r.get(c) or 0) for c in COLUMNS}

    def record(self, column: str | None):
        if column not in COLUMNS:
            return
        now = self.clock()
        key = (now.strftime("%Y-%m-%d"), now.strftime("%H:00"))
        row = self.rows.setdefault(key, {c: 0 for c in COLUMNS})
        row[column] += 1
        self.dirty = True

    def maybe_save(self, monotonic_now: float):
        """Guarda como mucho cada `save_every_s` segundos si hay cambios.

        Si falla (p. ej. el CSV está abierto en Excel), lanza OSError y lo reintenta en el
        siguiente intervalo, no en cada fotograma; los datos siguen en memoria."""
        if self._last_save is None:
            self._last_save = monotonic_now
        if self.dirty and monotonic_now - self._last_save >= self.save_every_s:
            self._last_save = monotonic_now
            self.save()

    def save(self):
        """Escribe el CSV completo de forma atómica (un archivo temporal y luego reemplazo)."""
        if not self.dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(HEADER)
            for (fecha, hora), row in sorted(self.rows.items()):
                w.writerow([fecha, hora] + [row[c] for c in COLUMNS])
        os.replace(tmp, self.path)
        self.dirty = False
