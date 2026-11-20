"""Exporta a Bobber a glTF (.glb) para la app, con sus animaciones reposo, saludar y caminar.

Se ejecuta con Blender (no con el Python del proyecto). Uso actual, con las animaciones que hizo
el club en Blender (una sola línea de tiempo repartida en tramos), en una sola línea:

    "C:\\Program Files\\Blender Foundation\\Blender 5.3\\blender.exe" -b --disable-autoexec
        "assets\\Saludo.Evento .blend" --python tools\\animar_bobber.py -- assets\\bobber.glb
        "tramos=saludar:1-44,caminar:44-116,reposo:116-138:idavuelta" en_el_sitio=0

Opciones tras «--»: el archivo de salida y luego
  tramos=nombre:inicio-fin[:idavuelta],...  hornea la animación del .blend por tramos.
                                            Sin esta opción se crean animaciones por código.
  en_el_sitio=0|1   1 (por defecto) quita el desplazamiento horizontal del cuerpo.
  decimate=1        proporción de polígonos de las mallas grandes (1, por defecto = sin reducir).
  luz_cara=1.7      luz con la que se calculan los colores de ojos, boca y pupilas (Material Preview).
  capas_cara=Atlas.Blanco,Pupilas,Atlas.Vacío,Atlas.Boca
                    orden de dibujo de los planos de la cara, del fondo hacia fuera: el blanco del
                    ojo, la pupila y el contorno con el párpado (hueco por dentro). Están casi
                    pegados, así que la app no puede deducirlo de la profundidad.

Qué hace, sin guardar cambios en el .blend:
1. Con «tramos»: lee fotograma a fotograma la pose del esqueleto de deformación
   («Bobber.Esqueleto», 54 huesos), que copia al rig de control Rigify («RIG-…»), y la guarda
   como una acción por tramo («hornear»). Informa de los saltos entre el final y el principio
   de cada tramo y entre tramos, para detectar bucles o transiciones bruscas.
   Sin «tramos»: crea tres acciones sencillas por código (X hacia delante, Y hacia la izquierda
   del personaje y Z hacia arriba).
2. Desconecta el esqueleto de deformación del rig y lo deja en su pose de reposo.
3. Materiales «toon» (rampas de color): glTF no puede guardar «Shader to RGB», así que en el .glb
   quedan con su color plano y, en bobber.json, su tabla de color según la luz (con la vista AgX),
   que la app usa para pintarlos como Blender. Ojos, boca y pupilas: se guarda en sus texturas el
   color que muestra Blender. Las imágenes y el .blend originales no se modifican.
4. Aplica los Shrinkwrap de la cara en reposo (solo en memoria) y exporta solo el esqueleto y las
   mallas que deforma, sin reducir polígonos salvo que se pida con «decimate».
"""
import math
import sys

import bpy
from mathutils import Quaternion, Vector

ARMATURE = "Bobber.Esqueleto"
FPS = 24
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = a[0] if a else "//bobber.glb"
    opts = {k: v for k, v in (x.split("=", 1) for x in a[1:] if "=" in x)}
    return bpy.path.abspath(out), opts


# ---------------------------------------------------------------- preparación
def prepare_armature():
    arm = bpy.data.objects[ARMATURE]
    for pb in arm.pose.bones:                   # el rig de control ya no manda
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        pb.rotation_mode = "QUATERNION"
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)
    arm.animation_data_clear()
    arm.animation_data_create()
    return arm


def apply_face_wraps(meshes):
    """Aplica los Shrinkwrap de la cara (ojos, boca, pupilas) con el esqueleto en reposo.

    En Blender esos planos se pegan a la cara en cada fotograma, después de posar el esqueleto.
    Si se dejan para la exportación, el exportador los calcula en reposo pero contra el cuerpo ya
    posado por las animaciones, y parte del plano queda por dentro de la cara (ojo a rayas).
    Aplicarlos aquí, antes de crear las animaciones y de reducir polígonos, los deja pegados a la
    cara en reposo; después siguen a la cabeza con el esqueleto como el resto de la malla."""
    def order(o):                               # las pupilas usan el plano de los ojos como apoyo
        return 1 if o.name.startswith("Pupila") else 0
    for o in sorted(meshes, key=order):
        for mod in [m for m in o.modifiers if m.type == "SHRINKWRAP"]:
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
                bpy.ops.object.modifier_apply(modifier=mod.name)
            print(f"   {o.name!r}: Shrinkwrap aplicado en reposo")


def skinned_meshes(arm):
    return [o for o in bpy.data.objects if o.type == "MESH"
            and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]


def _eval_input(sock, light):
    """Valor de una entrada de nodo: el del nodo conectado o su valor fijo."""
    if sock.is_linked:
        link = sock.links[0]
        return _eval_output(link.from_node, link.from_socket, light)
    v = sock.default_value
    return tuple(v[:3]) if hasattr(v, "__len__") else float(v)


def _as_color(v):
    if v is None:
        raise ValueError("el color depende solo de texturas")
    return v if isinstance(v, tuple) else (v, v, v)


def _eval_output(node, out, light):
    """Evalúa (simplificado) la salida de un nodo del sombreado «toon» de este modelo.

    light = color que daría «Shader to RGB»: en estos materiales el canal rojo es la luz principal
    (rampa de sombra/luz) y el verde, una segunda luz frontal."""
    t = node.type
    if t == "SHADERTORGB":
        return light
    if t == "SEPARATE_COLOR":
        c = _as_color(_eval_input(node.inputs[0], light))
        return c[{"Red": 0, "Green": 1, "Blue": 2}.get(out.name, 0)]
    if t == "VALTORGB":
        fac = _eval_input(node.inputs["Fac"], light)
        fac = fac[0] if isinstance(fac, tuple) else fac
        return tuple(node.color_ramp.evaluate(fac)[:3])
    if t == "VALUE":
        return float(node.outputs[0].default_value)
    if t == "MATH":
        vals = [_eval_input(i, light) for i in node.inputs if i.enabled][:3]
        vals = [v[0] if isinstance(v, tuple) else v for v in vals] + [0.0, 0.0]
        a, b = vals[0], vals[1]
        ops = {"ADD": a + b, "SUBTRACT": a - b, "MULTIPLY": a * b, "DIVIDE": a / b if b else 0.0,
               "GREATER_THAN": float(a > b), "LESS_THAN": float(a < b), "MAXIMUM": max(a, b),
               "MINIMUM": min(a, b), "ROUND": float(round(a)), "ABSOLUTE": abs(a),
               "COMPARE": float(abs(a - b) <= vals[2])}
        if node.operation not in ops:
            raise ValueError(f"operación Math no soportada: {node.operation}")
        return ops[node.operation]
    if t == "TEX_IMAGE":                        # texturas de expresiones: no forman el color base
        return None
    if t == "RGB":
        return tuple(node.outputs[0].default_value[:3])
    if t == "MIX":
        ins = [i for i in node.inputs if i.enabled]
        f = _eval_input(next(i for i in ins if i.name == "Factor"), light)
        f = f[0] if isinstance(f, tuple) else f
        a = _eval_input(next(i for i in ins if i.name == "A"), light)
        b = _eval_input(next(i for i in ins if i.name == "B"), light)
        if a is None or b is None:              # una rama con texturas: vale la otra entrada
            return b if a is None else a
        a, b = _as_color(a), _as_color(b)
        op = {"MULTIPLY": lambda x, y: x * y, "ADD": lambda x, y: x + y,
              "LIGHTEN": max, "DARKEN": min, "SUBTRACT": lambda x, y: x - y,
              "SCREEN": lambda x, y: 1 - (1 - x) * (1 - y)}.get(node.blend_type, lambda x, y: y)
        return tuple(x * (1 - f) + op(x, y) * f for x, y in zip(a, b))
    raise ValueError(f"nodo no soportado: {t}")


def toon_color(mat, key=1.0, fill=1.0):
    """Color que muestra un material «toon» de este modelo, evaluando su grafo de nodos.

    key = luz principal (canal rojo de «Shader to RGB»): 1 iluminado, 0 en sombra.
    fill = segunda luz (canal verde), que ilumina todo el frente del personaje. Con key=1 y
    fill=1 el resultado coincide con lo que pinta Blender en la vista frontal (comprobado
    midiendo píxeles de un render: camiseta, mofletes, peto, casco y nariz)."""
    out = next((n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
    if not out or not out.inputs["Surface"].is_linked:
        return None
    try:
        c = _as_color(_eval_input(out.inputs["Surface"], (key, fill, 0.0)))
    except (ValueError, StopIteration, KeyError) as e:
        print(f"   AVISO: no se pudo evaluar {mat.name!r} ({e}); color gris")
        return None
    return (*[min(max(v, 0.0), 1.0) for v in c], 1.0)


def display_colors(linear_colors):
    """Colores tal como los muestra Blender en pantalla (con la vista de color de la escena, p. ej.
    AgX), en sRGB 0-1. Guarda una imagen de 1 píxel por color con «save_render», que aplica la misma
    transformación que el visor, y la vuelve a leer."""
    import os
    import tempfile
    n = len(linear_colors)
    img = bpy.data.images.new("_colores", width=n, height=1, float_buffer=True, alpha=False)
    px = []
    for c in linear_colors:
        px += [c[0], c[1], c[2], 1.0]
    img.pixels = px
    path = os.path.join(tempfile.gettempdir(), "bobber_colores.png")
    scene = bpy.context.scene
    fmt = scene.render.image_settings
    old = (fmt.file_format, fmt.color_mode, fmt.color_depth)
    fmt.file_format, fmt.color_mode, fmt.color_depth = "PNG", "RGB", "8"
    try:
        img.save_render(path, scene=scene)
    finally:
        fmt.file_format, fmt.color_mode, fmt.color_depth = old
    shown = bpy.data.images.load(path)
    shown.colorspace_settings.name = "Non-Color"   # leer los valores tal cual (ya en sRGB)
    vals = list(shown.pixels)
    bpy.data.images.remove(shown); bpy.data.images.remove(img)
    os.remove(path)
    return [tuple(vals[i * 4: i * 4 + 3]) for i in range(n)]


def flatten_materials(meshes):
    """Sustituye los sombreadores «toon» por un Principled BSDF con el color que muestra Blender.

    El color se calcula evaluando el grafo del material con la luz principal y se pasa por la
    vista de color de la escena (AgX), para que el tono sea el mismo que se ve en Blender. La app
    pinta sin corrección gamma, así que se guarda ya en sRGB. Devuelve la proporción media de
    brillo en sombra (para el sombreado por bandas de la app)."""
    todo = []
    for o in meshes:
        for slot in o.material_slots:
            m = slot.material
            if not m or m in [t[0] for t in todo] or not m.use_nodes:
                continue
            if any(n.type == "BSDF_PRINCIPLED" for n in m.node_tree.nodes):
                continue                        # ya es compatible con glTF
            lit = toon_color(m) or (0.8, 0.8, 0.8, 1.0)
            dark = toon_color(m, key=0.0) or lit
            todo.append((m, lit, dark))
    if not todo:
        return None
    # Tabla de color según la luz que recibe el punto (0 a LUT_MAX), como la evalúa Blender: en
    # *Material Preview* la luz es blanca, así que «Shader to RGB» da el mismo valor en rojo y verde.
    # Las rampas de estos materiales son escalones: la tabla conserva los cortes y la app la usa en
    # su sombreador para pintar igual que Blender.
    levels = [LUT_MAX * i / (LUT_SIZE - 1) for i in range(LUT_SIZE)]
    lut_in = []
    for m, _lit, _dark in todo:
        out_node = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
        for v in levels:
            try:
                lut_in.append(_as_color(_eval_input(out_node.inputs["Surface"], (v, v, 0.0))))
            except (ValueError, StopIteration, KeyError):
                lut_in.append(_lit[:3])
    lut_out = display_colors(lut_in)
    for i, (m, _lit, _dark) in enumerate(todo):
        TOON_LUTS[m.name] = [[round(c, 4) for c in col] for col in lut_out[i * LUT_SIZE:(i + 1) * LUT_SIZE]]
    shown = display_colors([t[1] for t in todo] + [t[2] for t in todo])
    ratios = []
    for i, (m, _lit, _dark) in enumerate(todo):
        color, shadow = shown[i], shown[len(todo) + i]
        ratio = sum(shadow) / max(sum(color), 1e-6)
        if ratio < 0.99:                        # materiales que sí reciben luz
            ratios.append(ratio)
        # Solo caras exteriores (glTF «doubleSided» = false): algunas piezas con grosor, como los
        # tirantes, tienen la cara interior casi pegada a la exterior y, con el sombreado «toon»
        # de la app, las dos se pisan y salen moteadas. Los planos de la cara no pasan por aquí.
        m.use_backface_culling = True
        nodes = m.node_tree.nodes
        out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 1.0
        m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        print(f"   material {m.name!r}: color plano {tuple(round(v, 2) for v in color)}; "
              f"en sombra al {ratio:.0%}")
    return sum(ratios) / len(ratios) if ratios else None


def bake_face_textures(meshes, light):
    """Ojos, boca y pupilas como los muestra Blender: guarda en sus texturas el color ya visto.

    Son planos con una imagen (Principled BSDF). En *Material Preview* Blender los ilumina y les
    aplica la vista de color (AgX), que aclara el párpado y el iris; la app los pinta sin luz, así
    que aquí se calcula ese color para cada píxel (luz «light», medida con tu captura: 1,7) y se
    sustituye la imagen por una copia en memoria. Los PNG de assets no se tocan."""
    import os
    import tempfile
    import numpy as np
    done = {}
    for o in meshes:
        for slot in o.material_slots:
            m = slot.material
            if not (m and m.use_nodes and any(n.type == "BSDF_PRINCIPLED" for n in m.node_tree.nodes)):
                continue
            for n in m.node_tree.nodes:
                if n.type != "TEX_IMAGE" or not n.image or n.image.size[0] == 0:
                    continue
                src = n.image
                key = src.as_pointer()
                if key not in done and src not in done.values():
                    w, h = src.size
                    px = np.empty(w * h * 4, dtype=np.float32)
                    src.pixels.foreach_get(px)      # imagen de 8 bits: valores sRGB tal cual
                    px = px.reshape(-1, 4)
                    rgb = px[:, :3]
                    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
                    tmp = bpy.data.images.new("_calco", width=w, height=h, float_buffer=True, alpha=True)
                    tmp.alpha_mode = "STRAIGHT"
                    tmp.pixels.foreach_set(np.concatenate([lin * light, px[:, 3:]], axis=1).ravel())
                    path = os.path.join(tempfile.gettempdir(), f"bobber_{bpy.path.clean_name(src.name)}.png")
                    scene = bpy.context.scene
                    fmt = scene.render.image_settings
                    old = (fmt.file_format, fmt.color_mode, fmt.color_depth)
                    fmt.file_format, fmt.color_mode, fmt.color_depth = "PNG", "RGBA", "8"
                    try:
                        tmp.save_render(path, scene=scene)
                    finally:
                        fmt.file_format, fmt.color_mode, fmt.color_depth = old
                    bpy.data.images.remove(tmp)
                    shown = bpy.data.images.load(path)
                    shown.pack()                    # dentro del .glb; el archivo temporal sobra
                    os.remove(path)
                    name = src.name
                    src.name = name + ".original"   # solo en memoria: el .blend no se guarda
                    shown.name = name               # mismo nombre de textura en el .glb
                    shown.alpha_mode = src.alpha_mode
                    done[key] = shown
                    print(f"   textura {name!r}: color de Blender guardado (luz {light})")
                n.image = done.get(key, src)


def missing_texture_meshes(meshes):
    """Mallas cuyos materiales dependen de una imagen que no está disponible."""
    bad = []
    for o in meshes:
        for slot in o.material_slots:
            m = slot.material
            if not (m and m.use_nodes and any(n.type == "BSDF_PRINCIPLED" for n in m.node_tree.nodes)):
                continue
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image and not n.image.packed_file and not n.image.has_data:
                    try:
                        n.image.reload()
                    except Exception:
                        pass
                    if n.image.size[0] == 0:
                        bad.append((o, n.image.filepath))
    return bad


# ---------------------------------------------------------------- poses
def local_rot(bone, axis, degrees):
    """Rotación alrededor de un eje del personaje, expresada en el espacio local del hueso."""
    rest = bone.bone.matrix_local.to_quaternion()
    world = Quaternion(axis, math.radians(degrees))
    return rest.inverted() @ world @ rest


def combine(bone, *rots):
    """rots = [(eje, grados), ...] aplicados en orden (el primero, primero)."""
    q = Quaternion()
    for axis, deg in rots:
        q = local_rot(bone, axis, deg) @ q
    return q


class Pose(dict):
    """{hueso: [(eje, grados), ...]} más un desplazamiento vertical opcional de «Base»."""
    def __init__(self, rots=None, bob=0.0):
        super().__init__(rots or {})
        self.bob = bob


def arms_down(extra_l=(), extra_r=(), down=62):
    """Brazos bajados desde la pose en T, un poco hacia delante y con el codo algo doblado."""
    return {
        "Antebrazo.L": [(X, -down), (Z, 8)] + list(extra_l),
        "Antebrazo.R": [(X, down), (Z, -8)] + list(extra_r),
        "Brazo.L": [(Z, 12)],
        "Brazo.R": [(Z, -12)],
    }


def key_pose(arm, frame, pose):
    names = set(pose) | NEUTRAL_KEYS
    for name in names:
        pb = arm.pose.bones.get(name)
        if not pb:
            continue
        pb.rotation_quaternion = combine(pb, *pose.get(name, []))
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    base = arm.pose.bones["Base"]
    base.location = (0, pose.bob, 0)            # el eje Y local de «Base» apunta hacia arriba
    base.keyframe_insert("location", frame=frame)


def tail(phase, amp):
    """Balanceo de la cola: cada segmento algo retrasado respecto al anterior."""
    return {f"Cola.{i}": [(Z, amp * math.sin(phase - 0.6 * (i - 1)))] for i in range(1, 5)}


NEUTRAL_KEYS = {"Antebrazo.L", "Antebrazo.R", "Brazo.L", "Brazo.R", "Mano.L", "Mano.R",
                "Espina.2", "Espina.3", "Cuello", "Cabeza", "Muslo.L", "Muslo.R",
                "Pierna.L", "Pierna.R", "Tobillo.L", "Tobillo.R", "Cola.1", "Cola.2", "Cola.3", "Cola.4"}


# ---------------------------------------------------------------- acciones
def act_reposo(arm, n=72):
    """Respirar suave en bucle, con la cola balanceándose despacio."""
    for f in range(0, n + 1, 6):
        p = 2 * math.pi * f / n
        pose = arms_down(extra_l=[(Z, 2 * math.sin(p))], extra_r=[(Z, -2 * math.sin(p))])
        pose.update({"Espina.2": [(Y, 1.5 * math.sin(p))], "Espina.3": [(Y, 1.5 * math.sin(p))],
                     "Cabeza": [(X, 2.0 * math.sin(p + 1.0))]})
        pose.update(tail(p, 8))
        key_pose(arm, f + 1, Pose(pose, bob=0.05 * math.sin(p)))
    return n


def act_saludar(arm):
    """Levanta el brazo izquierdo del personaje (a la derecha del público), lo agita y lo baja."""
    keys = []
    up = [(X, 140)]                             # brazo alzado (desde bajado, ~80º sobre la horizontal)
    palm = [(Y, -90)]                           # gira la mano sobre el brazo: palma hacia el público
    keys.append((1, arms_down(), 0.0, 0))
    raised = arms_down(extra_l=up)
    raised["Mano.L"] = palm
    keys.append((10, raised, 0.06, 6))
    for i, f in enumerate(range(16, 47, 6)):    # agitar el antebrazo de lado a lado
        wave = 22 if i % 2 == 0 else -22
        pose = arms_down(extra_l=up)
        pose["Brazo.L"] = [(Z, 12), (X, wave)]
        pose["Mano.L"] = palm + [(X, wave * 0.6)]
        keys.append((f, pose, 0.06, 6))
    keys.append((56, arms_down(), 0.0, 0))
    for f, pose, bob, tilt in keys:
        pose = dict(pose)
        pose["Cabeza"] = [(X, -tilt)]           # inclina la cabeza hacia el brazo que saluda
        pose.update(tail(f / 3.0, 14))          # cola contenta
        key_pose(arm, f, Pose(pose, bob=bob))
    return 56


def act_caminar(arm, n=32):
    """Ciclo de paseo en el sitio: piernas y brazos alternos, rebote y cola."""
    for f in range(0, n + 1, 2):
        p = 2 * math.pi * f / n
        s = math.sin(p)
        lift_l, lift_r = max(0.0, math.sin(p)), max(0.0, -math.sin(p))
        pose = arms_down(extra_l=[(Y, 18 * s)], extra_r=[(Y, -18 * s)])
        pose.update({
            "Muslo.L": [(Y, -24 * s)], "Muslo.R": [(Y, 24 * s)],
            "Pierna.L": [(Y, 30 * lift_l)], "Pierna.R": [(Y, 30 * lift_r)],
            "Tobillo.L": [(Y, -10 * lift_l)], "Tobillo.R": [(Y, -10 * lift_r)],
            "Espina.3": [(Z, 4 * s)], "Cabeza": [(Z, -3 * s)],
        })
        pose.update(tail(2 * p, 10))
        key_pose(arm, f + 1, Pose(pose, bob=0.18 * abs(math.cos(p))))
    return n


EXPRESSIONS = {}      # clip -> material -> [[x, y] por fotograma]: casilla del atlas de ojos/boca
TOON_LUTS = {}        # material -> [[r, g, b] sRGB] para luz de 0 a LUT_MAX (lo que pinta Blender)
LUT_SIZE, LUT_MAX = 64, 1.2


def face_offsets():
    """Desplazamiento actual del atlas de cada material de la cara (nodo Mapping movido por drivers
    desde los controles de expresión del rig). glTF no puede animarlo; la app lo aplica."""
    out = {}
    for m in bpy.data.materials:
        if not (m.use_nodes and m.node_tree and m.node_tree.animation_data):
            continue
        if not any("Mapping" in d.data_path for d in m.node_tree.animation_data.drivers):
            continue
        mp = next((n for n in m.node_tree.nodes if n.type == "MAPPING"), None)
        if mp:
            loc = mp.inputs["Location"].default_value
            out[m.name] = [round(loc[0], 4), round(loc[1], 4)]
    return out


def write_sidecar(out, extra):
    """Escribe <modelo>.json con lo que glTF no puede guardar (expresiones de la cara, sombreado)."""
    import json
    import os
    path = os.path.splitext(out)[0] + ".json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"fps": FPS, **extra}, f, ensure_ascii=False, indent=1)
    print("DATOS EXTRA", path)


def sample_rig(arm, segments):
    """Lee la animación que ya trae el .blend (en el rig de control) sobre el esqueleto simple.

    segments = [(nombre, inicio, fin), ...]. Con las restricciones aún activas, guarda para cada
    fotograma la transformación local de cada hueso; después se quitan las restricciones y se
    crean acciones con esos valores («hornear»)."""
    scene = bpy.context.scene
    data = {}
    for name, start, end, pingpong in segments:
        frames, faces = [], []
        for f in range(start, end + 1):
            scene.frame_set(f)
            pose = {}
            for pb in arm.pose.bones:
                local = arm.convert_space(pose_bone=pb, matrix=pb.matrix, from_space="POSE", to_space="LOCAL")
                loc, rot, scl = local.decompose()
                pose[pb.name] = (loc.copy(), rot.copy(), scl.copy())
            frames.append(pose)
            faces.append(face_offsets())
        if pingpong:                            # ida y vuelta: termina igual que empieza
            frames = frames + frames[-2::-1]
            faces = faces + faces[-2::-1]
        data[name] = frames
        EXPRESSIONS[name] = {m: [fr[m] for fr in faces] for m in (faces[0] if faces else {})}
        # ¿Encaja el final con el principio? Importa para los clips que la app repite en bucle.
        jump = max(math.degrees(frames[0][b][1].rotation_difference(frames[-1][b][1]).angle) for b in frames[0])
        worst = max(frames[0], key=lambda b: frames[0][b][1].rotation_difference(frames[-1][b][1]).angle)
        print(f"   tramo {name!r}: fotogramas {start}-{end} leídos; del último al primero, "
              f"el hueso que más cambia es {worst!r} ({jump:.0f}º)")
    scene.frame_set(segments[0][1])
    fingers = ("Pulgar", "Indice", "Corazón", "Corazon", "Meñique", "Pupila", "Ctrl")
    def diff(p, q):                             # mayor giro entre dos poses, sin contar los dedos
        return max(math.degrees(p[b][1].rotation_difference(q[b][1]).angle)
                   for b in p if not b.startswith(fingers))
    names = list(data)
    for a in names:
        print(f"   del final de {a!r} al principio de: " +
              ", ".join(f"{b!r} {diff(data[a][-1], data[b][0]):.0f}º" for b in names))
    return data


def bake_actions(arm, data, in_place=True):
    """Crea una acción por tramo a partir de lo leído con sample_rig (tras prepare_armature)."""
    tracks = []
    for name, frames in data.items():
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        arm.animation_data.action = action
        base0 = frames[0]["Base"][0] if "Base" in frames[0] else None
        for i, pose in enumerate(frames, start=1):
            for bname, (loc, rot, scl) in pose.items():
                pb = arm.pose.bones[bname]
                if in_place and bname == "Base" and base0 is not None:
                    loc = loc.copy()            # en el sitio: sin desplazarse por el suelo
                    loc.x, loc.z = base0.x, base0.z  # (el eje Y local de «Base» es la altura)
                pb.location, pb.rotation_quaternion, pb.scale = loc, rot, scl
                pb.keyframe_insert("location", frame=i)
                pb.keyframe_insert("rotation_quaternion", frame=i)
                pb.keyframe_insert("scale", frame=i)
        arm.animation_data.action = None
        track = arm.animation_data.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, 1, action)
        strip.action_frame_end = len(frames)
        tracks.append((name, len(frames)))
        print(f"   acción {name!r}: {len(frames)} fotogramas ({len(frames) / FPS:.1f} s) horneada del .blend")
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    return tracks


def parse_segments(text):
    """«saludar:1-44,reposo:116-138:idavuelta» -> [("saludar", 1, 44, False), ("reposo", 116, 138, True)]

    «idavuelta»: el clip se reproduce hacia delante y luego hacia atrás, para que un bucle cuyo
    final no coincide con su principio no dé un salto al repetirse."""
    out = []
    for part in text.split(","):
        bits = part.split(":")
        a, b = bits[1].split("-")
        out.append((bits[0].strip(), int(a), int(b), len(bits) > 2 and bits[2].strip() == "idavuelta"))
    return out


def build_actions(arm):
    tracks = []
    for name, fn in (("reposo", act_reposo), ("saludar", act_saludar), ("caminar", act_caminar)):
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        arm.animation_data.action = action
        end = fn(arm)
        arm.animation_data.action = None
        track = arm.animation_data.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, 1, action)
        strip.action_frame_end = end
        tracks.append((name, end))
        print(f"   acción {name!r}: {end} fotogramas ({end / FPS:.1f} s)")
    for pb in arm.pose.bones:                   # dejar la pose de reposo para la exportación
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    return tracks


# ---------------------------------------------------------------- exportación
def export(arm, meshes, out, opts):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in [arm] + meshes:                    # un objeto oculto no se puede seleccionar ni exportar
        o.hide_set(False)
        o.hide_viewport = False
        o.select_set(True)
    if not arm.select_get():
        raise RuntimeError(f"No se pudo seleccionar {ARMATURE!r} para exportarlo")
    # Por defecto no se reduce nada: la app anima el esqueleto en la tarjeta gráfica y el modelo
    # completo va a cientos de fps. Reducir (p. ej. «decimate=0.3») estropea piezas finas como
    # los tirantes; úsalo solo si el equipo no puede animar en la tarjeta gráfica.
    ratio = float(opts.get("decimate", "1"))
    if ratio < 1.0:                             # menos polígonos: la app anima la malla en la CPU
        for o in meshes:
            if len(o.data.vertices) <= 20000:
                continue
            before = len(o.data.vertices)
            mod = o.modifiers.new("Reducir", "DECIMATE")
            mod.ratio = ratio
            # Primero en la pila y aplicado ya: se reduce la malla en reposo y se conservan los
            # grupos de vértices (pesos del esqueleto). Aplicarlo durante la exportación es muy lento.
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
                bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
                bpy.ops.object.modifier_apply(modifier=mod.name)
            if opts.get("suavizar", "1") != "0":
                # Normales suaves tras reducir: con el sombreado «toon» de la app, las normales
                # irregulares de la malla reducida hacen que el corte de luz salte de triángulo
                # en triángulo (tirantes «a rayas»).
                if o.data.has_custom_normals:
                    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
                        bpy.ops.mesh.customdata_custom_splitnormals_clear()
                o.data.shade_smooth()
            print(f"   {o.name!r}: {before} -> {len(o.data.vertices)} vértices ({ratio:.0%})")
    bpy.context.view_layer.objects.active = arm
    # El exportador importa «ctypes» solo para la compresión Draco, que no se usa. En equipos donde
    # Windows bloquea el _ctypes de Blender (Control de aplicaciones), se le da un módulo vacío
    # durante la exportación: así no se carga el archivo bloqueado ni se toca esa protección.
    import types
    stub = None
    try:
        import ctypes  # noqa: F401
    except ImportError:
        stub = types.ModuleType("ctypes")
        stub.__all__ = []
        sys.modules["ctypes"] = stub
        print("   (ctypes no disponible: exportando sin compresión Draco)")
    try:
        bpy.ops.export_scene.gltf(
            filepath=out, export_format="GLB", use_selection=True, export_apply=True,
            export_animations=True, export_animation_mode="NLA_TRACKS", export_skins=True,
            export_morph=False, export_yup=True, export_cameras=False, export_lights=False,
            export_draco_mesh_compression_enable=False)
    finally:
        if stub is not None and sys.modules.get("ctypes") is stub:
            del sys.modules["ctypes"]
    print("EXPORTADO", out)


def main():
    out, opts = args()
    bpy.context.scene.render.fps = FPS
    sampled = None
    if "tramos" in opts:                        # usar la animación que trae el .blend
        sampled = sample_rig(bpy.data.objects[ARMATURE], parse_segments(opts["tramos"]))
    arm = prepare_armature()
    meshes = skinned_meshes(arm)
    print("Mallas:", [o.name for o in meshes])
    flatten_materials(meshes)
    bake_face_textures(meshes, float(opts.get("luz_cara", "1.7")))
    missing = missing_texture_meshes(meshes)
    for o, path in missing:
        print(f"   AVISO: falta la textura {path!r}; se omite la malla {o.name!r}")
    meshes = [o for o in meshes if o not in {m for m, _ in missing}]
    apply_face_wraps(meshes)                    # en reposo y antes de crear las animaciones
    if sampled:
        bake_actions(arm, sampled, in_place=opts.get("en_el_sitio", "1") != "0")
    else:
        build_actions(arm)
    export(arm, meshes, out, opts)
    layers = [x for x in opts.get("capas_cara", "Atlas.Blanco,Pupilas,Atlas.Vacío,Atlas.Boca").split(",") if x]
    write_sidecar(out, {"expresiones": EXPRESSIONS, "capas_cara": layers,
                        "toon": {"max": LUT_MAX, "materiales": TOON_LUTS}})


main()
