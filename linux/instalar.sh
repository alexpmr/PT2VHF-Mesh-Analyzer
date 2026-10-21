#!/bin/sh
# Instala o PT2VHF Mesh Analyzer para o usuário atual (sem sudo).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
bin_dir="${HOME}/.local/bin"
app_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
mkdir -p "$bin_dir" "$app_dir/applications" "$app_dir/icons/hicolor/256x256/apps"
install -m 755 "$here/PT2VHF-Mesh-Analyzer" "$bin_dir/PT2VHF-Mesh-Analyzer"
install -m 644 "$here/pt2vhf-mesh-analyzer.png" "$app_dir/icons/hicolor/256x256/apps/pt2vhf-mesh-analyzer.png"
cat > "$app_dir/applications/pt2vhf-mesh-analyzer.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=PT2VHF Mesh Analyzer
Comment=Cliente Meshtastic independente por Alex, PT2VHF
Exec=$bin_dir/PT2VHF-Mesh-Analyzer
Icon=pt2vhf-mesh-analyzer
Terminal=false
Categories=Network;HamRadio;
DESKTOP
echo "Instalado em $bin_dir/PT2VHF-Mesh-Analyzer."
echo "Abra pelo menu de aplicativos (PT2VHF Mesh Analyzer) ou execute o arquivo acima."
