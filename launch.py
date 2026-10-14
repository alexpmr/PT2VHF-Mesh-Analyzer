"""Windows executable entry point with native error reporting."""
from mesh_analyzer.app import main

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        import ctypes
        import traceback
        from mesh_analyzer.database import profile_dir
        dest=profile_dir()/"startup-error.log"
        try:
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(traceback.format_exc(),encoding="utf-8")
        except Exception:pass
        try:
            ctypes.windll.user32.MessageBoxW(0,"O PT2VHF Mesh Analyzer não conseguiu iniciar.\n"+str(exc)+"\n\nDetalhes: "+str(dest),"PT2VHF Mesh Analyzer",0x10)
        except Exception:
            print(traceback.format_exc())
        raise SystemExit(1)