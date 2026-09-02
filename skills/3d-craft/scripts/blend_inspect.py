"""Run inside Blender to produce a deterministic scene inspection report."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--scene-contract")
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rounded(values) -> list[float]:
    return [round(float(value), 6) for value in values]


def scene_bounds(objects: list[bpy.types.Object]) -> tuple[list[float], list[float], list[float]]:
    corners = []
    for obj in objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        corners.extend(obj.matrix_world @ __import__("mathutils").Vector(corner) for corner in obj.bound_box)
    if not corners:
        return [0, 0, 0], [0, 0, 0], [0, 0, 0]
    minimum = [min(point[index] for point in corners) for index in range(3)]
    maximum = [max(point[index] for point in corners) for index in range(3)]
    dimensions = [maximum[index] - minimum[index] for index in range(3)]
    return rounded(minimum), rounded(maximum), rounded(dimensions)


def inspect_mesh(obj: bpy.types.Object) -> dict:
    mesh = obj.data
    mesh.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    non_manifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.free()
    return {
        "vertices": len(mesh.vertices),
        "polygons": len(mesh.polygons),
        "triangles": len(mesh.loop_triangles),
        "non_manifold_edges": non_manifold,
        "uv_layers": [layer.name for layer in mesh.uv_layers],
        "materials": [slot.material.name for slot in obj.material_slots if slot.material],
    }


def main() -> int:
    args = arguments()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    blend_path = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    contract = {}
    if args.scene_contract:
        contract = json.loads(Path(args.scene_contract).read_text(encoding="utf-8"))
    objects = sorted(bpy.context.scene.objects, key=lambda item: item.name)
    object_rows = []
    total_triangles = 0
    non_manifold_total = 0
    unapplied = []
    for obj in objects:
        mesh = inspect_mesh(obj) if obj.type == "MESH" else None
        if mesh:
            total_triangles += mesh["triangles"]
            non_manifold_total += mesh["non_manifold_edges"]
        scale_ok = all(math.isclose(value, 1.0, abs_tol=1e-5) for value in obj.scale)
        rotation_ok = all(math.isclose(value, 0.0, abs_tol=1e-5) for value in obj.rotation_euler)
        if obj.type == "MESH" and not (scale_ok and rotation_ok):
            unapplied.append(obj.name)
        object_rows.append(
            {
                "name": obj.name,
                "type": obj.type,
                "parent": obj.parent.name if obj.parent else None,
                "location": rounded(obj.location),
                "rotation_euler": rounded(obj.rotation_euler),
                "scale": rounded(obj.scale),
                "dimensions": rounded(obj.dimensions),
                "modifiers": [modifier.type for modifier in obj.modifiers],
                "mesh": mesh,
            }
        )
    images = []
    missing_textures = []
    for image in bpy.data.images:
        if image.source != "FILE":
            continue
        resolved = Path(bpy.path.abspath(image.filepath)).resolve()
        row = {"name": image.name, "path": str(resolved), "exists": resolved.is_file()}
        images.append(row)
        if not row["exists"]:
            missing_textures.append(row)
    mesh_objects = [obj for obj in objects if obj.type == "MESH" and obj.name.startswith("GRINDER_")]
    bbox_min, bbox_max, dimensions = scene_bounds(mesh_objects)
    expected_components = contract.get("components", [])
    expected_materials = contract.get("materials", [])
    names = {obj.name.removeprefix("GRINDER_").lower().replace("-", "_") for obj in objects}
    material_names = {material.name.lower().replace("-", "_") for material in bpy.data.materials}
    missing_components = [name for name in expected_components if name.lower().replace("-", "_") not in names]
    missing_materials = [name for name in expected_materials if name.lower().replace("-", "_") not in material_names]
    expected_dimensions = contract.get("dimensions", {})
    tolerance = float(expected_dimensions.get("tolerance_percent", 5.0)) / 100.0
    expected_vector = [expected_dimensions.get("width"), expected_dimensions.get("depth"), expected_dimensions.get("height")]
    dimension_ok = all(expected is None or abs(actual - expected) <= expected * tolerance for actual, expected in zip(dimensions, expected_vector))
    failures = []
    if missing_components:
        failures.append(f"missing components: {', '.join(missing_components)}")
    if missing_materials:
        failures.append(f"missing materials: {', '.join(missing_materials)}")
    if missing_textures:
        failures.append("missing external textures")
    if unapplied:
        failures.append(f"unapplied mesh transforms: {', '.join(unapplied)}")
    if not dimension_ok:
        failures.append("scene dimensions exceed tolerance")
    report = {
        "schema": "3d-craft.blend-inspection.v1",
        "status": "PASS" if not failures else "FAIL",
        "blender_version": bpy.app.version_string,
        "blend": {"path": str(blend_path) if blend_path else None, "sha256": sha256(blend_path) if blend_path and blend_path.is_file() else None},
        "scene": {"units": bpy.context.scene.unit_settings.system, "bbox_min": bbox_min, "bbox_max": bbox_max, "dimensions": dimensions, "objects": len(objects), "meshes": len(mesh_objects), "triangles": total_triangles, "cameras": [obj.name for obj in objects if obj.type == "CAMERA"], "lights": [obj.name for obj in objects if obj.type == "LIGHT"]},
        "coverage": {"components_percent": round(100 * (len(expected_components) - len(missing_components)) / max(1, len(expected_components))), "materials_percent": round(100 * (len(expected_materials) - len(missing_materials)) / max(1, len(expected_materials))), "missing_components": missing_components, "missing_materials": missing_materials},
        "integrity": {"unapplied_mesh_transforms": unapplied, "non_manifold_edges": non_manifold_total, "missing_textures": missing_textures, "images": images, "dimension_within_tolerance": dimension_ok},
        "objects": object_rows,
        "failures": failures,
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output), "triangles": total_triangles}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
