# Instrucciones para agentes y colaboradores

## Propósito

Este repositorio contiene **Bobber**, una aplicación Python de escritorio para mostrar una mascota 3D en un stand y hacerla reaccionar a la presencia de personas y a gestos de mano. El proyecto no pretende identificar personas.

Antes de cambiar código, lee `README.md`, `ROADMAP.md`, `config.toml` y los módulos afectados. Mantén los cambios dentro de este repositorio.

## Arquitectura

- `mascota/app.py`: ventana Panda3D, modelo, clips, interfaz, estado de la aplicación y coordinación de acciones.
- `mascota/detector.py`: captura OpenCV, MediaPipe Pose y Gesture Recognizer. Un único hilo posee la cámara y ejecuta ambos reconocedores sobre el mismo fotograma.
- `mascota/behavior.py`: lógica temporal de presencia, confirmación/rearme de gestos y prioridad de acciones.
- `mascota/config.py` y `config.toml`: valores por defecto y ajustes editables del stand. Mantén sus opciones coherentes.
- `mascota/modelio.py`: lectura y carga de `.gltf`/`.glb` y resolución de clips.
- `mascota/calibrate.py`: diagnóstico visual de cámara, pose y mano.
- `mascota/selftest.py` y `tests/test_logic.py`: diagnósticos y pruebas.

El modelo activo es `assets/mascota.gltf`; sus clips son `idle`, `jump` y `walk`. La configuración asigna `jump` al saludo de forma provisional. El archivo `assets/mascota.glb` no tiene animaciones. No afirmes que `jump` es un saludo con la pata ni inventes clips del modelo.

## Reglas de producto y privacidad

- El vídeo debe permanecer local. No guardar ni enviar fotogramas, no añadir identificación o reconocimiento de identidad.
- No abrir una segunda cámara. `PresenceDetector` es dueño de `VideoCapture`; solicita `stop()`, espera el cierre del hilo y libera todos los recursos en `finally`.
- Si la cámara falla, conserva el modo manual y muestra un mensaje que ayude a recuperarla.
- Respeta la prioridad implementada: controles manuales > gestos > presencia. Evita que dos acciones de mascota se solapen.
- Mantén configurables umbrales y tiempos; no hardcodees ajustes del stand cuando exista una opción en `config.toml`.
- Conserva los modelos y materiales originales. No reemplaces la mascota por una imagen ni conviertas el modelo sin necesidad.

## Dependencias y Windows

- Requisitos probados/documentados: Windows 10/11, Python 3.12 de 64 bits (numpy y contourpy fijados exigen 3.12). `requirements.txt` fija la versión exacta de todas las dependencias, directas e indirectas; si cambias una, prueba en un `.venv` nuevo y mantén la lista completa.
- No cambies versiones, APIs de MediaPipe o formato de exportación sin comprobar la compatibilidad con Windows y actualizar README e instrucciones.
- MediaPipe está fijado en `0.10.33` porque `0.10.35` envía telemetría a `play.googleapis.com` sin opción para desactivarla. No lo actualices sin comprobar que la nueva rueda no contiene `clearcut`/`play.googleapis.com` y sin una prueba de red de más de 16 minutos.
- Los modelos de MediaPipe están en `assets`. La descarga explícita se hace con `run.bat --descargar-modelos`; el análisis normal no debe necesitar internet si existen los modelos.
- No añadas `.venv`, `__pycache__`, `.pyc`, secretos o artefactos de compilación al control de versiones. `.gitignore` los excluye y el índice ya no rastrea `.venv` ni `__pycache__`; `.venv` debe quedarse solo en local. Antes de hacer commit, revisa `git status` para que no vuelvan a colarse.

## Pruebas y comprobaciones

- Para lógica sin hardware: `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
- `run.bat --selftest` es una prueba más amplia que puede usar cámara y render 3D; úsala solo cuando ese hardware esté disponible y pueda reservarse.
- Para calibración manual: `run.bat --calibrar`.
- Describe con precisión qué se comprobó. No digas que la cámara, la pantalla completa o el rendimiento de feria funcionan si no se probaron en Windows real.

## Documentación y cambios

- Mantén `README.md` como guía para usuarios y `ROADMAP.md` como lista de estado/pendientes.
- Actualiza `config.py` y `config.toml` juntos si añades un ajuste.
- Actualiza `tests` o `selftest` cuando cambie lógica relevante; explica los casos importantes.
- No borres assets grandes ni cambies `.gitignore`, el índice Git o el remoto por iniciativa propia. Antes de publicar, consulta licencias y atribución de los modelos.
