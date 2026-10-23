"""v0.6.41: análise de enlace entre 2 pontos (#179) e melhor ponto em polígono (#180)."""
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mesh_analyzer import survey, survey_pdf
from mesh_analyzer.database import Database, now_ms


def flat(points):
    return [800.0 for _ in points]


def hills(points):
    out = []
    for la, lo in points:
        out.append(800 + 300 * math.exp(-((la + 15.80) ** 2 + (lo + 47.90) ** 2) / 0.01 ** 2)
                   + 150 * math.exp(-((la + 15.77) ** 2 + (lo + 47.87) ** 2) / 0.006 ** 2)
                   + 40 * math.exp(-((la + 15.83) ** 2 + (lo + 47.93) ** 2) / 0.004 ** 2))
    return out


SQUARE = [(-15.75, -47.95), (-15.75, -47.85), (-15.85, -47.85), (-15.85, -47.95)]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "mesh-analyzer.sqlite3")
        self.calls = []

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def elevations(self, terrain=hills):
        def fetch(points):
            self.calls.append(len(points))
            self.assertLessEqual(len(points), survey.FETCH_BATCH)
            return terrain(points)
        return survey.Elevations(self.db, fetch)


class LinkBudget(Base):
    def test_sensitivity_follows_lora_presets(self):
        self.assertEqual(survey.sensitivity_dbm("LONG_FAST"), -131.5)
        self.assertEqual(survey.sensitivity_dbm("SHORT_TURBO"), -118.5)
        self.assertLess(survey.sensitivity_dbm("VERY_LONG_SLOW"), survey.sensitivity_dbm("LONG_SLOW"))

    def test_clear_short_link_is_viable_with_free_space_loss(self):
        r = survey.link_analysis(self.elevations(flat), (-15.80, -48.00), (-15.80, -47.98), {"height_a": 10, "height_b": 10})
        self.assertEqual(r["verdict"], "viable")
        self.assertAlmostEqual(r["distance_m"], 2141, delta=5)
        # FSPL = 20log10(d km) + 20log10(f MHz) + 32,44
        self.assertAlmostEqual(r["budget"]["fspl_db"], 20 * math.log10(2.141) + 20 * math.log10(915) + 32.44, delta=0.1)
        self.assertEqual(r["budget"]["diffraction_db"], 0.0)
        self.assertGreaterEqual(r["worst"]["ratio"], 0.6)
        self.assertIsNone(r["suggestion"])
        self.assertAlmostEqual(r["azimuth_ab"], 90, delta=0.5)
        self.assertAlmostEqual(r["azimuth_ba"], 270, delta=0.5)

    def test_earth_curvature_blocks_long_flat_path_with_low_antennas(self):
        r = survey.link_analysis(self.elevations(flat), (-15.80, -48.0), (-15.80, -47.80), {})
        self.assertLess(r["worst"]["ratio"], 0)
        self.assertGreater(r["budget"]["diffraction_db"], 0)
        self.assertIn("bloqueia a linha de visada", r["obstruction"])
        # Só subir as duas antenas resolve; uma só não basta (a outra ponta fica rente ao chão).
        self.assertIsNone(r["suggestion"]["height_a_m"])
        self.assertIsNotNone(r["suggestion"]["height_both_m"])
        both = survey.link_analysis(self.elevations(flat), (-15.80, -48.0), (-15.80, -47.80),
                                    {"height_a": r["suggestion"]["height_both_m"], "height_b": r["suggestion"]["height_both_m"]})
        self.assertGreaterEqual(both["worst"]["ratio"], 0.6)

    def test_hill_between_points_is_located_and_reduces_margin(self):
        r = survey.link_analysis(self.elevations(), (-15.80, -47.96), (-15.80, -47.84), {})
        self.assertIn(r["verdict"], ("marginal", "unviable"))
        self.assertAlmostEqual(r["worst"]["lon"], -47.90, delta=0.01)
        self.assertEqual(r["worst"]["blocked_pct"], 100)
        self.assertGreater(r["budget"]["diffraction_db"], 20)
        self.assertEqual(r["verdict_label"], survey.VERDICTS[r["verdict"]])
        self.assertTrue(r["reason"])

    def test_parameters_are_validated(self):
        e = self.elevations(flat)
        with self.assertRaises(ValueError):
            survey.link_analysis(e, (-15.8, -48), (-15.8, -47.9), {"height_a": 999})
        with self.assertRaises(ValueError):
            survey.link_analysis(e, (-15.8, -48), (-15.8, -47.9), {"preset": "XYZ"})
        with self.assertRaises(ValueError):
            survey.link_analysis(e, (-15.8, -48), (-15.8, -48), {})
        with self.assertRaises(ValueError):
            survey.link_analysis(e, (95, -48), (-15.8, -48), {})
        with self.assertRaises(ValueError):
            survey.link_analysis(e, (-15.8, -48), (-10.0, -40.0), {})

    def test_observed_snr_when_one_end_is_own_radio(self):
        for i, snr in enumerate((-4.0, 2.0, -1.0)):
            self.db._db.execute("""INSERT INTO packets(source_id,packet_id,source_packet_key,timestamp_ms,from_node,rx_snr,rx_rssi,
                                   hop_start,hop_limit,via_mqtt,direction) VALUES(1,?,?,?,?,?,?,3,3,0,'rx')""",
                                (str(i), "k%d" % i, now_ms(), 0x22, snr, -100 - i))
        self.db._db.commit()
        o = survey.observed_link(self.db, {0x11}, 0x11, 0x22)
        self.assertEqual(o["count"], 3)
        self.assertEqual(o["snr_db"], -1.0)
        self.assertEqual(o["best_snr_db"], 2.0)
        self.assertIsNone(survey.observed_link(self.db, {0x11}, 0x33, 0x22))
        self.assertIsNone(survey.observed_link(self.db, {0x11}, None, 0x22))


class ElevationCache(Base):
    def test_cached_points_work_offline(self):
        e = self.elevations(flat)
        first = survey.link_analysis(e, (-15.80, -48.0), (-15.80, -47.95), {})
        self.assertTrue(self.calls)

        def offline(points):
            raise RuntimeError("sem internet")
        again = survey.link_analysis(survey.Elevations(self.db, offline), (-15.80, -48.0), (-15.80, -47.95), {})
        self.assertEqual(first["budget"], again["budget"])
        with self.assertRaises(RuntimeError):
            survey.link_analysis(survey.Elevations(self.db, offline), (-15.70, -48.0), (-15.70, -47.95), {})


class BestPoint(Base):
    def test_distinct_hilltops_from_highest_to_lowest(self):
        r = survey.best_points(self.elevations(), SQUARE, count=10)
        elev = [p["elevation_m"] for p in r["points"]]
        self.assertEqual(elev, sorted(elev, reverse=True))
        self.assertEqual([p["rank"] for p in r["points"]], list(range(1, len(elev) + 1)))
        tops = [(p["lat"], p["lon"]) for p in r["points"]]
        for expected in ((-15.80, -47.90), (-15.77, -47.87), (-15.83, -47.93)):
            self.assertTrue(any(abs(a - expected[0]) < 0.006 and abs(b - expected[1]) < 0.006 for a, b in tops), expected)
        self.assertEqual(len(r["points"]), 3)
        self.assertIn("3 topo(s)", r["note"])
        self.assertAlmostEqual(r["area_km2"], 119, delta=1)
        self.assertGreater(r["points"][0]["elevation_m"], 1090)
        self.assertLessEqual(max(self.calls), survey.FETCH_BATCH)

    def test_edge_point_when_terrain_keeps_rising_outside(self):
        slope = lambda pts: [800 + (p[0] + 15.85) * 2000 for p in pts]
        r = survey.best_points(self.elevations(slope), SQUARE, count=3)
        self.assertTrue(r["points"])
        self.assertTrue(r["points"][0]["edge"])
        self.assertAlmostEqual(r["points"][0]["lat"], -15.75, delta=0.01)

    def test_reference_point_drives_delta_distance_and_direction(self):
        ref = (-15.85, -47.95)
        r = survey.best_points(self.elevations(), SQUARE, reference=ref, count=1)
        p = r["points"][0]
        self.assertEqual(r["reference"]["kind"], "custom")
        self.assertEqual(p["delta_m"], round(p["elevation_m"] - r["reference"]["elevation_m"], 1))
        self.assertEqual(p["direction"], "NE")
        self.assertAlmostEqual(p["distance_m"], survey.distance_m(ref, (p["lat"], p["lon"])), delta=2)

    def test_ties_go_to_the_closest_point(self):
        twin = lambda pts: [800 + 100 * math.exp(-((la + 15.78) ** 2 + (lo + 47.90) ** 2) / 0.005 ** 2)
                            + 100 * math.exp(-((la + 15.82) ** 2 + (lo + 47.90) ** 2) / 0.005 ** 2) for la, lo in pts]
        r = survey.best_points(self.elevations(twin), SQUARE, reference=(-15.84, -47.90), count=2)
        a, b = r["points"]
        if a["elevation_m"] == b["elevation_m"]:
            self.assertLessEqual(a["distance_m"], b["distance_m"])

    def test_limits(self):
        e = self.elevations(flat)
        with self.assertRaises(ValueError):
            survey.best_points(e, SQUARE[:2])
        with self.assertRaises(ValueError):
            survey.best_points(e, [(-10, -50), (-10, -40), (-20, -40), (-20, -50)])
        with self.assertRaises(ValueError):
            survey.best_points(e, SQUARE, count=0)
        with self.assertRaises(ValueError):
            survey.best_points(e, SQUARE, count=51)

    def test_save_and_delete_surveys(self):
        item = survey.save_survey(self.db, {"name": "Serra", "polygon": SQUARE, "reference": None, "count": 5})
        survey.save_survey(self.db, {"name": "Serra", "polygon": SQUARE[:3], "count": 7})
        saved = survey.saved_surveys(self.db)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["count"], 7)
        with self.assertRaises(ValueError):
            survey.save_survey(self.db, {"name": "", "polygon": SQUARE})
        survey.delete_survey(self.db, saved[0]["id"])
        self.assertEqual(survey.saved_surveys(self.db), [])
        with self.assertRaises(LookupError):
            survey.delete_survey(self.db, item["id"])


class Pdf(Base):
    def test_link_and_survey_pdfs(self):
        e = self.elevations()
        r = survey.best_points(e, SQUARE, count=5)
        link = survey.link_analysis(e, (r["points"][0]["lat"], r["points"][0]["lon"]), (-15.70, -47.80), {"height_a": 10})
        pdf = survey_pdf.survey_pdf(r, "Serra", [{"rank": 1, "target": "VHF3", "link": link}],
                                    [{"lat": -15.78, "lon": -47.92, "name": "VHF3"}])
        self.assertTrue(pdf.startswith(b"%PDF-"))
        single = survey_pdf.link_pdf(link, "Torre")
        self.assertTrue(single.startswith(b"%PDF-"))
        try:
            from pypdf import PdfReader
        except ImportError:
            return
        import io
        text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
        for needle in ("Survey de melhor ponto", "do mais alto para o mais baixo", "Enlace do ponto 1 até VHF3", "Margem do enlace"):
            self.assertIn(needle, text)


class RadioDefaults(unittest.TestCase):
    def test_reads_region_preset_and_power_from_active_radio(self):
        try:
            from meshtastic.protobuf import config_pb2
        except ImportError:
            from meshtastic import config_pb2
        lora = config_pb2.Config.LoRaConfig(region=config_pb2.Config.LoRaConfig.RegionCode.Value("EU_868"),
                                            modem_preset=config_pb2.Config.LoRaConfig.ModemPreset.Value("MEDIUM_FAST"),
                                            use_preset=True, tx_power=27)
        iface = SimpleNamespace(localNode=SimpleNamespace(localConfig=SimpleNamespace(lora=lora)))
        sources = SimpleNamespace(active_radio=lambda: 3, _interfaces={3: iface})
        d = survey.radio_defaults(sources)
        self.assertEqual((d["region"], d["preset"], d["freq_mhz"], d["tx_power_dbm"], d["from_radio"]),
                         ("EU_868", "MEDIUM_FAST", 869.525, 27.0, True))
        none = survey.radio_defaults(SimpleNamespace(active_radio=lambda: None, _interfaces={}))
        self.assertEqual((none["freq_mhz"], none["preset"], none["from_radio"]), (915.0, "LONG_FAST", False))


if __name__ == "__main__":
    unittest.main()
