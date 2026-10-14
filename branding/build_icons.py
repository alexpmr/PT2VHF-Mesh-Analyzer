"""Build Windows .ico and reference .png from the single versioned brand asset.

Run this script before PyInstaller and Inno Setup:
    python branding/build_icons.py
Pillow is a build dependency only, never required by the installed application.
"""
from __future__ import annotations

import base64
import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "mesh_analyzer_logo.png.b64"
EXPECTED_SHA256 = "42756eccfd2fca32f1de10805cb3c50a9372bbec7e95f05809791df158dd3319"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
         (96, 96), (128, 128), (256, 256)]


def build_assets() -> tuple[Path, Path]:
    raw = base64.b64decode(SOURCE.read_text(encoding="ascii").strip(), validate=True)
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Falha de integridade no logo do PT2VHF Mesh Analyzer.")
    with Image.open(BytesIO(raw)) as img:
        if img.size != (128, 128):
            raise RuntimeError("Dimensão inesperada para a imagem matriz.")
        source = img.convert("RGBA")
        canvas = source.resize((256, 256), Image.Resampling.LANCZOS)
    png_path = ROOT / "mesh-analyzer.png"
    ico_path = ROOT / "mesh-analyzer.ico"
    canvas.save(png_path, format="PNG", optimize=True)
    canvas.save(ico_path, format="ICO", sizes=SIZES)
    with Image.open(ico_path) as test:
        if test.format != "ICO" or not set(SIZES).issubset(test.ico.sizes()):
            raise RuntimeError("Ícone ICO incompleto: faltam resoluções Windows.")
    print(f"Ícone: {ico_path} / PNG: {png_path}")
    return png_path, ico_path


if __name__ == "__main__":
    build_assets()
