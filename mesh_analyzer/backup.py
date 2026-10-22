"""Backup e restauração em um clique (#166).

Exportação: arquivo .zip com o banco SQLite (cópia online consistente pela API
de backup do SQLite) e um manifesto. O banco já contém conexões, favoritos,
preferências, automações e histórico.

Restauração: o arquivo é validado (manifesto, integridade do SQLite e tabelas
esperadas) e fica pendente; no próximo início, antes de abrir o banco, o atual
é copiado para backups/ e substituído. Nada é sobrescrito sem cópia de segurança.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import time
import zipfile
from pathlib import Path

from . import __version__

APP_NAME = "PT2VHF Mesh Analyzer"
DB_NAME = "mesh-analyzer.sqlite3"
MANIFEST = "manifest.json"
MAX_UPLOAD = 1024 * 1024 * 1024
REQUIRED_TABLES = {"sources", "nodes", "messages", "packets", "settings"}
FILE_RE = re.compile(r"^PT2VHF-Mesh-Analyzer-backup-[0-9]{8}-[0-9]{6}\.zip$")


def backups_dir(data: Path) -> Path:
    folder = Path(data) / "backups"
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    return folder


def restore_dir(data: Path) -> Path:
    folder = Path(data) / "restore"
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    return folder


def _check_sqlite(path: Path) -> dict:
    con = sqlite3.connect(str(path))
    try:
        if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Banco do backup está corrompido")
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = REQUIRED_TABLES - tables
        if missing:
            raise ValueError("Arquivo não é um banco do Mesh Analyzer (faltam: " + ", ".join(sorted(missing)) + ")")
        count = lambda t: con.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
        return {"sources": count("sources"), "nodes": count("nodes"), "messages": count("messages")}
    finally:
        con.close()


def export_backup(db, data: Path) -> dict:
    """Gera PT2VHF-Mesh-Analyzer-backup-AAAAMMDD-HHMMSS.zip em backups/."""
    folder = backups_dir(data)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    name = "PT2VHF-Mesh-Analyzer-backup-" + stamp + ".zip"
    tmp_db = folder / (name + ".sqlite3.part")
    tmp_zip = folder / (name + ".part")
    try:
        with db._lock:
            target = sqlite3.connect(str(tmp_db))
            try:
                db._db.backup(target, pages=256, sleep=0.05)
            finally:
                target.close()
        stats = _check_sqlite(tmp_db)
        manifest = {"app": APP_NAME, "version": __version__, "created_ms": int(time.time() * 1000),
                    "database": DB_NAME, **stats}
        with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            zf.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
            zf.write(tmp_db, DB_NAME)
        os.replace(tmp_zip, folder / name)
        db.log("Backup exportado: " + name)
        return {"file": name, "bytes": (folder / name).stat().st_size, "path": str(folder / name), **manifest}
    finally:
        tmp_db.unlink(missing_ok=True)
        tmp_zip.unlink(missing_ok=True)


def backup_file(data: Path, name: str) -> Path:
    if not FILE_RE.fullmatch(str(name)):
        raise ValueError("Nome de backup inválido")
    path = backups_dir(data) / name
    if not path.is_file():
        raise LookupError("Backup não encontrado")
    return path


def stage_restore(data: Path, stream, size: int) -> dict:
    """Recebe o .zip enviado, valida e deixa a restauração pendente para o próximo início."""
    if not 1 <= size <= MAX_UPLOAD:
        raise ValueError("Arquivo de backup vazio ou grande demais")
    folder = restore_dir(data)
    incoming = folder / "incoming.zip"
    pending = folder / "pending.sqlite3"
    candidate = folder / "candidate.sqlite3"  # só substitui a pendência se for válido
    remaining = size
    with open(incoming, "wb") as out:
        while remaining:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError("Envio do backup interrompido")
            out.write(chunk)
            remaining -= len(chunk)
    try:
        if not zipfile.is_zipfile(incoming):
            raise ValueError("O arquivo não é um backup .zip do Mesh Analyzer")
        with zipfile.ZipFile(incoming) as zf:
            names = set(zf.namelist())
            if MANIFEST not in names or DB_NAME not in names:
                raise ValueError("Backup incompleto: falta o manifesto ou o banco")
            manifest = json.loads(zf.read(MANIFEST).decode("utf-8"))
            if manifest.get("app") != APP_NAME:
                raise ValueError("Backup de outro aplicativo")
            info = zf.getinfo(DB_NAME)
            if info.file_size > 8 * MAX_UPLOAD:
                raise ValueError("Banco do backup grande demais")
            with zf.open(DB_NAME) as src, open(candidate, "wb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
        stats = _check_sqlite(candidate)
        meta = {"version": manifest.get("version"), "created_ms": manifest.get("created_ms"),
                "staged_ms": int(time.time() * 1000), **stats}
        os.replace(candidate, pending)
        (folder / "pending.json").write_text(json.dumps(meta), encoding="utf-8")
        return meta
    finally:
        incoming.unlink(missing_ok=True)
        candidate.unlink(missing_ok=True)


def pending_restore(data: Path):
    path = Path(data) / "restore" / "pending.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, ValueError):
        return None


def cancel_restore(data: Path):
    folder = Path(data) / "restore"
    for name in ("pending.json", "pending.sqlite3"):
        (folder / name).unlink(missing_ok=True)


def apply_pending_restore(db_path: Path) -> dict | None:
    """Chamado no início, antes de abrir o banco. Guarda o atual e aplica o pendente."""
    db_path = Path(db_path)
    folder = db_path.parent / "restore"
    pending, meta_path = folder / "pending.sqlite3", folder / "pending.json"
    if not pending.is_file() or not meta_path.is_file():
        return None
    result_path = folder / "last.json"
    result = {"applied_ms": int(time.time() * 1000)}
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        _check_sqlite(pending)
        if db_path.exists():
            safety = backups_dir(db_path.parent) / ("pre-restore-" + time.strftime("%Y%m%d-%H%M%S") + ".sqlite3")
            src = sqlite3.connect(str(db_path))
            dst = sqlite3.connect(str(safety))
            try:
                src.backup(dst)
            finally:
                dst.close(); src.close()
            result["safety_copy"] = safety.name
        for suffix in ("", "-wal", "-shm"):
            Path(str(db_path) + suffix).unlink(missing_ok=True)
        os.replace(pending, db_path)
        result.update(status="applied", **meta)
    except Exception as exc:
        result.update(status="failed", error=str(exc)[:200])
    finally:
        meta_path.unlink(missing_ok=True)
        pending.unlink(missing_ok=True)
        result_path.write_text(json.dumps(result), encoding="utf-8")
    return result


def last_restore(data: Path):
    path = Path(data) / "restore" / "last.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, ValueError):
        return None


def restart_command():
    """Comando para reabrir o próprio aplicativo (EXE empacotado ou código-fonte)."""
    import sys
    if getattr(sys, "frozen", False):
        return [sys.executable]
    if os.path.basename(sys.argv[0]) == "__main__.py":
        return [sys.executable, "-m", "mesh_analyzer"]
    return [sys.executable, os.path.abspath(sys.argv[0])]
