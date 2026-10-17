"""v0.6.26 regression: Windows 10/11 packaging and old-client upgrade links."""
import unittest
from pathlib import Path
from mesh_analyzer import __version__
from mesh_analyzer.updater import release_assets
from scripts.retain_latest_release import removal_plan

ROOT = Path(__file__).resolve().parents[1]


class Win10CompatibilityTests(unittest.TestCase):
    def test_version_and_minimum_windows_build(self):
        self.assertRegex(__version__, r"^0\.6\.\d+$")
        self.assertEqual((ROOT / "VERSION").read_text().strip(), __version__)
        installer = (ROOT / "windows" / "installer.iss").read_text()
        self.assertIn('MinVersion=10.0.17763', installer)
        self.assertIn('ArchitecturesAllowed=x64compatible', installer)
        self.assertIn('OutputBaseFilename=PT2VHF-Mesh-Analyzer-Setup-Win10-Win11-x64', installer)

    def test_new_updater_names(self):
        names = release_assets(__version__)
        self.assertEqual(names["setup"],
                         f"PT2VHF-Mesh-Analyzer-v{__version__}-Setup-Win10-Win11-x64.exe")
        self.assertEqual(names["portable"],
                         f"PT2VHF-Mesh-Analyzer-v{__version__}-Portable-Win10-Win11-x64.zip")

    def test_ci_keeps_legacy_packages_for_v0625_updaters(self):
        workflow = (ROOT / ".github" / "workflows" / "windows.yml").read_text(encoding="utf-8")
        self.assertIn("Compilar EXE Windows 10/11 x64", workflow)
        self.assertIn("MajorSubsystemVersion <= 10", workflow)
        self.assertIn("Portable-Win11-x64.zip", workflow)
        self.assertIn("Setup-Win11-x64.exe", workflow)
        self.assertIn("Portable-Win10-Win11-x64.zip", workflow)
        self.assertIn("Setup-Win10-Win11-x64.exe", workflow)
        self.assertIn("Iniciar_Windows_10_11.bat", workflow)
        self.assertTrue((ROOT / "Iniciar_Windows_10_11.bat").exists())

    def test_release_cleanup_preserves_previous_until_both_families_uploaded(self):
        tag = "v0.6.26"
        names = [
            f"PT2VHF-Mesh-Analyzer-{tag}-Setup-Win10-Win11-x64.exe",
            f"PT2VHF-Mesh-Analyzer-{tag}-Portable-Win10-Win11-x64.exe",
            f"PT2VHF-Mesh-Analyzer-{tag}-Portable-Win10-Win11-x64.zip",
            f"PT2VHF-Mesh-Analyzer-{tag}-Setup-Win11-x64.exe",
            f"PT2VHF-Mesh-Analyzer-{tag}-Portable-Win11-x64.zip",
            "SHA256SUMS.txt",
        ]
        release = {"id":26,"tag_name":tag,"draft":False,"prerelease":False,
                   "assets":[{"name":name,"state":"uploaded","size":100} for name in names]}
        others = [release, {"id":25,"tag_name":"v0.6.25"}]
        self.assertEqual([r["id"] for r in removal_plan(release,others,tag)], [25])
        release["assets"].pop(3)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            removal_plan(release,others,tag)
