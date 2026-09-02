"""Render deterministic fixed-view evidence from the currently opened Blender file."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--resolution", type=int, default=768)
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def point_camera(camera: bpy.types.Object, position: tuple[float, float, float], target: Vector) -> None:
    camera.location = position
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def build_contact_sheet(paths: list[Path], output: Path, thumb: int = 256) -> None:
    loaded = []
    try:
        for path in paths:
            image = bpy.data.images.load(str(path), check_existing=False)
            image.scale(thumb, thumb)
            loaded.append(image)
        width, height = thumb * 3, thumb * 2
        pixels = [0.0] * (width * height * 4)
        for index, image in enumerate(loaded):
            source = list(image.pixels[:])
            column, row = index % 3, 1 - index // 3
            for y in range(thumb):
                src_start = y * thumb * 4
                dst_start = ((row * thumb + y) * width + column * thumb) * 4
                pixels[dst_start : dst_start + thumb * 4] = source[src_start : src_start + thumb * 4]
        sheet = bpy.data.images.new("3D_Craft_Contact_Sheet", width=width, height=height, alpha=True)
        sheet.pixels[:] = pixels
        sheet.filepath_raw = str(output)
        sheet.file_format = "PNG"
        sheet.save()
        bpy.data.images.remove(sheet)
    finally:
        for image in loaded:
            bpy.data.images.remove(image)


def main() -> int:
    args = arguments()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.91, 0.90, 0.87)
    camera = bpy.data.objects.get("Camera_Evidence")
    if not camera:
        camera_data = bpy.data.cameras.new("Camera_Evidence")
        camera = bpy.data.objects.new("Camera_Evidence", camera_data)
        scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.42
    target = Vector((0.0, 0.0, 0.16))
    positions = {
        "front": (0.0, -1.0, 0.16),
        "back": (0.0, 1.0, 0.16),
        "left": (-1.0, 0.0, 0.16),
        "right": (1.0, 0.0, 0.16),
        "top": (0.0, 0.0, 1.1),
    }
    rendered: list[Path] = []
    metadata = []
    for name, position in positions.items():
        point_camera(camera, position, target)
        path = output_dir / f"{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        rendered.append(path)
        metadata.append({"view": name, "path": str(path), "sha256": sha256(path), "camera_location": [round(value, 6) for value in camera.location], "camera_rotation": [round(value, 6) for value in camera.rotation_euler], "camera_type": "ORTHO", "ortho_scale": camera.data.ortho_scale})
    camera.data.type = "PERSP"
    camera.data.lens = 70
    point_camera(camera, (0.48, -0.62, 0.42), target)
    perspective = output_dir / "perspective.png"
    scene.render.filepath = str(perspective)
    bpy.ops.render.render(write_still=True)
    rendered.append(perspective)
    metadata.append({"view": "perspective", "path": str(perspective), "sha256": sha256(perspective), "camera_location": [round(value, 6) for value in camera.location], "camera_rotation": [round(value, 6) for value in camera.rotation_euler], "camera_type": "PERSP", "lens": camera.data.lens})
    contact_sheet = output_dir / "contact-sheet.png"
    build_contact_sheet(rendered, contact_sheet)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output_dir / "lookdev-perspective.png")
    bpy.ops.render.render(write_still=True)
    lookdev = output_dir / "lookdev-perspective.png"
    report = {
        "schema": "3d-craft.render-evidence.v1",
        "status": "PASS",
        "blender_version": bpy.app.version_string,
        "renderers": {"structure": "BLENDER_WORKBENCH", "lookdev": "BLENDER_EEVEE"},
        "resolution": [args.resolution, args.resolution],
        "views": metadata,
        "contact_sheet": {"path": str(contact_sheet), "sha256": sha256(contact_sheet), "dimensions": [768, 512]},
        "lookdev": {"path": str(lookdev), "sha256": sha256(lookdev)},
    }
    report_path = output_dir / "render-evidence.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(report_path), "views": len(metadata)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
