# Hoja de ruta de Bobber

## Estado actual

La aplicación de escritorio funciona como prototipo integrado: presenta la mascota, detecta presencia, reconoce gestos de una mano y ofrece modo manual. El repositorio incluye modelos, configuración, scripts de Windows, documentación y pruebas de lógica.

### Hecho

- Ventana de escritorio Panda3D con controles manuales, ventana/pantalla completa y mensajes de estado.
- Carga de glTF/GLB y reproducción de clips; el modelo activo `bobber.glb` (Bobber del club) contiene `reposo`, `saludar` y `caminar`, animados por el club en Blender (`Saludo.Evento .blend`) y exportados con `tools/animar_bobber.py`.
- Captura local OpenCV con MediaPipe Pose para estimar presencia por nariz y hombros.
- MediaPipe Gesture Recognizer conectado al mismo flujo de cámara: palma abierta → saludo; puño cerrado → caminar.
- Confirmación, cooldown y liberación de gesto para reducir activaciones accidentales.
- Prioridad de acciones para que presencia y gestos no se solapen con controles manuales.
- Modo manual de respaldo, tiempo máximo de inicio de cámara, limpieza de recursos y vista de calibración.
- Corregido el cierre de la app al caminar (tecla 3, botón o puño): faltaba el mensaje `walk`. Hay una prueba que comprueba que todos los mensajes usados tienen valor por defecto.
- Un error en una tecla, un botón, un temporizador o el bucle principal ya no cierra la app: se avisa en pantalla, se registra en la consola y la mascota vuelve a reposo. Comprobado inyectando fallos con la app sin ventana visible.
- Ayuda de gestos para el visitante: texto con los gestos disponibles y barra de «¡Mantén el gesto!» mientras se confirma uno (`[messages] hint`/`hold`).
- Modo stand: a pantalla completa se ocultan botones, cursor y estado; `C` o `F11` los muestran (`[window] hide_controls`).
- Modelos de pose y gestos incluidos en `assets`; comando para recuperarlos si faltan.
- Configuración en `config.toml`, instalación con `run.bat`, `selftest.py` y pruebas unitarias de presencia, gestos, prioridad de acciones y modelo.
- `.gitignore` con patrones para entorno Python, cachés, builds, archivos de sistema y secretos locales.

### Limitaciones conocidas

- En `caminar` los pies apenas se despegan del suelo (así está animado en Blender). El reposo dura 1,9 s y se reproduce de ida y vuelta; al empezar a saludar desde el reposo hay un pequeño cambio de postura (unos 24°).
- El modelo se exporta completo y la app lo anima en la tarjeta gráfica (más de 1000 fps en el PC de desarrollo); el `selftest` avisa si un equipo baja de 30 fps. Los materiales «toon» se pintan con las tablas de color que calcula Blender (`bobber.json`) y las expresiones de la cara cambian fotograma a fotograma como en Blender. Falta el movimiento de las pupilas (drivers de objeto).
- La aplicación está ajustada para una cámara y una mano. Los tiempos de análisis y umbrales deben calibrarse en el stand real, con su iluminación y distancia.
- El rendimiento puede variar porque pose y gesto se analizan en CPU sobre cada fotograma.
- El `selftest` y el modo de calibración necesitan acceso a la cámara; no sustituyen la prueba final en el ordenador y la cámara del stand.
- El código tiene licencia MIT y `THIRD_PARTY_NOTICES.md` recoge las licencias de terceros, pero falta confirmar el origen del modelo de pruebas actual. La licencia del clasificador de gestos de MediaPipe se deduce por indicios, sin declaración expresa de Google.
- MediaPipe está fijado en `0.10.33` porque `0.10.35` envía telemetría de uso a Google sin opción para desactivarla. Antes de actualizarlo hay que comprobar que la nueva versión no la incluye. Google no la eliminará ([#6291](https://github.com/google-ai-edge/mediapipe/issues/6291)), así que a la larga habrá que compilar MediaPipe o bloquear `play.googleapis.com`.
- La orientación (`heading_degrees = 180`) se comprobó con un render fuera de pantalla del modelo; falta verla en el monitor del stand.

## Prioridad 0 — dejar el repositorio listo para GitHub

- [x] Revisar `git status` y confirmar el estado de la rama/remoto antes de alterar el índice.
- [x] Quitar del índice `.venv` y bytecode sin borrar las copias locales (el historial actual ya no los contiene).
- [x] Confirmar que `.gitignore` cubre `.venv/`, `__pycache__/`, `*.py[cod]`, cachés, builds y `.env`.
- [ ] Decidir si se conserva en el repositorio el modelo de pruebas (`mascota.gltf`/`mascota.glb`), ahora que el activo es `bobber.glb`.
- [x] Documentar licencias y atribuciones de dependencias y modelos en `THIRD_PARTY_NOTICES.md` (`pose_landmarker_lite.task`: Apache 2.0).
- [x] Revisar la licencia de `gesture_recognizer.task`: el detector de manos es Apache 2.0 según su ficha; el clasificador, por indicios del repositorio oficial de MediaPipe (ver `THIRD_PARTY_NOTICES.md`).
- [ ] Antes de una publicación abierta o comercial, pedir confirmación a Google sobre el clasificador de gestos o dejar de incluir el `.task` en el repositorio.
- [x] Fijar los derechos del Bobber definitivo: es del club, © Maker Club León, todos los derechos reservados (fuera de la MIT).
- [ ] Confirmar el origen del modelo de pruebas actual (`mascota.gltf`/`mascota.glb`). Si no es del club y no tiene licencia que lo permita, retirarlo del repositorio público.
- [x] Elegir una licencia para el código y añadir el archivo correspondiente (MIT, `LICENSE`; no cubre `assets/`).

## Prioridad 1 — validar en las condiciones de la feria

El stand usará uno de los portátiles del club, preparado ese día y con alguien del club presente. No hace falta arranque automático ni instalación en PCs ajenos; lo importante es que ese portátil llegue preparado y que Bobber aguante horas sin intervención.

- [x] Lista de preparación del portátil (día antes y montaje) en el README: actualizar, selftest, energía, notificaciones y Windows Update.
- [x] Evitar que Windows se suspenda o apague la pantalla mientras Bobber está abierto (`[window] keep_awake`).
- [x] Reintentar la cámara automáticamente tras un fallo, sin tener que pulsar `M` (`[camera] retry_seconds`).
- [ ] Preparar el portátil concreto del stand con esa lista y repetir allí el `selftest` con la webcam que se llevará.

- [x] Instalar desde un clon limpio de GitHub con `run.bat --selftest` en el PC de desarrollo (2026-11-13): eligió Python 3.12 aunque `py` usa 3.15 por defecto, instaló `mediapipe 0.10.33` sin conflictos, ni rastro de `.venv` en Git, 31 pruebas y selftest «TODO CORRECTO» en 56 s. Los paquetes salieron de la caché de pip.
- [x] Fijar la versión exacta de todas las dependencias (23 paquetes) y exigir Python 3.12; el selftest comprueba ambas cosas. Instalación limpia verificada con `run.bat --selftest` (2026-11-13).
- [x] Ejecutar `python -m unittest discover -s tests -v` y `run.bat --selftest` en el PC de desarrollo con su webcam (2026-11-13: 26 pruebas y selftest «TODO CORRECTO»; un fotograma 640x480, persona detectada).
- [x] Abrir `run.bat --calibrar` en el PC de desarrollo: persona, palma y puño se ven bien a simple vista (2026-11-13). Falta medir la distancia de detección en el stand.
- [x] Revisar conexiones de red: MediaPipe `0.10.35` intentaba enviar telemetría; fijado `0.10.33`, sin conexiones en 17 minutos de prueba (2026-11-13).
- [ ] Probar la webcam real: permisos, cambio a manual, cierre/reintento, distancia de detección y recuperación tras ausencias.
- [ ] Calibrar iluminación, encuadre, `min_shoulder_width`, `min_visibility` y `interval_ms` en el stand.
- [ ] Probar palma y puño varias veces, y comprobar cooldown, retirada de mano y ausencia de solapamiento.
- [ ] Medir FPS/temperatura durante una sesión prolongada y ajustar intervalos o resolución si hace falta.
- [x] Definir un procedimiento de arranque y un plan manual si la cámara o el modelo fallan (README, «Procedimiento en el stand»).
- [ ] Validar ese procedimiento en el stand y completar la tabla de solución de problemas con lo que ocurra en pruebas reales.

## Prioridad 2 — mejorar la interacción

- [x] Bobber definitivo con las animaciones del club (`Saludo.Evento .blend`: saludar 1-44, caminar 44-116, reposo 116-138), horneadas y exportadas con `tools/animar_bobber.py`; `[animations]` y documentación actualizados (2026-11-19).
- [x] Expresiones de la cara animadas (ojos y boca del atlas), leídas de los drivers de Blender (2026-11-20).
- [ ] Opcional: movimiento de las pupilas y un caminar con pasos más marcados.
- [x] Añadir pruebas lógicas específicas para `GestureLogic` y `ActionArbiter` (cooldown, gesto sostenido, liberación y prioridad manual).
- [x] Fijar `heading_degrees` para que la mascota mire al público (`-90` con `bobber.glb`; era `180` con el modelo de pruebas).
- [x] Pantalla completa y ventana ajustadas a la pantalla donde está la ventana, también en TVs 4K con escalado al 300 % y con varias pantallas (comprobado con TV 3840x2160 + monitor 1920x1080, 2026-11-16).
- [x] Teclas `F12` (ayuda del personal con las teclas y los controles, sin salir de la pantalla completa) y `H` (mostrar/ocultar la ayuda de gestos).
- [x] Logo del Maker Club León como icono de la ventana y de la barra de tareas (`assets/bobber.ico`).
- [x] Ojo izquierdo «a rayas» en la app: los *Shrinkwrap* de la cara se calculaban contra el cuerpo ya posado al exportar. El script los aplica ahora en reposo (2026-11-20). El `.blend` estaba bien.
- [x] Aspecto de Blender en la app (`[render] toon`): tablas de color de cada material «toon» calculadas de su grafo de nodos con la vista AgX, luz desde arriba como en *Material Preview*, tirantes sin motas (solo caras exteriores) y ojos, boca y pupilas con el color de Blender (2026-11-20).
- [x] Fondo configurable (`[background]`): degradado con halo detrás de Bobber o una imagen a pantalla completa sin deformar (2026-11-20).
- [ ] Opcional: contorno de tinta (`[render] ink`) más limpio; el filtro de Panda3D remarca de más tirantes y casco.
- [ ] Revisar el encuadre/orientación en el monitor del stand.
- [x] Añadir una captura del modo stand al README (`docs/captura-stand.png`, render de la app sin ventana visible).
- [x] Captura del README con el Bobber definitivo.
- [ ] Opcional: vídeo corto del saludo y del paseo.
- [ ] Completar la guía de solución de problemas con lo que ocurra en pruebas reales en el stand.
- [x] Modo reclamo: la mascota alterna saludo y paseo con «¡Ven a saludarme!» tras 15 s sin nadie o tras 45 s sin interacción aunque pase gente; prioridad mínima (`[attract]`).
- [ ] Ajustar en el stand los tiempos del modo reclamo según el paso de gente.
- [x] Contador anónimo del stand: CSV local por horas con saludos, gestos, reclamos y teclas; solo números (`[stats]`, `estadisticas/` fuera de Git).
- [ ] Tras la feria, revisar el CSV para ajustar los tiempos del modo reclamo y las horas de más actividad.
- [ ] Opcional: `run-stand.bat` que reabra la app si se cierra; fondo con la marca del club y QR.

## Criterios para considerar lista una versión de feria

- Arranca en el equipo elegido sin editar código y encuentra todos los assets necesarios.
- La mascota mira al público, permanece en reposo y ejecuta un saludo real al detectar presencia o palma.
- El gesto de puño ejecuta caminar, si ese clip se conserva; una acción ausente muestra un aviso claro.
- El modo manual sigue siendo usable aunque no haya cámara o falle un reconocedor.
- Una sola cámara queda abierta y se libera al cerrar; los fotogramas no se guardan ni se transmiten.
- El repositorio no contiene entorno virtual, cachés, secretos ni archivos sin licencia revisada.
