"""Ferramentas de planejamento no mapa (#179 e #180).

- Análise de enlace entre dois pontos quaisquer: perfil de altimetria com a
  curvatura da Terra (k=4/3), 1ª zona de Fresnel, perda em espaço livre, perda por
  difração (método de Deygout com gume de faca, ITU-R P.526), sinal estimado no
  receptor, margem sobre a sensibilidade do preset LoRa e veredito.
- Análise de melhor ponto: dentro de um polígono desenhado no mapa, procura os
  pontos mais altos, separados entre si, do mais alto para o mais baixo.

As elevações vêm dos tiles de terreno Terrarium (AWS Open Data; SRTM e outros,
~30–40 m por pixel), com o Open-Meteo como alternativa. Tiles e pontos ficam
guardados localmente, de modo que áreas já analisadas funcionam sem internet.
Não incluem prédios nem vegetação.
"""
from __future__ import annotations

import json
import math
import re
import time
import urllib.request

from .database import now_ms

EARTH_R = 6371000.0
K_FACTOR = 4 / 3
CACHE_DECIMALS = 4            # ~11 m: bem abaixo da resolução do modelo de terreno
FETCH_BATCH = 1000            # pontos por lote enviado à fonte de elevação
MAX_FETCH_POINTS = 8000       # proteção contra consultas exageradas
MAX_AREA_KM2 = 5000.0
LARGE_AREA_KM2 = 1000.0

# Presets Meshtastic: (spreading factor, largura de banda em kHz).
PRESETS = {
    "SHORT_TURBO": (7, 500), "SHORT_FAST": (7, 250), "SHORT_SLOW": (8, 250),
    "MEDIUM_FAST": (9, 250), "MEDIUM_SLOW": (10, 250), "LONG_FAST": (11, 250),
    "LONG_MODERATE": (11, 125), "LONG_SLOW": (12, 125), "VERY_LONG_SLOW": (12, 62.5),
    # MeshCore (#190): rádio configurado por SF e largura de banda; estes são os mais comuns.
    "MESHCORE_SF7_BW62.5": (7, 62.5), "MESHCORE_SF8_BW62.5": (8, 62.5), "MESHCORE_SF9_BW62.5": (9, 62.5),
    "MESHCORE_SF10_BW62.5": (10, 62.5), "MESHCORE_SF10_BW250": (10, 250), "MESHCORE_SF11_BW250": (11, 250),
    "MESHCORE_SF12_BW125": (12, 125),
}
SNR_LIMIT = {7: -7.5, 8: -10.0, 9: -12.5, 10: -15.0, 11: -17.5, 12: -20.0}
NOISE_FIGURE_DB = 6.0
# Frequência central aproximada do canal padrão por região (MHz).
REGION_FREQ = {
    "US": 906.875, "EU_433": 433.875, "EU_868": 869.525, "CN": 490.0, "JP": 922.4,
    "ANZ": 919.875, "ANZ_433": 433.92, "KR": 921.9, "TW": 923.875, "RU": 868.9, "IN": 865.4625,
    "NZ_865": 866.0, "TH": 922.0, "UA_433": 433.875, "UA_868": 868.4, "MY_433": 433.875,
    "MY_919": 921.0, "SG_923": 923.0, "PH_433": 433.875, "PH_868": 869.0, "PH_915": 916.0,
    "KZ_433": 433.875, "KZ_863": 864.0, "NP_865": 866.0, "BR_902": 904.875, "LORA_24": 2450.0,
}
VERDICTS = {"viable": "Viável", "marginal": "Marginal", "unviable": "Inviável"}
CARDINALS = ("N", "NNE", "NE", "ENE", "L", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO")


def preset_sf_bw(preset):
    """(SF, BW kHz) de um preset; aceita qualquer combinação MESHCORE_SF<n>_BW<kHz>."""
    name = str(preset or "").upper()
    if name in PRESETS:
        return PRESETS[name]
    m = re.fullmatch(r"MESHCORE_SF(\d+)_BW([\d.]+)", name)
    if m and int(m.group(1)) in SNR_LIMIT and 7.8 <= float(m.group(2)) <= 500:
        return int(m.group(1)), float(m.group(2))
    return None


def meshcore_preset(sf, bw):
    bw = float(bw)
    return "MESHCORE_SF%d_BW%s" % (int(sf), ("%g" % bw))


def sensitivity_dbm(preset):
    sf, bw = preset_sf_bw(preset) or PRESETS["LONG_FAST"]
    return round(-174 + 10 * math.log10(bw * 1000) + NOISE_FIGURE_DB + SNR_LIMIT[sf], 1)


# --- geometria -----------------------------------------------------------------
def _point(value, label="ponto"):
    try:
        lat, lon = float(value[0]), float(value[1])
    except (TypeError, ValueError, IndexError, KeyError):
        raise ValueError("Coordenadas inválidas para o " + label) from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValueError("Coordenadas fora do intervalo para o " + label)
    return lat, lon


def distance_m(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_R * math.asin(min(1.0, math.sqrt(h)))


def bearing_deg(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def cardinal(deg):
    return CARDINALS[int((deg % 360) / 22.5 + 0.5) % 16]


def _interpolate(a, b, f):
    """Ponto na fração f do grande círculo entre a e b."""
    d = distance_m(a, b) / EARTH_R
    if d < 1e-9:
        return a
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    sa, sb = math.sin((1 - f) * d) / math.sin(d), math.sin(f * d) / math.sin(d)
    x = sa * math.cos(la1) * math.cos(lo1) + sb * math.cos(la2) * math.cos(lo2)
    y = sa * math.cos(la1) * math.sin(lo1) + sb * math.cos(la2) * math.sin(lo2)
    z = sa * math.sin(la1) + sb * math.sin(la2)
    return math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))


class _Plane:
    """Projeção equiretangular local (metros) em torno de uma origem."""

    def __init__(self, origin):
        self.lat0, self.lon0 = origin
        self.kx = math.cos(math.radians(self.lat0)) * math.pi * EARTH_R / 180
        self.ky = math.pi * EARTH_R / 180

    def xy(self, p):
        return (p[1] - self.lon0) * self.kx, (p[0] - self.lat0) * self.ky

    def latlon(self, x, y):
        return self.lat0 + y / self.ky, self.lon0 + x / self.kx


def _inside(x, y, poly):
    inside = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def polygon_metrics(polygon):
    pts = [_point(p, "vértice") for p in polygon]
    if len(pts) < 3:
        raise ValueError("Desenhe um polígono com pelo menos 3 vértices")
    if len(pts) > 100:
        raise ValueError("Polígono com vértices demais (máximo 100)")
    origin = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    plane = _Plane(origin)
    xy = [plane.xy(p) for p in pts]
    area = abs(sum(xy[i - 1][0] * xy[i][1] - xy[i][0] * xy[i - 1][1] for i in range(len(xy)))) / 2
    perimeter = sum(distance_m(pts[i - 1], pts[i]) for i in range(len(pts)))
    # Centroide da área (cai para a média dos vértices em polígonos degenerados).
    a6 = sum(xy[i - 1][0] * xy[i][1] - xy[i][0] * xy[i - 1][1] for i in range(len(xy))) * 3
    if abs(a6) > 1e-6:
        cx = sum((xy[i - 1][0] + xy[i][0]) * (xy[i - 1][0] * xy[i][1] - xy[i][0] * xy[i - 1][1]) for i in range(len(xy))) / a6
        cy = sum((xy[i - 1][1] + xy[i][1]) * (xy[i - 1][0] * xy[i][1] - xy[i][0] * xy[i - 1][1]) for i in range(len(xy))) / a6
        centroid = plane.latlon(cx, cy)
    else:
        centroid = origin
    return {"vertices": pts, "area_km2": area / 1e6, "perimeter_km": perimeter / 1000, "centroid": centroid,
            "plane": plane, "xy": xy}


# --- elevações -----------------------------------------------------------------
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
TILE_MAX_ZOOM = 12            # ~38 m por pixel no equador
TILE_MAX_COUNT = 80           # por consulta; acima disso a zoom diminui
USER_AGENT = "PT2VHF-Mesh-Analyzer (+https://github.com/alexpmr/PT2VHF-Mesh-Analyzer)"


def _reason(exc):
    """Motivo curto e legível de uma falha de rede."""
    import urllib.error
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP %d%s" % (exc.code, " (limite de uso do serviço atingido)" if exc.code == 429 else "")
    if isinstance(exc, urllib.error.URLError):
        exc = exc.reason
    text = str(exc) or type(exc).__name__
    if "CERTIFICATE_VERIFY_FAILED" in text:
        return "certificado HTTPS não reconhecido (" + text[:80] + ")"
    if "timed out" in text.lower():
        return "tempo esgotado"
    return text[:120]


def _http_get(url, timeout=20):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return resp.read()


def _fetch_open_meteo(points):
    values = []
    for i in range(0, len(points), 100):    # o serviço aceita até 100 coordenadas por consulta
        chunk = points[i:i + 100]
        url = ("https://api.open-meteo.com/v1/elevation?latitude=" + ",".join("%.4f" % p[0] for p in chunk)
               + "&longitude=" + ",".join("%.4f" % p[1] for p in chunk))
        try:
            data = [float(x) for x in json.loads(_http_get(url))["elevation"]]
        except Exception as exc:
            raise RuntimeError("Open-Meteo: " + _reason(exc)) from exc
        if len(data) != len(chunk):
            raise RuntimeError("Open-Meteo: resposta incompleta")
        values += data
    return values


def _png_rgb(data):
    """Decodifica PNG 8 bits RGB/RGBA sem entrelaçamento (formato dos tiles Terrarium)."""
    import struct
    import zlib
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("tile de elevação inválido")
    pos, idat, width = 8, [], 0
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", body)
            if depth != 8 or color not in (2, 6) or interlace:
                raise ValueError("formato de tile de elevação não suportado")
            bpp = 3 if color == 2 else 4
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
        pos += 12 + length
    raw = zlib.decompress(b"".join(idat))
    stride = width * bpp
    rows, prev, pos = [], bytearray(stride), 0
    for _ in range(height):
        ftype, line = raw[pos], bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if ftype == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif ftype == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif ftype == 3:
            for i in range(stride):
                line[i] = (line[i] + ((line[i - bpp] if i >= bpp else 0) + prev[i]) // 2) & 255
        elif ftype == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b, c = prev[i], prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    return width, bpp, rows


SPIKE_M = 250.0               # pixel mais de 250 m fora da mediana 5x5 = defeito do tile
SPIKE_HINT_M = 150.0          # pré-filtro barato antes de calcular a mediana


def despike(grid, size=256, limit=SPIKE_M):
    """Remove defeitos dos tiles Terrarium: pixels ou pequenos aglomerados com altitude impossível,
    comuns nos zooms baixos perto de água (ex.: 3.418 m na margem do Lago Paranoá, cercado de
    ~1.000 m). Pixel suspeito (fora de ±150 m dos vizinhos a 2 px nos eixos) é comparado com a
    mediana da janela 5x5; se ficar mais de `limit` acima ou abaixo dela, recebe a mediana.
    `grid` é uma sequência plana (linha a linha) e é corrigida no lugar."""
    fixed = 0
    for y in range(size):
        row = y * size
        for x in range(size):
            v = grid[row + x]
            ring = [grid[row + xx] for xx in (x - 2, x + 2) if 0 <= xx < size] + \
                   [grid[yy * size + x] for yy in (y - 2, y + 2) if 0 <= yy < size]
            if not ring or (min(ring) - SPIKE_HINT_M <= v <= max(ring) + SPIKE_HINT_M):
                continue
            window = sorted(grid[yy * size + xx] for yy in range(max(0, y - 2), min(size, y + 3))
                            for xx in range(max(0, x - 2), min(size, x + 3)))
            median = window[len(window) // 2]
            if abs(v - median) > limit:
                grid[row + x] = median
                fixed += 1
    return fixed


class TerrainTiles:
    """Elevação a partir dos tiles Terrarium (AWS Open Data: SRTM, GMTED, ETOPO e outros), sem chave e
    sem limite diário. Os tiles ficam guardados em disco para uso sem internet."""

    def __init__(self, cache_dir=None, getter=None):
        self.cache_dir = cache_dir
        self.getter = getter or _http_get
        self.decoded = {}

    def _tile(self, z, x, y):
        key = (z, x, y)
        if key in self.decoded:
            return self.decoded[key]
        path = None
        data = None
        if self.cache_dir:
            from pathlib import Path
            path = Path(self.cache_dir) / str(z) / str(x) / ("%d.png" % y)
            if path.exists():
                data = path.read_bytes()
        if data is None:
            try:
                data = self.getter(TILE_URL.format(z=z, x=x, y=y))
            except Exception as exc:
                raise RuntimeError("tiles de terreno: " + _reason(exc)) from exc
            if path is not None:
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                except OSError:
                    pass
        width, bpp, rows = _png_rgb(data)
        flat = [(r[i] * 256 + r[i + 1] + r[i + 2] / 256) - 32768 for r in rows for i in range(0, width * bpp, bpp)]
        despike(flat, width)
        grid = [flat[y * width:(y + 1) * width] for y in range(len(rows))]
        if len(self.decoded) > 120:
            self.decoded.clear()
        self.decoded[key] = grid
        return grid

    @staticmethod
    def _pixel(lat, lon, z):
        n = 256 * 2 ** z
        lat = max(-85.0511, min(85.0511, lat))
        x = (lon + 180) / 360 * n
        y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
        return x, y

    def _zoom(self, points):
        for z in range(TILE_MAX_ZOOM, 5, -1):
            tiles = {(int(px // 256), int(py // 256)) for px, py in (self._pixel(p[0], p[1], z) for p in points)}
            if len(tiles) <= TILE_MAX_COUNT:
                return z
        return 6

    def _value(self, z, gx, gy):
        n = 2 ** z
        tx, ty = int(gx // 256) % n, min(n - 1, max(0, int(gy // 256)))
        return self._tile(z, tx, ty)[int(gy) % 256][int(gx) % 256]

    def __call__(self, points):
        z = self._zoom(points)
        out = []
        for lat, lon in points:
            px, py = self._pixel(lat, lon, z)
            # Interpolação bilinear entre os centros dos quatro pixels vizinhos.
            x0, y0 = math.floor(px - 0.5), math.floor(py - 0.5)
            fx, fy = px - 0.5 - x0, py - 0.5 - y0
            v00, v10 = self._value(z, x0, y0), self._value(z, x0 + 1, y0)
            v01, v11 = self._value(z, x0, y0 + 1), self._value(z, x0 + 1, y0 + 1)
            out.append((v00 * (1 - fx) + v10 * fx) * (1 - fy) + (v01 * (1 - fx) + v11 * fx) * fy)
        return out


def default_fetcher(cache_dir=None):
    """Tiles de terreno primeiro; Open-Meteo só se os tiles falharem."""
    tiles = TerrainTiles(cache_dir)

    def fetch(points):
        try:
            return tiles(points)
        except RuntimeError as tile_error:
            try:
                return _fetch_open_meteo(points)
            except RuntimeError as om_error:
                raise RuntimeError("Não foi possível obter as elevações do terreno (%s; %s). Verifique a conexão "
                                   "com a internet; pontos já analisados continuam disponíveis sem ela."
                                   % (tile_error, om_error)) from om_error
    return fetch


class Elevations:
    """Elevações com cache no SQLite, consultadas em lotes."""

    def __init__(self, db, fetch=None, cache_dir=None):
        self.db = db
        self.fetch = fetch or default_fetcher(cache_dir)
        self.fetched = 0
        with db._lock, db._db:
            db._db.execute("CREATE TABLE IF NOT EXISTS elevation_cache (key TEXT PRIMARY KEY, "
                           "elevation REAL NOT NULL, fetched_ms INTEGER NOT NULL)")

    @staticmethod
    def _key(p):
        return "%.*f,%.*f" % (CACHE_DECIMALS, p[0], CACHE_DECIMALS, p[1])

    def get(self, points):
        keys = [self._key(p) for p in points]
        unique = list(dict.fromkeys(keys))
        known = {}
        for i in range(0, len(unique), 500):
            chunk = unique[i:i + 500]
            rows = self.db._rows("SELECT key,elevation FROM elevation_cache WHERE key IN (%s)" % ",".join("?" * len(chunk)), chunk)
            known.update({r["key"]: float(r["elevation"]) for r in rows})
        missing = [k for k in unique if k not in known]
        if len(missing) > MAX_FETCH_POINTS:
            raise ValueError("Análise grande demais: reduza a área ou a distância")
        for i in range(0, len(missing), FETCH_BATCH):
            chunk = missing[i:i + FETCH_BATCH]
            values = self.fetch([tuple(map(float, k.split(","))) for k in chunk])
            self.fetched += len(chunk)
            stamp = now_ms()
            with self.db._lock, self.db._db:
                self.db._db.executemany("INSERT OR REPLACE INTO elevation_cache(key,elevation,fetched_ms) VALUES(?,?,?)",
                                        [(k, v, stamp) for k, v in zip(chunk, values)])
            known.update(zip(chunk, values))
        return [known[k] for k in keys]


# --- enlace entre dois pontos (#179) -------------------------------------------
def _knife_edge_db(v):
    """Perda por difração em gume de faca (ITU-R P.526-15, eq. 31)."""
    if v <= -0.78:
        return 0.0
    return 6.9 + 20 * math.log10(math.sqrt((v - 0.1) ** 2 + 1) + v - 0.1)


def _deygout(d, h, wavelength, i, j, depth=0):
    """Perda total por difração entre os índices i e j (alturas efetivas h, distâncias d)."""
    if j - i < 2:
        return 0.0
    best, best_k = -1e9, None
    span = d[j] - d[i]
    for k in range(i + 1, j):
        d1, d2 = d[k] - d[i], d[j] - d[k]
        if d1 <= 0 or d2 <= 0:
            continue
        line = h[i] + (h[j] - h[i]) * d1 / span
        v = (h[k] - line) * math.sqrt(2 * span / (wavelength * d1 * d2))
        if v > best:
            best, best_k = v, k
    if best_k is None or best <= -0.78:
        return 0.0
    loss = _knife_edge_db(best)
    if depth < 1:
        loss += _deygout(d, h, wavelength, i, best_k, depth + 1) + _deygout(d, h, wavelength, best_k, j, depth + 1)
    return loss


def _clearance(d, ground, wavelength, ha, hb):
    """Menor razão folga/raio de Fresnel e o índice onde ocorre."""
    dist = d[-1]
    start, end = ground[0] + ha, ground[-1] + hb
    worst, idx = None, None
    for k in range(1, len(d) - 1):
        d1, d2 = d[k], dist - d[k]
        bulge = d1 * d2 / (2 * EARTH_R * K_FACTOR)
        los = start + (end - start) * d1 / dist
        r = math.sqrt(wavelength * d1 * d2 / dist)
        ratio = (los - ground[k] - bulge) / r
        if worst is None or ratio < worst:
            worst, idx = ratio, k
    return worst, idx


def _min_height(d, ground, wavelength, fixed, end, limit=300.0):
    """Altura mínima de antena numa ponta (a outra fixa) ou nas duas iguais ("both")
    para liberar 60% da 1ª zona de Fresnel."""
    def ok(h):
        ha, hb = (h, h) if end == "both" else (h, fixed) if end == "a" else (fixed, h)
        return _clearance(d, ground, wavelength, ha, hb)[0] >= 0.6
    if not ok(limit):
        return None
    lo, hi = 0.0, limit
    if ok(lo):
        return 0.0
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if ok(mid) else (mid, hi)
    return math.ceil(hi * 2) / 2


def _number(params, key, default, lo, hi, label):
    raw = params.get(key, default)
    try:
        value = float(default if raw in (None, "") else raw)
    except (TypeError, ValueError):
        raise ValueError(label + " inválido") from None
    if not lo <= value <= hi:
        raise ValueError("%s: %g a %g" % (label, lo, hi))
    return value


def link_params(params):
    params = params or {}
    preset = str(params.get("preset") or "LONG_FAST").upper()
    if preset_sf_bw(preset) is None:
        raise ValueError("Preset LoRa desconhecido")
    return {
        "height_a": _number(params, "height_a", 2, 0, 300, "Altura da antena A (m)"),
        "height_b": _number(params, "height_b", 2, 0, 300, "Altura da antena B (m)"),
        "freq_mhz": _number(params, "freq_mhz", 915, 100, 6000, "Frequência (MHz)"),
        "tx_power_dbm": _number(params, "tx_power_dbm", 22, -10, 40, "Potência TX (dBm)"),
        "gain_a_dbi": _number(params, "gain_a_dbi", 2, -10, 30, "Ganho da antena A (dBi)"),
        "gain_b_dbi": _number(params, "gain_b_dbi", 2, -10, 30, "Ganho da antena B (dBi)"),
        "cable_a_db": _number(params, "cable_a_db", 0.5, 0, 30, "Perda de cabo A (dB)"),
        "cable_b_db": _number(params, "cable_b_db", 0.5, 0, 30, "Perda de cabo B (dB)"),
        "preset": preset,
    }


def link_analysis(elevations, a, b, params=None, observed=None):
    a, b = _point(a, "ponto A"), _point(b, "ponto B")
    p = link_params(params)
    dist = distance_m(a, b)
    if dist < 20:
        raise ValueError("Os dois pontos estão praticamente no mesmo lugar")
    if dist > 300000:
        raise ValueError("Distância acima de 300 km: fora do alcance de um enlace LoRa terrestre")
    samples = int(max(40, min(256, dist / 60)))
    points = [_interpolate(a, b, i / (samples - 1)) for i in range(samples)]
    ground = elevations.get(points)
    d = [dist * i / (samples - 1) for i in range(samples)]
    wavelength = 299.792458 / p["freq_mhz"]
    start, end = ground[0] + p["height_a"], ground[-1] + p["height_b"]
    effective, profile = [], []
    for k in range(samples):
        d1, d2 = d[k], dist - d[k]
        bulge = d1 * d2 / (2 * EARTH_R * K_FACTOR)
        los = start + (end - start) * d1 / dist
        r = math.sqrt(wavelength * d1 * d2 / dist) if 0 < k < samples - 1 else 0.0
        effective.append(ground[k] + bulge)
        profile.append({"distance_m": round(d1, 1), "ground_m": round(ground[k], 1), "terrain_m": round(ground[k] + bulge, 1),
                        "los_m": round(los, 1), "fresnel_m": round(r, 1), "lat": round(points[k][0], 6), "lon": round(points[k][1], 6)})
    heights = list(effective)
    heights[0], heights[-1] = start, end
    worst_ratio, worst_k = _clearance(d, ground, wavelength, p["height_a"], p["height_b"])
    fspl = 20 * math.log10(dist / 1000) + 20 * math.log10(p["freq_mhz"]) + 32.44
    diffraction = _deygout(d, heights, wavelength, 0, samples - 1)
    eirp = p["tx_power_dbm"] + p["gain_a_dbi"] - p["cable_a_db"]
    rx = eirp - fspl - diffraction + p["gain_b_dbi"] - p["cable_b_db"]
    sens = sensitivity_dbm(p["preset"])
    margin = rx - sens
    sf, bw = preset_sf_bw(p["preset"])
    snr = rx - (-174 + 10 * math.log10(bw * 1000) + NOISE_FIGURE_DB)
    worst = None
    if worst_k is not None:
        w = profile[worst_k]
        clearance = (w["los_m"] - w["terrain_m"])
        worst = {"distance_m": round(d[worst_k]), "clearance_m": round(clearance, 1), "ratio": round(worst_ratio, 2),
                 "lat": w["lat"], "lon": w["lon"], "ground_m": w["ground_m"],
                 "blocked_pct": max(0, min(100, round((1 - worst_ratio) * 100)))}
    km = lambda m: ("%.1f" % (m / 1000)).replace(".", ",")
    if worst is None or worst_ratio >= 0.6:
        obstruction = "Visada livre: 60% ou mais da 1ª zona de Fresnel desobstruída em todo o trajeto."
    elif worst_ratio >= 0:
        obstruction = "Terreno a %s km de A ocupa %d%% da 1ª zona de Fresnel (há visada, com perdas)." % (km(worst["distance_m"]), worst["blocked_pct"])
    else:
        obstruction = "Terreno a %s km de A bloqueia a linha de visada (%.0f m acima dela)." % (km(worst["distance_m"]), -worst["clearance_m"])
    if margin < 0:
        verdict = "unviable"
        reason = "Sinal estimado %.0f dB abaixo da sensibilidade do preset %s." % (-margin, p["preset"])
    elif margin < 10:
        verdict = "marginal"
        reason = "Margem de apenas %.0f dB: o enlace pode funcionar, mas com falhas por desvanecimento." % margin
    elif worst is not None and worst_ratio < 0:
        verdict = "marginal"
        reason = "Sem visada direta: o enlace depende de difração no terreno; vegetação e prédios podem impedi-lo."
    else:
        verdict = "viable"
        reason = "Margem de %.0f dB sobre a sensibilidade do preset %s." % (margin, p["preset"])
    suggestion = None
    if worst is not None and worst_ratio < 0.6:
        suggestion = {"height_a_m": _min_height(d, ground, wavelength, p["height_b"], "a"),
                      "height_b_m": _min_height(d, ground, wavelength, p["height_a"], "b"),
                      "height_both_m": _min_height(d, ground, wavelength, 0, "both")}
    return {
        "a": {"lat": a[0], "lon": a[1], "ground_m": round(ground[0], 1)},
        "b": {"lat": b[0], "lon": b[1], "ground_m": round(ground[-1], 1)},
        "params": p, "distance_m": round(dist), "azimuth_ab": round(bearing_deg(a, b), 1),
        "azimuth_ba": round(bearing_deg(b, a), 1), "samples": samples, "profile": profile, "worst": worst,
        "budget": {"eirp_dbm": round(eirp, 1), "fspl_db": round(fspl, 1), "diffraction_db": round(diffraction, 1),
                   "rx_dbm": round(rx, 1), "sensitivity_dbm": sens, "margin_db": round(margin, 1), "snr_db": round(snr, 1)},
        "verdict": verdict, "verdict_label": VERDICTS[verdict], "reason": reason, "obstruction": obstruction,
        "suggestion": suggestion, "observed": observed,
        "notes": "Elevações do modelo digital de terreno (~30–40 m); não incluem prédios, árvores nem a altura de torres. "
                 "Difração por gume de faca (Deygout); o resultado é uma estimativa para planejamento.",
    }


def observed_link(db, own_nodes, node_a, node_b, days=30):
    """SNR/RSSI já recebidos diretamente (sem saltos) quando uma das pontas é um rádio próprio."""
    if node_a is None or node_b is None:
        return None
    pairs = []
    if node_a in own_nodes and node_b not in own_nodes:
        pairs.append(node_b)
    elif node_b in own_nodes and node_a not in own_nodes:
        pairs.append(node_a)
    if not pairs:
        return None
    rows = db._rows("""SELECT rx_snr,rx_rssi FROM packets WHERE from_node=? AND timestamp_ms>=? AND via_mqtt=0
                       AND direction='rx' AND rx_snr IS NOT NULL AND hop_start IS NOT NULL AND hop_start=hop_limit""",
                    (pairs[0], now_ms() - days * 86400000))
    if not rows:
        return {"count": 0, "days": days}
    snr = sorted(float(r["rx_snr"]) for r in rows)
    rssi = sorted(float(r["rx_rssi"]) for r in rows if r["rx_rssi"] is not None)
    med = lambda v: v[len(v) // 2] if v else None
    return {"count": len(rows), "days": days, "snr_db": med(snr), "rssi_dbm": med(rssi), "best_snr_db": snr[-1]}


# --- melhor ponto (#180) -------------------------------------------------------
def best_points(elevations, polygon, reference=None, count=10, grid_points=2500):
    shape = polygon_metrics(polygon)
    area = shape["area_km2"]
    if area < 0.001:
        raise ValueError("Área muito pequena: desenhe um polígono maior")
    if area > MAX_AREA_KM2:
        raise ValueError("Área de %.0f km² acima do limite de %.0f km²: divida a região em partes menores" % (area, MAX_AREA_KM2))
    count = 10 if count in (None, "") else int(count)
    if not 1 <= count <= 50:
        raise ValueError("Quantidade de pontos: 1 a 50")
    plane, poly = shape["plane"], shape["xy"]
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    step = max(30.0, math.sqrt(area * 1e6 / grid_points))
    grid, cells = [], {}
    rows_n = int((max(ys) - min(ys)) / step) + 1
    cols_n = int((max(xs) - min(xs)) / step) + 1
    for i in range(rows_n):
        for j in range(cols_n):
            x, y = min(xs) + (j + 0.5) * step, min(ys) + (i + 0.5) * step
            if _inside(x, y, poly):
                cells[(i, j)] = len(grid)
                grid.append((x, y))
    for vx, vy in poly:       # polígonos estreitos: garante amostras nos vértices
        grid.append((vx, vy))
    pts = [plane.latlon(x, y) for x, y in grid]
    elev = elevations.get(pts)
    min_sep = max(2 * step, 150.0, 0.08 * math.sqrt(area * 1e6))
    # Topos: amostras que não têm vizinho mais alto dentro do polígono. Assim o ranking
    # mostra morros diferentes, e não várias encostas do mesmo morro.
    # Topo na borda: o terreno continua subindo fora do polígono.
    peaks, edge = set(), set()
    for (i, j), k in cells.items():
        neighbours = [cells.get((i + di, j + dj)) for di in (-1, 0, 1) for dj in (-1, 0, 1) if di or dj]
        if (all(n is None or elev[n] <= elev[k] for n in neighbours)
                and any(n is not None and elev[n] < elev[k] for n in neighbours)):
            peaks.add(k)
            if None in neighbours:
                edge.add(k)

    def suppress(cands, limit):
        chosen = []
        for c in sorted(cands, key=lambda c: -c[2]):
            if all(math.hypot(c[0] - o[0], c[1] - o[1]) >= min_sep for o in chosen):
                chosen.append(c)
                if len(chosen) >= limit:
                    break
        return chosen

    coarse = suppress([(x, y, e, k in edge) for k, ((x, y), e) in enumerate(zip(grid, elev)) if k in peaks], count * 2)
    # Refinamento: grade fina em volta de cada pico para achar o topo real.
    fine, fine_xy = [], []
    origin = []
    for cx, cy, _, at_edge in coarse:
        for i in range(-2, 3):
            for j in range(-2, 3):
                x, y = cx + i * step / 2.5, cy + j * step / 2.5
                if _inside(x, y, poly):
                    fine_xy.append((x, y))
                    origin.append(at_edge)
    if fine_xy:
        fine_e = elevations.get([plane.latlon(x, y) for x, y in fine_xy])
        fine = [(x, y, e, pk) for (x, y), e, pk in zip(fine_xy, fine_e, origin)]
    ref = _point(reference, "ponto de referência") if reference else shape["centroid"]
    ref_elev = elevations.get([ref])[0]
    ranked = suppress(coarse + fine, count * 3)
    rows = []
    for x, y, e, at_edge in ranked:
        lat, lon = plane.latlon(x, y)
        rows.append({"lat": round(lat, 6), "lon": round(lon, 6), "elevation_m": round(e, 1), "edge": bool(at_edge),
                     "distance_m": round(distance_m(ref, (lat, lon)))})
    # Do mais alto para o mais baixo; empate: o mais perto da referência primeiro.
    rows.sort(key=lambda r: (-r["elevation_m"], r["distance_m"]))
    rows = rows[:count]
    for n, r in enumerate(rows, 1):
        brg = bearing_deg(ref, (r["lat"], r["lon"]))
        r.update({"rank": n, "delta_m": round(r["elevation_m"] - ref_elev, 1), "bearing_deg": round(brg),
                  "direction": cardinal(brg)})
    lo, hi = min(elev), max(elev)
    return {
        "points": rows,
        "reference": {"lat": round(ref[0], 6), "lon": round(ref[1], 6), "elevation_m": round(ref_elev, 1),
                      "kind": "custom" if reference else "centroid"},
        "polygon": [[round(p[0], 6), round(p[1], 6)] for p in shape["vertices"]],
        "area_km2": round(area, 3), "perimeter_km": round(shape["perimeter_km"], 3),
        "resolution_m": round(step), "min_separation_m": round(min_sep), "samples": len(grid) + len(fine_xy),
        "elevation_range_m": [round(lo, 1), round(hi, 1)],
        "grid": [[round(p[0], 6), round(p[1], 6), round(e, 1)] for p, e in zip(pts, elev)],
        "grid_step_m": round(step),
        "requested": count,
        "note": ("A área tem %d topo(s) distinto(s); encostas do mesmo morro não entram no ranking." % len(rows))
                if len(rows) < count else "",
        "warning": ("Área grande: a busca usa uma amostra a cada %d m; para mais detalhe, divida a região." % round(step))
                   if area > LARGE_AREA_KM2 else "",
    }


# --- surveys salvos ------------------------------------------------------------
SAVED_KEY = "surveys"


def saved_surveys(db):
    try:
        value = json.loads(db._setting(SAVED_KEY) or "[]")
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


def save_survey(db, data):
    name = str(data.get("name") or "").strip()[:60]
    if not name:
        raise ValueError("Dê um nome ao survey")
    polygon = [list(p) for p in polygon_metrics(data.get("polygon") or [])["vertices"]]
    reference = list(_point(data["reference"], "ponto de referência")) if data.get("reference") else None
    count = int(data.get("count") or 10)
    if not 1 <= count <= 50:
        raise ValueError("Quantidade de pontos: 1 a 50")
    items = [s for s in saved_surveys(db) if s.get("name") != name]
    item = {"id": int(time.time() * 1000), "name": name, "polygon": polygon, "reference": reference,
            "count": count, "saved_ms": now_ms()}
    items.insert(0, item)
    db._set_setting(SAVED_KEY, json.dumps(items[:50]))
    return item


def delete_survey(db, survey_id):
    items = saved_surveys(db)
    left = [s for s in items if int(s.get("id", 0)) != int(survey_id)]
    if len(left) == len(items):
        raise LookupError("Survey não encontrado")
    db._set_setting(SAVED_KEY, json.dumps(left))


def _meshcore_defaults(out, info):
    """Frequência, SF/BW e potência lidos do rádio MeshCore (self_info)."""
    try:
        sf, bw = int(info.get("radio_sf") or 0), float(info.get("radio_bw") or 0)
        name = meshcore_preset(sf, bw)
        if preset_sf_bw(name):
            out.update(preset=name, from_radio=True, protocol="meshcore")
        if info.get("radio_freq"):
            out.update(freq_mhz=round(float(info["radio_freq"]), 3), from_radio=True)
        if info.get("tx_power"):
            out["tx_power_dbm"] = float(info["tx_power"])
    except (TypeError, ValueError):
        pass
    return out


def radio_defaults(sources):
    """Frequência, potência e preset do rádio ativo, quando disponíveis."""
    out = {"freq_mhz": 915.0, "tx_power_dbm": 22.0, "preset": "LONG_FAST", "region": None, "from_radio": False}
    try:
        sid = sources.active_radio()
        iface = sources._interfaces.get(sid) if sid is not None else None
        if getattr(iface, "is_meshcore", False):
            return _meshcore_defaults(out, getattr(iface, "self_info", {}) or {})
        lora = iface.localNode.localConfig.lora if iface is not None else None
    except Exception:
        lora = None
    if lora is None:
        return out
    try:
        try:
            from meshtastic.protobuf import config_pb2
        except ImportError:
            from meshtastic import config_pb2
        region = config_pb2.Config.LoRaConfig.RegionCode.Name(lora.region)
        preset = config_pb2.Config.LoRaConfig.ModemPreset.Name(lora.modem_preset)
    except Exception:
        return out
    out.update(region=region, from_radio=True)
    if preset in PRESETS and getattr(lora, "use_preset", True):
        out["preset"] = preset
    if getattr(lora, "override_frequency", 0):
        out["freq_mhz"] = round(float(lora.override_frequency), 3)
    elif region in REGION_FREQ:
        out["freq_mhz"] = REGION_FREQ[region]
    if getattr(lora, "tx_power", 0) > 0:
        out["tx_power_dbm"] = float(lora.tx_power)
    return out
