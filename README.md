# Mascota de la feria (versión Python)

Ventana de escritorio con tu modelo glTF de Blender (Panda3D) que saluda cuando la cámara (OpenCV + MediaPipe)
detecta a alguien. Todo es local: no se identifica a nadie y **no se guardan ni envían imágenes**
(los fotogramas solo existen en memoria). Los modelos de detección vienen incluidos; internet solo hace falta
para instalar dependencias o volver a descargar un modelo si falta.

## Qué hay en tu modelo (inspeccionado)
`assets/mascota.gltf`: modelo autocontenido con esqueleto, una malla, un material, una imagen y tres animaciones:
`idle`, `jump`, `walk`. La configuración usa `idle` para reposo, `jump` como saludo y `walk` para caminar.
`jump` es un salto, no un movimiento de mano saludando; para un saludo real crea un clip `saludo` en Blender y cambia `[animations] saludo`.

## Instalar y ejecutar (Windows 10/11)
1. Instala **Python 3.11 o 3.12 de 64 bits** (python.org; marca "Add to PATH"). MediaPipe aún no declara soporte para 3.13+.
2. Descomprime esta carpeta (no toca el proyecto web).
3. Haz doble clic en **`run.bat`**. La primera vez crea `.venv` e instala dependencias (necesita internet, unos minutos).
4. Los modelos de pose y gestos vienen incluidos. Si falta alguno, con internet ejecuta `run.bat --descargar-modelos` para recuperarlo; después la app funciona sin internet.
5. Opciones: `run.bat --selftest` (prueba), `run.bat --calibrar` (ver la detección), `run.bat --manual`, `run.bat --ventana`, `run.bat --descargar-modelos`.

## Uso
Botones: Reposo, Saludo, Caminar, Auto/Manual, Calibración, Pantalla. Teclas: `1` reposo · `2` saludo · `3` caminar · `M` auto/manual ·
`C` calibración (vista previa de cámara con nariz y hombros + valores) · `F11` pantalla completa/ventana · `Esc`/`Q` salir.
Si la cámara falla, está ocupada o no hay permiso, pasa sola a **modo manual** y muestra el motivo.

## Gestos de mano
Además de saludar cuando hay una persona, la mascota reacciona a gestos de **una mano**. Usa el *Gesture Recognizer*
de MediaPipe (mismo paquete `mediapipe` y misma API *Tasks* que el detector de poses; sin dependencias nuevas), en el
**mismo hilo y con el mismo fotograma** de la cámara: no se abre una segunda cámara y la interfaz no se bloquea.
Todo local; no se guardan ni envían imágenes.

| Gesto | Acción por defecto |
|---|---|
| Palma abierta | `saludo` |
| Puño cerrado | `caminar` (usa el clip `walk` de este modelo) |
| Sin mano / sin gesto reconocido | ninguna |
| Dedo arriba, pulgar arriba/abajo, victoria, te quiero | disponibles, asignados a `ninguna` |

**Modelo adicional (`gesture_recognizer.task`, unos 8 MB).** Está incluido en `assets`. No se descarga durante el uso. Si falta, recupéralo con
`run.bat --descargar-modelos` o a mano desde
https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task
(documentación: https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer/python) y guárdalo como
`assets/gesture_recognizer.task`. Si falta, los gestos se desactivan con un aviso; la detección de personas y el modo manual siguen funcionando.

**Cómo se evitan activaciones accidentales**
1. El gesto debe mantenerse estable `confirm_seconds`.
2. Entre dos acciones por gesto pasan al menos `cooldown_seconds`.
3. Tras actuar, el *mismo* gesto no se repite hasta que retires la mano (o dejes de hacer un gesto reconocido) `release_seconds`; después queda listo para el siguiente. Un gesto *distinto* puede activarse cuando acabe la espera.

**Prioridades (persona vs. gesto):** botones/teclas manuales > gesto > presencia. La presencia nunca interrumpe una
acción en curso (si hay un gesto en marcha, el saludo automático se omite). Un gesto puede interrumpir el saludo por presencia, pero
no a otra acción de gesto hasta que termine. Así las animaciones no se solapan.

El saludo se rearma cuando la cámara deja de detectar a la persona durante `lost_tolerance_seconds` (0,5 s por defecto).
Esto permite saludar de nuevo al volver a aparecer sin esperar los 4 s de `reset_seconds`, que solo controla cuándo la mascota vuelve a reposo.

**Estado en pantalla:** barra superior, p. ej. "Mano detectada: palma abierta", "Mano detectada: sin gesto reconocido" o "Sin mano".
Con `C` (calibración) se ve la cámara con los puntos de la mano, la etiqueta de MediaPipe (`Open_Palm`, `Closed_Fist`…) y su confianza.

### Ajustar en el stand (`[gestures]` en `config.toml`)
| Clave | Significado | Ajuste |
|---|---|---|
| `enabled` | activa/desactiva los gestos | `false` = solo personas |
| `min_confidence` | confianza mínima (0-1) de mano y gesto | sube a 0.7-0.8 con falsos positivos; baja a 0.4-0.5 si no reconoce |
| `confirm_seconds` | tiempo que debe mantenerse el gesto | 0.4 rápido · 0.8-1.0 más seguro |
| `cooldown_seconds` | espera entre acciones | al menos la duración del clip de saludo |
| `release_seconds` | tiempo sin gesto para poder repetir | 0.5-1.0 |
| `walk_seconds` | duración de `caminar` antes de volver a reposo | según el clip |
| `[gestures.actions]` | acción por gesto: `saludo`, `caminar`, `reposo`, `ninguna` | p. ej. `pulgar_arriba = "saludo"` |
| `[animations] caminar` | nombre del clip de caminar en el glTF/GLB | como en Blender |

Consejos: mano a 40-100 cm, palma o puño de frente a la cámara, fondo poco cargado y buena luz.

## Prueba breve
`run.bat --selftest` comprueba: lógica de saludo, de gestos y prioridades (sin hardware), lectura del glTF/GLB (animaciones/materiales), carga del modelo en una
ventana 3D oculta y apertura de cámara + detección y carga del modelo de gestos. Termina con "TODO CORRECTO" o indica qué falla.

## Configuración (`config.toml`)
| Qué | Clave |
|---|---|
| Ruta del glTF/GLB / giro si mira de lado | `[model] path`, `heading_degrees` |
| Nombres de clips | `[animations] reposo`, `saludo` (admite coincidencia parcial, sin mayúsculas) |
| Cámara | `[camera] index` (0, 1, 2…) |
| Sensibilidad | `[detection] min_shoulder_width` (más alto = hay que estar más cerca), `min_visibility` |
| Tiempo para saludar / volver a reposo | `[timing] detect_seconds`, `reset_seconds`, `lost_tolerance_seconds` (rearma tras una ausencia estable) |
| Gestos (activar, confianza, tiempos, acciones) | `[gestures]` y `[gestures.actions]` (ver Gestos de mano) |
| Pantalla completa, fuente | `[window] fullscreen`, `font` |
| Brillo | `[render] ambient`, `directional` |

## Crear o cambiar animaciones en Blender
1. Selecciona el esqueleto del modelo y abre **Dope Sheet → Action Editor**.
2. Crea acciones llamadas `reposo`, `saludo` y `caminar`; usa los huesos que tenga este modelo. El último fotograma debe coincidir con el primero en las acciones cíclicas.
3. En todas las acciones activa *Fake User* para conservarlas.
4. Exporta desde **File → Export → glTF 2.0** con **Animation** activado y el modo **Actions** (o *NLA Tracks* si preparaste pistas con esos nombres).
   Puedes exportar como glTF Embedded (`.gltf`) o GLB (`.glb`).
5. Coloca el archivo en `assets` y actualiza `[model] path` y los nombres en `[animations]` de `config.toml`.
   Ejecuta `run.bat --selftest` para revisar los clips y la carga del modelo.

## Solución de problemas
- **"No se pudo abrir la cámara"**: cierra Teams/Zoom/navegador; Configuración → Privacidad → Cámara (permitir apps de escritorio); prueba `index = 1`.
- **La cámara tarda en cerrarse**: la app conserva el hilo hasta que libere la cámara y no inicia otra captura en paralelo. Espera unos segundos; si sigue atascada, cierra y vuelve a abrir la aplicación.
- **Falla el selftest de la ventana 3D**: actualiza el driver de la tarjeta gráfica; ejecuta `.venv\Scripts\python -m pip install -U panda3d panda3d-gltf`.
- **Error instalando mediapipe**: usa Python 3.11/3.12 de 64 bits; borra `.venv` y repite `run.bat`.
- **No descarga el modelo de pose**: con internet, abre la URL de `POSE_URL` en `mascota/detector.py` y guarda el archivo en `assets/pose_landmarker_lite.task`.
- **No saluda**: usa `C` y comprueba "persona: SÍ"; baja `min_shoulder_width` o mejora la luz; se ven nariz y hombros.
- **Saluda a quien pasa lejos**: sube `min_shoulder_width` (p. ej. 0.15).
- **Modelo de espaldas/de lado**: cambia `heading_degrees`. **Colores raros**: ajusta `ambient`/`directional`.
- **Aviso "Faltan animaciones"**: los nombres no coinciden; cámbialos en `[animations]` según los clips listados.
- **"Gestos desactivados":** falta `assets/gesture_recognizer.task` (ejecuta `run.bat --descargar-modelos`) o `[gestures] enabled = false`.
- **El saludo no parece un saludo:** este modelo usa `jump` como clip provisional. Crea una acción de saludo en Blender y actualiza `[animations] saludo`.
- **Saluda/camina sin querer:** sube `min_confidence` y `confirm_seconds`. **No reacciona:** baja `min_confidence`, acerca la mano, mejora la luz y usa `C` para ver la etiqueta detectada.
- **Va lento con gestos:** sube `[detection] interval_ms` (p. ej. 250) o desactiva gestos.
- **Respaldo en la feria**: botones o teclas `1`/`2` y `--manual`; la app nunca depende de la cámara para funcionar.

## Archivos
`run.bat`, `requirements.txt`, `config.toml`, `assets/mascota.gltf`, los modelos locales de MediaPipe y `mascota/{app,detector,behavior,modelio,config,calibrate,selftest,__main__}.py`.
