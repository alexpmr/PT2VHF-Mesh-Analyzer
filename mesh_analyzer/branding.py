"""Single source of truth for the offline PT2VHF Mesh Analyzer brand image."""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from pathlib import Path

SHA256 = "42756eccfd2fca32f1de10805cb3c50a9372bbec7e95f05809791df158dd3319"
IMAGE = Path(__file__).resolve().parent.parent / "branding" / "mesh_analyzer_logo.png.b64"


@lru_cache(maxsize=1)
def brand_image_data_uri() -> str:
    text = IMAGE.read_text(encoding="ascii").strip()
    raw = base64.b64decode(text, validate=True)
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise RuntimeError("Logo PT2VHF Mesh Analyzer com integridade inválida.")
    return "data:image/png;base64," + text
