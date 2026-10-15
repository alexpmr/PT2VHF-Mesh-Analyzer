"""Native Windows desktop shell for the local Meshtastic dashboard.

No browser fallback: the application must not silently open a browser window.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys


def native_window_icon() -> Path | None:
    """Find the actual Windows ICO used by pywebview WinForms.

    The PE icon alone does not necessarily become the native WebView2 window icon.
    PyInstaller --onefile extracts --add-data files under sys._MEIPASS.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    # Inno Setup copies this icon to an installed, stable path shared by
    # Desktop/Start shortcuts. Point the WebView2 host there too when present:
    # a PyInstaller onefile _MEIPASS path changes on every launch.
    if getattr(sys, "frozen", False):
        stable = Path(sys.executable).resolve().parent / "branding" / "mesh-analyzer.ico"
        if stable.is_file():
            return stable
    icon = base / "branding" / "mesh-analyzer.ico"
    if icon.is_file():
        return icon
    if getattr(sys, "frozen", False):
        raise RuntimeError(
            "Ícone nativo PT2VHF ausente do pacote Windows. "
            "Reinstale uma versão que inclua branding/mesh-analyzer.ico."
        )
    # Source checkout: branding/build_icons.py may not have been run yet.
    return None


def open_desktop_window(url: str, profile: Path) -> None:
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("Componente desktop WebView2 indisponível. Reinstale o aplicativo.") from exc

    # Keep the running WebView2 window grouped with the installed Start-menu
    # and desktop shortcuts, not with Python/Edge.
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "PT2VHF.MeshAnalyzer")
        except (AttributeError, OSError):
            pass  # The branded EXE resource still supplies the taskbar icon.

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
        icon_path = native_window_icon() if os.name == "nt" else None
        webview.start(gui="edgechromium", debug=False,
                      private_mode=False, storage_path=str(profile),
                      icon=str(icon_path) if icon_path else None)
    except Exception as exc:
        raise RuntimeError(
            "Falha ao iniciar WebView2. Verifique o Microsoft Edge WebView2 Runtime."
        ) from exc
