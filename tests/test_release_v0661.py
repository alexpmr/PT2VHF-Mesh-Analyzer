"""v0.6.61: indicador de conexão, menu Ferramentas, análise de cobertura, relevo com corte
compacto com cor, Relevo sombreado removido e automações recolhidas."""
import base64
import math
import re
import tempfile
import unittest
from array import array
from pathlib import Path
from unittest import mock

from mesh_analyzer import coverage as C
from mesh_analyzer.database import Database
from mesh_analyzer.survey import TerrainTiles

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "mesh_analyzer" / "ui.html").read_text(encoding="utf-8")
CENTER = (-16.1, -47.9)


def flat_tiles(height=1000.0, ridge=None):
    """Terreno sintético: plano, com uma crista opcional (função de lat, lon -> altura extra)."""
    tiles = TerrainTiles(None, getter=lambda url: (_ for _ in ()).throw(AssertionError("sem rede")))

    def load(self, key):
        tx, ty = key
        grid = array("f", [height]) * (256 * 256)
        if ridge:
            n = 256 * 2 ** self.z
            for py in range(256):
                for px in range(256):
                    gx, gy = tx * 256 + px + 0.5, ty * 256 + py + 0.5
                    lon = gx / n * 360 - 180
                    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * gy / n))))
                    extra = ridge(lat, lon)
                    if extra:
                        grid[py * 256 + px] = height + extra
        return grid
    return tiles, mock.patch.object(C._Raster, "_load", load)


def decode(result):
    return base64.b64decode(result["grid"]), result["size"]


def value_at(result, lat, lon):
    grid, n = decode(result)
    (s, w), (north, e) = result["bounds"]
    x = int((lon - w) / (e - w) * n)
    y = int((north - lat) / (north - s) * n)
    b = grid[min(n - 1, y) * n + min(n - 1, x)]
    return b - 200 if b else None


class CoverageModel(unittest.TestCase):
    def test_refractivity_and_fade_margin(self):
        self.assertAlmostEqual(C.refractivity_k(301), 4 / 3, delta=0.01)
        self.assertAlmostEqual(C.fade_margin_db(50, 50, "equatorial"), 0.0, places=6)
        self.assertGreater(C.fade_margin_db(95, 95, "desert"), C.fade_margin_db(95, 95, "equatorial"))
        self.assertLess(C.fade_margin_db(10, 10, "equatorial"), 0)

    def test_params_are_validated(self):
        with self.assertRaises(ValueError):
            C.coverage_params({"max_km": 50, "hires": True})
        with self.assertRaises(ValueError):
            C.coverage_params({"climate": "lunar"})
        with self.assertRaises(ValueError):
            C.coverage_params({"tx_power_dbm": 99})
        p = C.coverage_params({"preset": "LONG_FAST"})
        self.assertLess(p["rx_sensitivity_dbm"], -120)

    def test_flat_terrain_falls_off_with_distance_and_matches_free_space(self):
        tiles, patch = flat_tiles()
        with patch:
            r = C.coverage(tiles, CENTER, {"max_km": 5, "tx_height_m": 30, "rx_height_m": 30, "clutter_m": 0,
                                           "location_pct": 50, "time_pct": 50, "tx_power_dbm": 20,
                                           "tx_gain_dbi": 0, "rx_gain_dbi": 0, "rx_cable_db": 0, "freq_mhz": 915})
        self.assertEqual(r["fade_margin_db"], 0.0)
        north_1km = value_at(r, CENTER[0] + 1 / 111.2, CENTER[1])
        north_4km = value_at(r, CENTER[0] + 4 / 111.2, CENTER[1])
        self.assertGreater(north_1km, north_4km)
        fspl_4km = 20 * math.log10(4) + 20 * math.log10(915) + 32.44
        self.assertAlmostEqual(north_4km, 20 - fspl_4km, delta=2.5)
        # Simétrico: mesmo sinal a leste e ao norte na mesma distância.
        east_4km = value_at(r, CENTER[0], CENTER[1] + 4 / (111.2 * math.cos(math.radians(CENTER[0]))))
        self.assertAlmostEqual(north_4km, east_4km, delta=1.5)
        # Fora do círculo do alcance máximo não há dado.
        grid, n = decode(r)
        self.assertEqual(grid[0], 0)

    def test_ridge_shadows_the_area_behind_it(self):
        ridge_lat = CENTER[0] + 2 / 111.2
        ridge = lambda lat, lon: 150.0 if abs(lat - ridge_lat) < 0.002 else 0.0
        tiles, patch = flat_tiles(ridge=ridge)
        with patch:
            r = C.coverage(tiles, CENTER, {"max_km": 5, "tx_height_m": 5, "rx_height_m": 2, "clutter_m": 0})
        behind = value_at(r, CENTER[0] + 3.5 / 111.2, CENTER[1])
        open_side = value_at(r, CENTER[0] - 3.5 / 111.2, CENTER[1])
        self.assertLess(behind, open_side - 15)

    def test_highest_point_finds_the_hill(self):
        hill = (CENTER[0] + 0.004, CENTER[1] - 0.003)
        bump = lambda lat, lon: max(0.0, 80 - 40000 * math.hypot(lat - hill[0], lon - hill[1]))
        tiles, patch = flat_tiles(ridge=bump)
        with patch:
            best = C.highest_point(tiles, CENTER, 1)
        self.assertAlmostEqual(best["lat"], hill[0], delta=0.0008)
        self.assertAlmostEqual(best["lon"], hill[1], delta=0.0008)
        self.assertGreater(best["ground_m"], 1050)
        with self.assertRaises(ValueError):
            C.highest_point(tiles, CENTER, 60)      # v0.6.62: limite de 50 km


class CoverageInterface(unittest.TestCase):
    def test_tool_is_wired_to_api_and_map(self):
        self.assertIn('id="mapToolCoverage"', HTML)
        self.assertIn("$('mapToolCoverage').onclick=()=>openCoverageTool();", HTML)
        self.assertIn("api('/api/survey/coverage',{center:t.tx,params:t.params})", HTML)
        self.assertIn("api('/api/survey/highest',{center:t.tx,radius_km:t.searchKm})", HTML)
        for section in ("'Transmissor'", "'Receptor'", "'Ambiente'", "'Simulação'", "'Exibição'"):
            self.assertIn("section(" + section, HTML)
        # A escala e a transparência mudam sem recalcular (só redesenha a grade recebida).
        self.assertIn("drawCoverage();", HTML[HTML.index("body.querySelectorAll('[data-cov-display]')"):])
        self.assertIn("if(mapTool.kind==='coverage'){if(!mapTool.pickTx)return false;setCoverageTx(p,n.node_num);return true;}", HTML)

    def test_api_routes_exist(self):
        app = (ROOT / "mesh_analyzer" / "app.py").read_text(encoding="utf-8")
        self.assertIn('path == "/api/survey/coverage"', app)
        self.assertIn('path == "/api/survey/highest"', app)
        self.assertIn('"sensitivity":{p:survey.sensitivity_dbm(p) for p in presets}', app)


class ToolsMenuAndTerrain(unittest.TestCase):
    def test_planning_and_terrain_moved_to_tools(self):
        ver = HTML[HTML.index('<div id="mapVisibilityPanel"'):HTML.index("</section>", HTML.index('<div id="mapVisibilityPanel"'))]
        tools = HTML[HTML.index('<div id="mapToolsPanel"'):HTML.index('<section class="view active" id="viewMap">')]
        for token in ('id="mapToolLink"', 'id="mapToolSurvey"', 'id="mapTerrain"', 'id="mapToolCoverage"'):
            self.assertNotIn(token, ver)
            self.assertIn(token, tools)
        self.assertIn('id="mapToolsBtn"', HTML)

    def test_hillshade_removed(self):
        self.assertNotIn("mapHillshade", HTML)
        self.assertNotIn("Relevo sombreado", HTML)
        self.assertNotIn("World_Hillshade", HTML)

    def test_compact_terrain_control_with_color(self):
        self.assertIn('id="terrainColor"', HTML)
        self.assertIn("#terrainSlider #terrainCut{flex:1 1 auto", HTML)
        self.assertIn("width:68px", HTML[HTML.index("#terrainSlider{"):HTML.index("#terrainSlider{") + 200])
        self.assertIn("terrainRgb()", HTML)
        for ids in re.findall(r"\[('mapRadar','mapRadarOpacity'[^\]]*)\]", HTML):
            self.assertIn("'terrainColor'", ids)

    def test_preferences_accept_color_and_drop_old_hillshade(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "t.db")
            db.save_ui_preferences({"terrainColor": "#c0392b", "mapHillshade": True, "mapTerrain": True})
            with self.assertRaises(ValueError):
                db.save_ui_preferences({"terrainColor": "red"})
            db.close()


class ConnectionIndicator(unittest.TestCase):
    def test_green_red_and_type_in_parentheses(self):
        fn = HTML[HTML.index("function updateRadioConnectionIndicator(){"):HTML.index("let radioRestartBusy")]
        self.assertIn("const label=s=>s.name+' ('+connectionTypeLabel(s.kind)+')';", fn)
        self.assertIn("$('radioConnectionText').textContent=label(seen);", fn)
        self.assertIn("function connectionTypeLabel(kind){return {serial:'USB',ble:'BLE',tcp:'WIFI',mqtt:'MQTT'}", HTML)
        # Sem cores por tipo: só verde (conectado) e vermelho (desconectado).
        self.assertNotRegex(HTML, r'#radioConnectionStatus(\[data-status="connected"\])?\[data-kind=')


class CollapsedAutomations(unittest.TestCase):
    def test_items_start_collapsed_with_save_and_cancel(self):
        self.assertIn('id="meshAutoCard"', HTML)
        for key, card in (("meshtastic", "meshAutoCard"), ("meshcore", "mcAutoCard"), ("messages", "msgAutoCard")):
            self.assertIn("{key:'%s',card:'%s'" % (key, card), HTML)
        self.assertIn("body.className='autoItemBody';body.hidden=true;", HTML)
        self.assertIn("data-auto-save>Salvar</button><button type=\"button\" data-auto-cancel>Cancelar</button>", HTML)
        self.assertIn("for(const id of ['autoSaveButton','mcAutoSave','msgAutoSaveConfig'])$(id).hidden=true;", HTML)

    def test_unsaved_changes_are_resolved_before_switching(self):
        toggle = HTML[HTML.index("async function toggleAutomation(key){"):HTML.index("function setupAutomationItems(){")]
        self.assertIn("if(!await resolveAutomationChanges())return;", toggle)
        self.assertIn("if(view==='automations'&&next!==view&&automationDirtyItem()){", HTML)
        self.assertIn("if(mcAutoDirty)return;", HTML)
        self.assertIn("if(!msgAutoDirty){$('msgAutoEnabled').checked=d.config.enabled;", HTML)


if __name__ == "__main__":
    unittest.main()
