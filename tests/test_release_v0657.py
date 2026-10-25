"""v0.6.57: contador de downloads por tipo de build (#210)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import download_stats as ds  # noqa: E402


def rel(tag, **counts):
    return {"tag_name": tag, "assets": [{"name": n.replace("TAG", tag), "download_count": c} for n, c in counts.items()]}


class Kinds(unittest.TestCase):
    def test_asset_names_map_to_build_types(self):
        cases = {"PT2VHF-Mesh-Analyzer-v0.6.56-Setup-Win10-Win11-x64.exe": "windows-setup",
                 "PT2VHF-Mesh-Analyzer-Setup-Win11-x64.exe": "windows-setup",
                 "PT2VHF-Mesh-Analyzer-v0.6.56-Portable-Win10-Win11-x64.exe": "windows-portable-exe",
                 "PT2VHF-Mesh-Analyzer-Portable-Win10-Win11-x64.zip": "windows-portable-zip",
                 "PT2VHF-Mesh-Analyzer-macOS-arm64.dmg": "macos-arm64",
                 "PT2VHF-Mesh-Analyzer-v0.6.56-macOS-x64.dmg": "macos-x64",
                 "PT2VHF-Mesh-Analyzer-amd64.deb": "linux-deb",
                 "PT2VHF-Mesh-Analyzer-v0.6.56-Linux-x64.tar.gz": "linux-tar",
                 "SHA256SUMS.txt": None}
        for name, kind in cases.items():
            self.assertEqual(ds.kind(name), kind, name)


class Totals(unittest.TestCase):
    def test_counts_survive_deleted_releases_and_never_go_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = [rel("v1", **{"A-TAG-Setup-Win10-Win11-x64.exe": 5, "A-TAG-amd64.deb": 2, "SHA256SUMS.txt": 9})]
            self.assertEqual(ds.main(tmp, releases=first)["total"], 7)
            # v1 apagada pela retenção; v2 nova; um contador que "voltou" não diminui o total.
            second = [rel("v2", **{"A-Setup-Win10-Win11-x64.exe": 3, "A-macOS-arm64.dmg": 4})]
            out = ds.main(tmp, releases=second)
            self.assertEqual((out["windows"], out["linux"], out["macos"], out["total"]), (8, 2, 4, 14))
            out = ds.main(tmp, releases=[rel("v2", **{"A-Setup-Win10-Win11-x64.exe": 1})])
            self.assertEqual(out["windows-setup"], 8)
            badge = json.loads((Path(tmp) / "total.json").read_text())
            self.assertEqual((badge["schemaVersion"], badge["message"], badge["label"]), (1, "14", "downloads"))
            self.assertEqual(json.loads((Path(tmp) / "linux-tar.json").read_text())["color"], "lightgrey")

    def test_thousands_use_dot(self):
        self.assertEqual(ds.badge(12345)["message"], "12.345")


class Readme(unittest.TestCase):
    def test_tables_show_badges_for_every_build(self):
        text = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
        for key in ("windows-setup", "windows-portable-exe", "windows-portable-zip", "macos-arm64", "macos-x64",
                    "linux-deb", "linux-tar", "total", "windows", "macos", "linux"):
            self.assertIn("badges%2Fdownloads%2F" + key + ".json", text)


if __name__ == "__main__":
    unittest.main()
