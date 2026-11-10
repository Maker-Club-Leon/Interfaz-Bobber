"""Inspección del GLB (sin dependencias) y carga en Panda3D."""
import json
import struct
from pathlib import Path


def inspect_glb(path: Path) -> dict:
    """Inspecciona el JSON de un GLB o glTF y enumera animaciones, huesos, materiales y texturas."""
    data = Path(path).read_bytes()
    if data[:4] == b"glTF":
        magic, _version, _length = struct.unpack("<4sII", data[:12])
        chunk_len, _ = struct.unpack("<II", data[12:20])
        j = json.loads(data[20:20 + chunk_len])
    elif Path(path).suffix.lower() == ".gltf":
        j = json.loads(data)
    else:
        raise ValueError("No es un archivo glTF/GLB válido")
    mats = []
    for m in j.get("materials", []):
        has_tex = "baseColorTexture" in m.get("pbrMetallicRoughness", {})
        mats.append((m.get("name", "?"), "textura" if has_tex else "color",
                     "KHR_materials_unlit" in m.get("extensions", {})))
    return {
        "size_mb": len(data) / 1e6,
        "animations": [a.get("name", f"anim{i}") for i, a in enumerate(j.get("animations", []))],
        "skins": len(j.get("skins", [])),
        "joints": sum(len(s["joints"]) for s in j.get("skins", [])),
        "materials": mats,
        "images": [i.get("name", "?") for i in j.get("images", [])],
    }


def resolve_clips(available, wanted: dict) -> dict:
    """Resuelve clips sin distinguir mayúsculas; devuelve nombres reales o None."""
    names = list(available)
    result = {}
    for action, aliases in wanted.items():
        if isinstance(aliases, str):
            aliases = [aliases]
        aliases = [str(alias) for alias in aliases]
        found = None
        for alias in aliases:
            found = next((name for name in names if name == alias), None)
            if found is None:
                found = next((name for name in names if name.lower() == alias.lower()), None)
            if found is None:
                found = next((name for name in names if alias.lower() in name.lower()), None)
            if found is not None:
                break
        result[action] = found
    return result


def load_model(loader, path: Path):
    """Carga un glTF/GLB con el loader plugin de panda3d-gltf."""
    import gltf
    from direct.actor.Actor import Actor
    from panda3d.core import Filename
    fn = Filename.fromOsSpecific(str(path)).getFullpath()
    try:
        actor = Actor(fn)                  # modelo con esqueleto y animaciones
        return actor, list(actor.getAnimNames())
    except Exception as e:                 # p. ej. modelo sin Character
        print("Aviso: no se cargó como Actor:", e)
        return loader.loadModel(fn), []
