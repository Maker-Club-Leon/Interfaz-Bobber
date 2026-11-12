# Componentes de terceros

El código propio de Bobber se publica bajo la [licencia MIT](LICENSE). Este archivo enumera los componentes de terceros que usa o incluye el proyecto, con su licencia y su estado de revisión. Revisado el 2026-11-12.

## Modelos incluidos en `assets/`

| Archivo | Origen | Licencia | Estado |
| --- | --- | --- | --- |
| `pose_landmarker_lite.task` | Google MediaPipe, modelo BlazePose GHUM 3D (lite) | Apache License 2.0, según su [ficha del modelo](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf) | Comprobado |
| `gesture_recognizer.task` | Google MediaPipe, Gesture Recognizer (detector de manos + clasificador de gestos) | La [ficha del clasificador](https://storage.googleapis.com/mediapipe-assets/gesture_recognizer/model_card_hand_gesture_classification_with_faireness_2022.pdf) no indica licencia | **Por confirmar** antes de redistribuirlo |
| `mascota.gltf`, `mascota.glb` | Modelo de Bobber exportado con Khronos glTF Blender I/O v1.8.19 | El archivo no declara autor ni licencia | **Por confirmar** por el club: autoría y derecho de redistribución |

Los modelos de MediaPipe proceden de `storage.googleapis.com/mediapipe-models/` (ver `mascota/detector.py`). Si no se redistribuyen, `run.bat --descargar-modelos` los descarga de esa misma fuente.

Ambas fichas de MediaPipe declaran fuera de alcance la vigilancia y el reconocimiento de identidad. Bobber respeta ese límite: solo estima presencia y gestos, y no identifica personas.

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
| `mediapipe` | 0.10.35 | Apache 2.0 |
| `numpy` (versión instalada, no fijada) | 2.5.4 | BSD-3-Clause y otras permisivas (0BSD, MIT, Zlib, CC0) |

Las ruedas de `opencv-python` incluyen FFmpeg (LGPL) y otras bibliotecas; sus avisos están en `cv2/LICENSE-3RD-PARTY.txt` dentro del paquete instalado. Esto solo importa si se distribuye una copia de `.venv` o un ejecutable empaquetado; el repositorio no lo hace.
