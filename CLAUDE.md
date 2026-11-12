# Guía para Claude

Lee primero `AGENTS.md`, `README.md` y `ROADMAP.md`. Este archivo añade contexto operativo para trabajar en el proyecto Bobber.

## Objetivo del producto

Bobber es una mascota 3D local para un stand de feria. Detecta presencia y gestos de una mano con la cámara y reproduce acciones del modelo. No identifica personas y no guarda ni envía imágenes.

## Flujo actual

1. `PresenceDetector` abre la cámara una sola vez en un hilo propio.
2. Cada fotograma se analiza con MediaPipe Pose y, si está activado, con Gesture Recognizer.
3. `GreetingLogic` filtra presencia breve y rearma saludos tras ausencia confirmada.
4. `GestureLogic` exige gesto estable, aplica cooldown y espera que se libere la mano para repetir.
5. `ActionArbiter` coordina presencia, gestos y botones/teclado.
6. Panda3D muestra `assets/mascota.gltf` y reproduce sus clips.

## Detalles que no debes asumir

- El modelo activo tiene `idle`, `jump` y `walk`; `jump` se usa temporalmente como saludo, pero no es un saludo con la pata.
- `assets/mascota.glb` es una alternativa sin clips de animación.
- Palma abierta activa `saludo`; puño cerrado activa `caminar`; los demás gestos están desactivados por configuración.
- El análisis de cámara es local. No introduzcas servicios en la nube, almacenamiento de fotogramas o reconocimiento de identidad.
- Si falta un clip, presenta un aviso y conserva el control manual; no inventes animaciones ni sustituyas el modelo.

## Convenciones para cambios

- Ajustes del usuario van en `config.toml` y deben tener un valor por defecto equivalente en `mascota/config.py`.
- Respeta el ciclo de vida de la cámara: el hilo detector crea, usa y libera `VideoCapture`; los demás hilos solo solicitan que pare.
- Si falla el detector de gestos, la detección de personas debe seguir disponible y la app debe explicar el fallo.
- No añadas dependencias si la solución ya cabe en Panda3D/OpenCV/MediaPipe existentes.
- Mantén soporte para las versiones fijadas en `requirements.txt` y Windows 10/11.
- No incluyas `.venv`, cachés ni artefactos generados en commits. El índice ya no rastrea `.venv` ni `__pycache__` y `.gitignore` los excluye; `.venv` es solo local. No reescribas el historial ni cambies el remoto por iniciativa propia.

## Verificación

- Lógica: `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
- Diagnóstico con cámara/modelo: `run.bat --selftest`.
- Calibración visual: `run.bat --calibrar`.

El diagnóstico integral usa hardware. Informa qué se ejecutó y qué quedó pendiente; no atribuyas validación real de cámara si no se hizo.
