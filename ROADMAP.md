# Hoja de ruta de Bobber

## Estado actual

La aplicación de escritorio funciona como prototipo integrado: presenta la mascota, detecta presencia, reconoce gestos de una mano y ofrece modo manual. El repositorio incluye modelos, configuración, scripts de Windows, documentación y pruebas de lógica.

### Hecho

- Ventana de escritorio Panda3D con controles manuales, ventana/pantalla completa y mensajes de estado.
- Carga de glTF/GLB y reproducción de clips; el archivo activo `mascota.gltf` contiene `idle`, `jump` y `walk`.
- Captura local OpenCV con MediaPipe Pose para estimar presencia por nariz y hombros.
- MediaPipe Gesture Recognizer conectado al mismo flujo de cámara: palma abierta → saludo; puño cerrado → caminar.
- Confirmación, cooldown y liberación de gesto para reducir activaciones accidentales.
- Prioridad de acciones para que presencia y gestos no se solapen con controles manuales.
- Modo manual de respaldo, tiempo máximo de inicio de cámara, limpieza de recursos y vista de calibración.
- Modelos de pose y gestos incluidos en `assets`; comando para recuperarlos si faltan.
- Configuración en `config.toml`, instalación con `run.bat`, `selftest.py` y pruebas unitarias de presencia, gestos, prioridad de acciones y modelo.
- `.gitignore` con patrones para entorno Python, cachés, builds, archivos de sistema y secretos locales.

### Limitaciones conocidas

- `jump` es un salto que se usa como saludo provisional. Falta crear/exportar una animación real `saludo` (por ejemplo, levantar y mover la pata).
- La aplicación está ajustada para una cámara y una mano. Los tiempos de análisis y umbrales deben calibrarse en el stand real, con su iluminación y distancia.
- El rendimiento puede variar porque pose y gesto se analizan en CPU sobre cada fotograma.
- El `selftest` y el modo de calibración necesitan acceso a la cámara; no sustituyen la prueba final en el ordenador y la cámara del stand.
- El código tiene licencia MIT y `THIRD_PARTY_NOTICES.md` recoge las licencias de terceros, pero falta confirmar el origen del modelo de pruebas actual. La licencia del clasificador de gestos de MediaPipe se deduce por indicios, sin declaración expresa de Google.
- `mascota.gltf` es un modelo de pruebas; el Bobber definitivo, con sus animaciones, está pendiente.
- La orientación (`heading_degrees = 180`) se comprobó con un render fuera de pantalla del modelo; falta verla en el monitor del stand.

## Prioridad 0 — dejar el repositorio listo para GitHub

- [x] Revisar `git status` y confirmar el estado de la rama/remoto antes de alterar el índice.
- [x] Quitar del índice `.venv` y bytecode sin borrar las copias locales (el historial actual ya no los contiene).
- [x] Confirmar que `.gitignore` cubre `.venv/`, `__pycache__/`, `*.py[cod]`, cachés, builds y `.env`.
- [ ] Decidir si se publican ambos modelos. `mascota.gltf` es el activo; `mascota.glb` es una alternativa sin animaciones.
- [x] Documentar licencias y atribuciones de dependencias y modelos en `THIRD_PARTY_NOTICES.md` (`pose_landmarker_lite.task`: Apache 2.0).
- [x] Revisar la licencia de `gesture_recognizer.task`: el detector de manos es Apache 2.0 según su ficha; el clasificador, por indicios del repositorio oficial de MediaPipe (ver `THIRD_PARTY_NOTICES.md`).
- [ ] Antes de una publicación abierta o comercial, pedir confirmación a Google sobre el clasificador de gestos o dejar de incluir el `.task` en el repositorio.
- [x] Fijar los derechos del Bobber definitivo: es del club, © Maker Club León, todos los derechos reservados (fuera de la MIT).
- [ ] Confirmar el origen del modelo de pruebas actual (`mascota.gltf`/`mascota.glb`). Si no es del club y no tiene licencia que lo permita, retirarlo del repositorio público.
- [x] Elegir una licencia para el código y añadir el archivo correspondiente (MIT, `LICENSE`; no cubre `assets/`).

## Prioridad 1 — validar en las condiciones de la feria

- [ ] Instalar desde cero en un PC Windows limpio usando solo el README y `run.bat`.
- [ ] Ejecutar `python -m unittest discover -s tests -v` y `run.bat --selftest`.
- [ ] Probar la webcam real: permisos, cambio a manual, cierre/reintento, distancia de detección y recuperación tras ausencias.
- [ ] Calibrar iluminación, encuadre, `min_shoulder_width`, `min_visibility` y `interval_ms` en el stand.
- [ ] Probar palma y puño varias veces, y comprobar cooldown, retirada de mano y ausencia de solapamiento.
- [ ] Medir FPS/temperatura durante una sesión prolongada y ajustar intervalos o resolución si hace falta.
- [x] Definir un procedimiento de arranque y un plan manual si la cámara o el modelo fallan (README, «Procedimiento en el stand»).
- [ ] Validar ese procedimiento en el stand y completar la tabla de solución de problemas con lo que ocurra en pruebas reales.

## Prioridad 2 — mejorar la interacción

- [ ] Crear y exportar clips reales `saludo` y `reposo` en Blender; mantener `walk` para el gesto de puño.
- [ ] Actualizar `[animations]` y la documentación cuando los clips nuevos estén dentro del modelo.
- [x] Añadir pruebas lógicas específicas para `GestureLogic` y `ActionArbiter` (cooldown, gesto sostenido, liberación y prioridad manual).
- [x] Fijar `heading_degrees` para que la mascota mire al público (`180` con `mascota.gltf`).
- [ ] Revisar el encuadre/orientación en el monitor del stand.
- [ ] Preparar una captura o vídeo corto para el README y una guía de solución de problemas basada en pruebas reales.

## Criterios para considerar lista una versión de feria

- Arranca en el equipo elegido sin editar código y encuentra todos los assets necesarios.
- La mascota mira al público, permanece en reposo y ejecuta un saludo real al detectar presencia o palma.
- El gesto de puño ejecuta caminar, si ese clip se conserva; una acción ausente muestra un aviso claro.
- El modo manual sigue siendo usable aunque no haya cámara o falle un reconocedor.
- Una sola cámara queda abierta y se libera al cerrar; los fotogramas no se guardan ni se transmiten.
- El repositorio no contiene entorno virtual, cachés, secretos ni archivos sin licencia revisada.
