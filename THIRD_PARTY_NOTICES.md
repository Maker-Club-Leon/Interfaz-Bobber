# Componentes de terceros

El código propio de Bobber se publica bajo la [licencia MIT](LICENSE). Este archivo enumera los componentes de terceros que usa o incluye el proyecto, con su licencia y su estado de revisión. Revisado el 2026-11-12.

## Modelos incluidos en `assets/`

| Archivo | Origen | Licencia | Estado |
| --- | --- | --- | --- |
| `pose_landmarker_lite.task` | Google MediaPipe, modelo BlazePose GHUM 3D (lite) | Apache License 2.0, según su [ficha del modelo](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf) | Comprobado |
| `gesture_recognizer.task` | Google MediaPipe, Gesture Recognizer. Contiene `hand_landmarker.task` (detector y seguimiento de manos) y `hand_gesture_recognizer.task` (clasificador de gestos) | Apache License 2.0 (ver nota) | Comprobado el detector de manos; el clasificador, por indicios |
| `mascota.gltf`, `mascota.glb` | Modelo **de pruebas**, provisional hasta tener el Bobber definitivo con sus animaciones. Exportado con Khronos glTF Blender I/O v1.8.19 | El archivo no declara autor ni licencia | **Origen por confirmar**: no consta si lo hizo el club o un tercero |

### Modelo de Bobber

El personaje Bobber y sus modelos 3D son de Maker Club León: © 2026 Maker Club León, todos los derechos reservados. La licencia MIT del código no los cubre. Se incluyen en el repositorio para que la aplicación funcione, pero no se concede permiso para reutilizarlos fuera de este proyecto sin autorización del club.

Mientras no se confirme el origen del modelo de pruebas actual, esta sección se aplica solo al Bobber definitivo.

Los modelos de MediaPipe proceden de `storage.googleapis.com/mediapipe-models/` (ver `mascota/detector.py`). Si no se redistribuyen, `run.bat --descargar-modelos` los descarga de esa misma fuente.

Nota sobre `gesture_recognizer.task`:

- **Detector y seguimiento de manos:** la [ficha de MediaPipe Hands](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Hand%20Tracking%20(Lite_Full)%20with%20Fairness%20Oct%202021.pdf) indica expresamente «Apache License, Version 2.0».
- **Clasificador de gestos:** su [ficha](https://storage.googleapis.com/mediapipe-assets/gesture_recognizer/model_card_hand_gesture_classification_with_faireness_2022.pdf) no menciona licencia. Aun así, el repositorio oficial [google-ai-edge/mediapipe](https://github.com/google-ai-edge/mediapipe) (Apache-2.0) declara sus pesos (`canned_gesture_classifier.tflite`, `gesture_embedder.tflite`) en `mediapipe/model_maker/models/gesture_recognizer/BUILD`, con cabecera Apache 2.0 y `licenses(["notice"])`.
- **Conclusión:** es coherente con Apache 2.0, pero Google no lo declara de forma expresa para este archivo. Para una distribución comercial o pública conviene pedir confirmación a Google o no incluir el archivo en el repositorio y descargarlo con `run.bat --descargar-modelos`.

Las fichas de MediaPipe declaran fuera de alcance la vigilancia y el reconocimiento de identidad. Bobber respeta ese límite: solo estima presencia y gestos, y no identifica personas.

Atribución de BlazePose, tal como pide su ficha:

- Bazarevsky, V., Grishchenko, I. *et al.* «BlazePose: On-device Real-time Body Pose tracking», CVPR Workshop on Computer Vision for Augmented and Virtual Reality, 2020.
- Xu, H., Bazavan, E. G. *et al.* «GHUM & GHUML: Generative 3D Human Shape and Articulated Pose Models», CVPR 2020.

## Dependencias de Python

No se incluyen en el repositorio; `run.bat` las instala en `.venv` desde PyPI. Licencias leídas de los metadatos de los paquetes instalados (versiones de `requirements.txt`):

| Paquete | Versión | Licencia |
| --- | --- | --- |
| `panda3d` | 1.10.16 | BSD modificada (3 cláusulas) |
| `panda3d-gltf` | 1.3.0 | BSD-3-Clause |
| `panda3d-simplepbr` (dependencia de `panda3d-gltf`) | 0.13.1 | BSD-3-Clause |
| `opencv-python` | 5.0.0.93 | Apache 2.0 |
| `opencv-contrib-python` (dependencia de `mediapipe`) | 5.0.0.93 | Apache 2.0 |
| `mediapipe` | 0.10.33 | Apache 2.0 |
| `numpy` (versión instalada, no fijada) | 2.5.4 | BSD-3-Clause y otras permisivas (0BSD, MIT, Zlib, CC0) |

Las ruedas de `opencv-python` incluyen FFmpeg (LGPL) y otras bibliotecas; sus avisos están en `cv2/LICENSE-3RD-PARTY.txt` dentro del paquete instalado. Esto solo importa si se distribuye una copia de `.venv` o un ejecutable empaquetado; el repositorio no lo hace.
