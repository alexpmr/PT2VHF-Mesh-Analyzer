"""v0.6.42: elevações por tiles de terreno (Terrarium) com cache em disco e Open-Meteo como alternativa."""
import struct
import tempfile
import unittest
import urllib.error
import zlib
from pathlib import Path

from mesh_analyzer import survey
from mesh_analyzer.database import Database


def terrarium_png(elevation_of, size=256, filters=(0, 1, 2, 3, 4)):
    """PNG RGB no formato Terrarium, usando todos os filtros de linha."""
    raw, prev = bytearray(), bytearray(size * 3)
    for y in range(size):
        line = bytearray()
        for x in range(size):
            v = elevation_of(x, y) + 32768
            line += bytes((int(v // 256), int(v % 256), int((v % 1) * 256)))
        f = filters[y % len(filters)]
        out = bytearray(line)
        for i in range(len(line)):
            a = line[i - 3] if i >= 3 else 0
            b, c = prev[i], prev[i - 3] if i >= 3 else 0
            pred = {0: 0, 1: a, 2: b, 3: (a + b) // 2}.get(f)
            if f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else b if pb <= pc else c
            out[i] = (line[i] - pred) & 255
        raw += bytes([f]) + out
        prev = line

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b""))


class Tiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.urls = []

    def tearDown(self):
        self.tmp.cleanup()

    def getter(self, url):
        self.urls.append(url)
        # Plano inclinado: 1000 m + 2 m por pixel para a direita + 0,5 m por pixel para baixo.
        return terrarium_png(lambda x, y: 1000 + 2 * x + 0.5 * y)

    def test_png_decoder_handles_every_row_filter(self):
        width, bpp, rows = survey._png_rgb(terrarium_png(lambda x, y: (x * 7 + y * 13) % 5000, size=16))
        self.assertEqual((width, bpp, len(rows)), (16, 3, 16))
        for y in range(16):
            for x in range(16):
                r, g, b = rows[y][x * 3:x * 3 + 3]
                self.assertEqual(r * 256 + g + b / 256 - 32768, (x * 7 + y * 13) % 5000)

    def test_bilinear_elevation_and_disk_cache_for_offline_use(self):
        tiles = survey.TerrainTiles(Path(self.tmp.name), self.getter)
        lat, lon = -15.80, -47.90
        px, py = tiles._pixel(lat, lon, survey.TILE_MAX_ZOOM)
        expected = 1000 + 2 * ((px - 0.5) % 256) + 0.5 * ((py - 0.5) % 256)
        self.assertAlmostEqual(tiles([(lat, lon)])[0], expected, delta=0.6)
        self.assertTrue(self.urls and "/terrarium/12/" in self.urls[0])
        self.assertTrue(list(Path(self.tmp.name).rglob("*.png")))

        def offline(url):
            raise urllib.error.URLError("sem rede")
        again = survey.TerrainTiles(Path(self.tmp.name), offline)
        self.assertAlmostEqual(again([(lat, lon)])[0], expected, delta=0.6)

    def test_zoom_drops_for_wide_areas(self):
        tiles = survey.TerrainTiles(None, self.getter)
        near = [(-15.8 + i * 0.001, -47.9) for i in range(10)]
        wide = [(-15 - i * 0.2, -48 + j * 0.2) for i in range(20) for j in range(20)]
        self.assertEqual(tiles._zoom(near), survey.TILE_MAX_ZOOM)
        self.assertLess(tiles._zoom(wide), survey.TILE_MAX_ZOOM)

    def test_failure_reasons_are_shown(self):
        err = urllib.error.HTTPError("u", 429, "Too Many", {}, None)
        self.assertIn("limite de uso", survey._reason(err))
        self.assertEqual(survey._reason(urllib.error.URLError(TimeoutError("timed out"))), "tempo esgotado")


class Fallback(unittest.TestCase):
    def test_open_meteo_is_used_when_tiles_fail_and_both_reasons_are_reported(self):
        calls = []
        original_tiles, original_om = survey.TerrainTiles.__call__, survey._fetch_open_meteo

        def broken_tiles(self, points):
            raise RuntimeError("tiles de terreno: HTTP 403")
        try:
            survey.TerrainTiles.__call__ = broken_tiles
            survey._fetch_open_meteo = lambda pts: calls.append(len(pts)) or [500.0] * len(pts)
            self.assertEqual(survey.default_fetcher()([(-15.8, -47.9)]), [500.0])

            def broken_om(pts):
                raise RuntimeError("Open-Meteo: HTTP 429 (limite de uso do serviço atingido)")
            survey._fetch_open_meteo = broken_om
            with self.assertRaises(RuntimeError) as ctx:
                survey.default_fetcher()([(-15.8, -47.9)])
            self.assertIn("HTTP 403", str(ctx.exception))
            self.assertIn("HTTP 429", str(ctx.exception))
        finally:
            survey.TerrainTiles.__call__, survey._fetch_open_meteo = original_tiles, original_om
        self.assertEqual(calls, [1])

    def test_open_meteo_requests_are_split_in_100_coordinates(self):
        urls = []

        def fake_get(url, timeout=20):
            urls.append(url)
            count = url.split("latitude=")[1].split("&")[0].count(",") + 1
            return ('{"elevation":[%s]}' % ",".join(["1"] * count)).encode()
        original = survey._http_get
        try:
            survey._http_get = fake_get
            values = survey._fetch_open_meteo([(-15.8, -47.9)] * 250)
        finally:
            survey._http_get = original
        self.assertEqual(len(values), 250)
        self.assertEqual(len(urls), 3)


class AppWiring(unittest.TestCase):
    def test_link_works_end_to_end_with_tiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "x.sqlite3")
            try:
                tiles = survey.TerrainTiles(Path(tmp) / "tiles", lambda url: terrarium_png(lambda x, y: 900.0))
                r = survey.link_analysis(survey.Elevations(db, tiles), (-15.80, -48.0), (-15.80, -47.97), {"height_a": 10, "height_b": 10})
                self.assertEqual(r["a"]["ground_m"], 900.0)
                self.assertEqual(r["verdict"], "viable")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
