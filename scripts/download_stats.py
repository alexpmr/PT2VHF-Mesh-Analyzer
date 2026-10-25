"""Contador de downloads por tipo de build (#210), para os selos do README.

Os releases antigos são apagados a cada versão (retain_latest_release.py), então o
contador do GitHub zeraria. Aqui o histórico fica num JSON (`state.json`): para cada
versão e arquivo guarda o maior número já visto. Os totais por tipo somam esse
histórico e viram arquivos "endpoint" do shields.io (um por tipo).

Uso: python scripts/download_stats.py <pasta>   (lê e grava <pasta>/state.json e <pasta>/*.json)
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPOSITORY = "alexpmr/PT2VHF-Mesh-Analyzer"
TYPES = (
    ("windows-setup", "Windows · instalador", re.compile(r"Setup-.*\.exe$", re.I)),
    ("windows-portable-exe", "Windows · portable", re.compile(r"(Portable-.*\.exe|^PT2VHF-Mesh-Analyzer\.exe)$", re.I)),
    ("windows-portable-zip", "Windows · ZIP", re.compile(r"Portable-.*\.zip$", re.I)),
    ("macos-arm64", "macOS Apple Silicon", re.compile(r"macOS-arm64\.dmg$", re.I)),
    ("macos-x64", "macOS Intel", re.compile(r"macOS-x64\.dmg$", re.I)),
    ("linux-deb", "Linux .deb", re.compile(r"\.deb$", re.I)),
    ("linux-tar", "Linux .tar.gz", re.compile(r"Linux-x64\.tar\.gz$", re.I)),
    ("linux-appimage", "Linux AppImage", re.compile(r"\.AppImage$", re.I)),
)
GROUPS = {"windows": ("windows-setup", "windows-portable-exe", "windows-portable-zip"),
          "macos": ("macos-arm64", "macos-x64"),
          "linux": ("linux-deb", "linux-tar", "linux-appimage")}


def kind(asset_name):
    for key, _, pattern in TYPES:
        if pattern.search(asset_name):
            return key
    return None  # SHA256SUMS e afins não contam


def fetch_releases(token=None, opener=urllib.request.urlopen):
    releases, page = [], 1
    while True:
        req = urllib.request.Request("https://api.github.com/repos/%s/releases?per_page=100&page=%d" % (REPOSITORY, page),
                                     headers={"Accept": "application/vnd.github+json", "User-Agent": "pt2vhf-download-stats"})
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with opener(req, timeout=30) as resp:
            batch = json.loads(resp.read())
        releases += batch
        if len(batch) < 100:
            return releases
        page += 1


def merge(state, releases):
    """Atualiza o histórico com o maior contador visto de cada (versão, arquivo)."""
    seen = state.setdefault("assets", {})
    for release in releases:
        tag = str(release.get("tag_name") or "")
        if not tag or release.get("draft"):
            continue
        for asset in release.get("assets", []):
            key = tag + "/" + asset["name"]
            seen[key] = max(int(seen.get(key, 0)), int(asset.get("download_count") or 0))
    return state


def totals(state):
    out = {key: 0 for key, _, _ in TYPES}
    for key, count in state.get("assets", {}).items():
        k = kind(key.split("/", 1)[1])
        if k:
            out[k] += count
    for group, members in GROUPS.items():
        out[group] = sum(out[m] for m in members)
    out["total"] = sum(out[g] for g in GROUPS)
    return out


def badge(count, label="downloads"):
    return {"schemaVersion": 1, "label": label, "message": "{:,}".format(count).replace(",", "."),
            "color": "2ea44f" if count else "lightgrey", "cacheSeconds": 1800}


def main(folder, token=None, releases=None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "state.json"
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    merge(state, releases if releases is not None else fetch_releases(token))
    path.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    result = totals(state)
    for key, count in result.items():
        (folder / (key + ".json")).write_text(json.dumps(badge(count)), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1] if len(sys.argv) > 1 else "downloads", os.environ.get("GITHUB_TOKEN")), indent=1))
