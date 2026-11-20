"""Aspecto de Blender en la app: sombreado «toon» con las tablas de color del .blend y expresiones.

tools/animar_bobber.py escribe, junto al modelo (bobber.glb -> bobber.json), lo que glTF no puede
guardar:
  - toon.materiales: para cada material «toon», su color (sRGB, ya con la vista AgX de Blender)
    según la luz que recibe el punto, de 0 a toon.max. Son escalones, como las rampas de Blender.
  - expresiones: casilla del atlas de ojos y boca (desplazamiento del Mapping) en cada fotograma
    de cada animación.

Ojos, boca y pupilas llevan en su textura el color que ya muestra Blender; la app los pinta tal
cual, sin luz (sombreador DECAL_FRAG).

En *Material Preview* de Blender la luz acompaña a la vista y viene de arriba; aquí, la luz de
cada punto es ambient + gain * (cuánto mira hacia la luz), con la luz fija respecto a la cámara,
y con ella se lee el color de la tabla. Las caras que miran abajo (bajo los mofletes, la barbilla,
el ala del casco) quedan en el escalón oscuro, como en Blender.
"""
import json
import math
from pathlib import Path

from panda3d.core import (CullBinAttrib, DepthWriteAttrib, MaterialAttrib, PNMImage, SamplerState, Shader, ShaderAttrib, Texture,
                          TextureAttrib, TransformState)

VERT = """
#version 150
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat3 p3d_NormalMatrix;
uniform mat4 p3d_TransformTable[100];
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec4 transform_weight;
in uvec4 transform_index;
out vec3 v_normal;
void main() {
    mat4 skin = p3d_TransformTable[transform_index.x] * transform_weight.x
              + p3d_TransformTable[transform_index.y] * transform_weight.y
              + p3d_TransformTable[transform_index.z] * transform_weight.z
              + p3d_TransformTable[transform_index.w] * transform_weight.w;
    gl_Position = p3d_ModelViewProjectionMatrix * (skin * p3d_Vertex);
    v_normal = p3d_NormalMatrix * (mat3(skin) * p3d_Normal);
}
"""

FRAG = """
#version 150
uniform sampler2D lut;
uniform vec3 light;            // x = luz ambiente, y = ganancia de la luz direccional, z = máximo de la tabla
uniform vec3 light_dir;        // hacia la luz, en coordenadas de la cámara (z = hacia la cámara)
in vec3 v_normal;
out vec4 p3d_FragColor;
void main() {
    float facing = clamp(dot(normalize(v_normal), light_dir), 0.0, 1.0);   // 1 = de cara a la luz
    float level = clamp(light.x + light.y * facing, 0.0, light.z);
    p3d_FragColor = vec4(texture(lut, vec2(level / light.z, 0.5)).rgb, 1.0);
}
"""


DECAL_VERT = """
#version 150
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_TextureMatrix[1];
uniform mat4 p3d_TransformTable[100];
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec4 transform_weight;
in uvec4 transform_index;
out vec2 v_uv;
void main() {
    mat4 skin = p3d_TransformTable[transform_index.x] * transform_weight.x
              + p3d_TransformTable[transform_index.y] * transform_weight.y
              + p3d_TransformTable[transform_index.z] * transform_weight.z
              + p3d_TransformTable[transform_index.w] * transform_weight.w;
    gl_Position = p3d_ModelViewProjectionMatrix * (skin * p3d_Vertex);
    v_uv = (p3d_TextureMatrix[0] * vec4(p3d_MultiTexCoord0, 0.0, 1.0)).xy;   // casilla del atlas
}
"""

DECAL_FRAG = """
#version 150
uniform sampler2D p3d_Texture0;
in vec2 v_uv;
out vec4 p3d_FragColor;
void main() {
    vec4 c = texture(p3d_Texture0, v_uv);
    // La textura es sRGB y la tarjeta la pasa a lineal al leerla; la ventana no corrige gamma,
    // así que se vuelve a sRGB para pintar exactamente el color guardado.
    vec3 s = mix(c.rgb * 12.92, 1.055 * pow(c.rgb, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c.rgb));
    p3d_FragColor = vec4(s, c.a);
}
"""


def load_sidecar(model_path):
    """Datos extra del modelo (bobber.json) o {} si no existen."""
    p = Path(model_path).with_suffix(".json")
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _lut_texture(colors):
    img = PNMImage(len(colors), 1, 3)
    for i, (r, g, b) in enumerate(colors):
        img.setXel(i, 0, r, g, b)
    tex = Texture("lut")
    tex.load(img)
    tex.setMinfilter(SamplerState.FT_nearest)       # escalones nítidos, como las rampas de Blender
    tex.setMagfilter(SamplerState.FT_nearest)
    tex.setWrapU(SamplerState.WM_clamp)
    return tex


def _geoms(model):
    """(nodo, índice de geometría, estado) de cada geometría del modelo."""
    for np_ in model.findAllMatches("**/+GeomNode"):
        node = np_.node()
        for i in range(node.getNumGeoms()):
            yield np_, i, node.getGeomState(i)


def light_direction(heading, pitch):
    """Dirección hacia la luz en coordenadas de la cámara. heading 0 y pitch 0 = desde la cámara;
    pitch negativo = desde arriba; heading positivo = desde la derecha de la imagen."""
    h, p = math.radians(heading), math.radians(pitch)
    return (math.sin(h) * math.cos(p), -math.sin(p), math.cos(h) * math.cos(p))


def apply_toon(model, sidecar, ambient, gain, heading=0.0, pitch=0.0):
    """Aplica el sombreador «toon» a las geometrías cuyos materiales tienen tabla. Devuelve cuántas."""
    toon = sidecar.get("toon", {})
    luts = toon.get("materiales", {})
    if not luts:
        return 0
    shader = Shader.make(Shader.SL_GLSL, VERT, FRAG)
    textures = {name: _lut_texture(colors) for name, colors in luts.items()}
    done = 0
    for np_, i, state in _geoms(model):
        mat = state.getAttrib(MaterialAttrib)
        name = mat.getMaterial().getName() if mat and mat.getMaterial() else None
        if name not in textures:
            continue
        attr = ShaderAttrib.make(shader).setFlag(ShaderAttrib.F_hardware_skinning, True)
        attr = attr.setShaderInput("lut", textures[name])
        attr = attr.setShaderInput("light", (float(ambient), float(gain), float(toon.get("max", 1.0))))
        attr = attr.setShaderInput("light_dir", light_direction(heading, pitch))
        np_.node().setGeomState(i, state.setAttrib(attr, 1))
        done += 1
    return done


def apply_decals(model, sidecar, skip=()):
    """Pinta sin luz las geometrías con textura (ojos, boca, pupilas). Devuelve cuántas.

    Son planos casi pegados entre sí (blanco del ojo, pupila, contorno con párpado): se dibujan
    después del cuerpo, en el orden de «capas_cara» y sin escribir profundidad, así ninguno tapa
    al siguiente por un error de profundidad, pero el cuerpo (mofletes, nariz) sí los tapa."""
    shader = Shader.make(Shader.SL_GLSL, DECAL_VERT, DECAL_FRAG)
    layers = list(sidecar.get("capas_cara", []))
    done = 0
    for np_, i, state in _geoms(model):
        mat = state.getAttrib(MaterialAttrib)
        name = mat.getMaterial().getName() if mat and mat.getMaterial() else None
        tex = state.getAttrib(TextureAttrib)
        if name in skip or not tex or tex.getNumOnStages() == 0:
            continue
        attr = ShaderAttrib.make(shader).setFlag(ShaderAttrib.F_hardware_skinning, True)
        order = layers.index(name) if name in layers else len(layers)
        state = state.setAttrib(attr, 1).setAttrib(CullBinAttrib.make("fixed", order), 1)
        if layers:
            state = state.setAttrib(DepthWriteAttrib.make(DepthWriteAttrib.M_off), 1)
        np_.node().setGeomState(i, state)
        done += 1
    return done


class Expressions:
    """Cambia la casilla del atlas de ojos y boca según la animación y el fotograma en curso."""

    def __init__(self, model, sidecar):
        self.model = model
        self.clips = sidecar.get("expresiones", {})
        self.targets = {}           # material -> [(nodo, etapa de textura)]
        for np_, _i, state in _geoms(model):
            mat = state.getAttrib(MaterialAttrib)
            name = mat.getMaterial().getName() if mat and mat.getMaterial() else None
            tex = state.getAttrib(TextureAttrib)
            if not name or not tex or tex.getNumOnStages() == 0:
                continue
            if any(name in mats for mats in self.clips.values()):
                self.targets.setdefault(name, []).append((np_, tex.getOnStage(0)))
        self._last = {}

    def __bool__(self):
        return bool(self.targets)

    def update(self):
        anim = self.model.getCurrentAnim()
        if anim not in self.clips:
            return
        frames = max(self.model.getNumFrames(anim) - 1, 1)
        t = min(max(self.model.getCurrentFrame(anim) / frames, 0.0), 1.0)
        for name, offsets in self.clips[anim].items():
            if not offsets or name not in self.targets:
                continue
            x, y = offsets[round(t * (len(offsets) - 1))]
            if self._last.get(name) == (x, y):
                continue
            self._last[name] = (x, y)
            for np_, stage in self.targets[name]:
                # Mismo desplazamiento que el nodo Mapping de Blender (las UV de Panda3D coinciden
                # con las de Blender tras la conversión de glTF).
                np_.setTexTransform(stage, TransformState.makePos2d((x, y)))
