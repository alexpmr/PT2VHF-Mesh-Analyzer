"""Native Windows desktop shell for the local Meshtastic dashboard.

No browser fallback: the application must not silently open a browser window.
"""
from __future__ import annotations

from pathlib import Path


def open_desktop_window(url: str, profile: Path) -> None:
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("Componente desktop WebView2 indisponível. Reinstale o aplicativo.") from exc

    window = webview.create_window(
        "PT2VHF Mesh Analyzer",
        url=url,
        width=1450,
        height=900,
        min_size=(950, 600),
        resizable=True,
        confirm_close=False,
    )
    if window is None:
        raise RuntimeError("Não foi possível criar a janela desktop.")
    # Runs on the main thread; returns only after the last desktop window closes.
    # Windows 11 normally includes the Evergreen WebView2 Runtime.
    try:
        webview.start(gui="edgechromium", debug=False,
                      private_mode=False, storage_path=str(profile))
    except Exception as exc:
        raise RuntimeError(
            "Falha ao iniciar WebView2. Verifique o Microsoft Edge WebView2 Runtime."
        ) from exc
