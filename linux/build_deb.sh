#!/bin/sh
# Gera o pacote .deb (Ubuntu / Linux Mint / Debian) a partir do executável já
# testado pelo PyInstaller (#153). Uso: linux/build_deb.sh <executável> <versão> <pasta-saída>
set -eu
exe=$1; version=$2; out=$3
here=$(cd "$(dirname "$0")" && pwd)
root=$(mktemp -d)
chmod 755 "$root"
pkg=pt2vhf-mesh-analyzer
install -d "$root/DEBIAN" "$root/opt/$pkg" "$root/usr/bin" "$root/usr/share/applications" \
  "$root/usr/share/doc/$pkg"
install -m 755 "$exe" "$root/opt/$pkg/PT2VHF-Mesh-Analyzer"
ln -s "/opt/$pkg/PT2VHF-Mesh-Analyzer" "$root/usr/bin/$pkg"
python3 - "$here/../branding/mesh-analyzer.png" "$root/usr/share/icons/hicolor" <<'PY'
import sys
from pathlib import Path
from PIL import Image
src, dest = sys.argv[1], Path(sys.argv[2])
with Image.open(src) as img:
    for size in (48, 64, 128, 256):
        folder = dest / f"{size}x{size}" / "apps"
        folder.mkdir(parents=True, exist_ok=True)
        img.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS).save(folder / "pt2vhf-mesh-analyzer.png")
PY
cat > "$root/usr/share/applications/$pkg.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=PT2VHF Mesh Analyzer
Comment=Cliente Meshtastic independente por Alex, PT2VHF
Exec=/usr/bin/$pkg
Icon=$pkg
Terminal=false
Categories=Network;HamRadio;
DESKTOP
cat > "$root/usr/share/doc/$pkg/copyright" <<DOC
PT2VHF Mesh Analyzer — por Alex, PT2VHF.
Fonte: https://github.com/alexpmr/PT2VHF-Mesh-Analyzer
DOC
size=$(du -sk "$root" | cut -f1)
cat > "$root/DEBIAN/control" <<CONTROL
Package: $pkg
Version: $version
Section: hamradio
Priority: optional
Architecture: amd64
Installed-Size: $size
Depends: libc6 (>= 2.35), xdg-utils
Recommends: bluez
Maintainer: Alex PT2VHF <alexpmr@gmail.com>
Homepage: https://github.com/alexpmr/PT2VHF-Mesh-Analyzer
Description: Cliente Meshtastic independente com mapa, mensagens e estatísticas
 PT2VHF Mesh Analyzer conecta a rádios Meshtastic por USB, Wi-Fi/TCP,
 Bluetooth LE e MQTT, guarda o tráfego em SQLite local e mostra mapa,
 nós, mensagens, estatísticas e automações. A interface abre no
 navegador padrão.
CONTROL
cat > "$root/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
echo "PT2VHF Mesh Analyzer instalado. Para rádio USB, seu usuário precisa do grupo dialout:"
echo "  sudo usermod -aG dialout \$USER   (e entre novamente na sessão)"
exit 0
POSTINST
cat > "$root/DEBIAN/postrm" <<'POSTRM'
#!/bin/sh
set -e
# Dados do usuário (~/.local/share/PT2VHF-Mesh-Analyzer) são preservados.
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
exit 0
POSTRM
chmod 755 "$root/DEBIAN/postinst" "$root/DEBIAN/postrm"
mkdir -p "$out"
dpkg-deb --root-owner-group --build "$root" "$out/PT2VHF-Mesh-Analyzer-v$version-amd64.deb"
rm -rf "$root"
