# PT2VHF Mesh Analyzer — imagem para servidor doméstico, NAS e Raspberry Pi (#160).
# Interface web em http://localhost:8789 (publique com -p 127.0.0.1:8789:8789).
ARG BASE=python:3.12-slim
FROM ${BASE} AS build
WORKDIR /src
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM ${BASE}
ARG VERSION=dev
LABEL org.opencontainers.image.title="PT2VHF Mesh Analyzer" \
      org.opencontainers.image.description="Cliente Meshtastic independente por Alex, PT2VHF" \
      org.opencontainers.image.source="https://github.com/alexpmr/PT2VHF-Mesh-Analyzer" \
      org.opencontainers.image.version="${VERSION}"
COPY --from=build /install /usr/local
# Usuário sem privilégios, no grupo dialout para rádios USB (--device /dev/ttyUSB0).
RUN groupadd --system --gid 20 dialout 2>/dev/null || true \
 && useradd --system --uid 1000 --gid dialout --home-dir /data --no-create-home mesh \
 && mkdir -p /data && chown mesh:dialout /data
WORKDIR /app
COPY launch.py VERSION ./
COPY mesh_analyzer ./mesh_analyzer
COPY branding/mesh_analyzer_logo.png.b64 ./branding/
ENV PT2VHF_CONTAINER=1 \
    PT2VHF_MESH_DATA=/data \
    PT2VHF_HOST=0.0.0.0 \
    PT2VHF_PORT=8789 \
    PT2VHF_DISABLE_AUTODETECT=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Sao_Paulo
USER mesh
VOLUME ["/data"]
EXPOSE 8789
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PT2VHF_PORT','8789')+'/health',timeout=4)" || exit 1
CMD ["python", "launch.py", "--headless", "--no-browser"]
