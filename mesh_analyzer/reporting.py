"""Native offline technical PDF. Uses only Mesh Analyzer SQLite-derived data.

Sensitive messages, MQTT passwords, channel PSKs and raw packet payloads are excluded.
"""
from __future__ import annotations

from io import BytesIO
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String

from .analytics import calculate
from . import __version__

NAVY = colors.HexColor("#16273b")
BLUE = colors.HexColor("#2171b5")
TEAL = colors.HexColor("#258779")
GRAY = colors.HexColor("#4a5a68")


def printable(value, maximum=160):
    if value is None:
        return "Não medido"
    return escape(str(value)[:maximum])


def number(value, unit="", decimals=1):
    if value is None:
        return "Não medido"
    return (f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
            + unit)


def _grid(rows, widths=None, header=True, size=8):
    if not rows:
        rows = [["Sem dados disponíveis para os filtros selecionados."]]
        header = False
    t = Table([[Paragraph(printable(c), ST["Cell"]) for c in row] for row in rows],
              colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [("VALIGN",(0,0),(-1,-1),"TOP"),
             ("BOTTOMPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),
             ("LINEBELOW",(0,-1),(-1,-1),0.25,colors.HexColor("#cbd6df")),
             ("ROWBACKGROUNDS",(0,1 if header else 0),(-1,-1),
              [colors.white, colors.HexColor("#f4f7fa")])]
    if header:
        style.extend([("BACKGROUND",(0,0),(-1,0),NAVY)])
        for col in range(len(rows[0])):
            rows[0][col] = rows[0][col]
        # Cell text in header is dark on navy; adjust with a paragraph style below.
        t = Table([[Paragraph(printable(c), ST["HeadCell"] if j==0 else ST["Cell"])
                    for c in row] for j,row in enumerate(rows)],
                  colWidths=widths,repeatRows=1,hAlign="LEFT")
    t.setStyle(TableStyle(style))
    return t


def _bar_chart(items, width=750, height=130):
    """Deterministic vector chart with no JavaScript/CDN dependencies."""
    d = Drawing(width, height)
    items = [(str(n)[:22], float(c)) for n,c in items if c is not None][:10]
    if not items:
        d.add(String(8,height//2,"Sem amostras suficientes",fontSize=10,fillColor=GRAY))
        return d
    maxval=max(max(v for _,v in items),1)
    bar_h=min(15,(height-8)/len(items)-4)
    for i,(name,value) in enumerate(items):
        y=height-18-i*(bar_h+4)
        d.add(String(6,y+2,name,fontSize=8,fillColor=NAVY))
        bar_x=180
        d.add(Rect(bar_x,y,max(0,(width-260)*value/maxval),bar_h,
                   fillColor=TEAL if i%2 else BLUE,strokeColor=None))
        d.add(String(width-64,y+2,str(int(value)),fontSize=8,fillColor=GRAY))
    return d


def _footer(canvas, doc):
    canvas.saveState()
    w,h=landscape(A4)
    canvas.setStrokeColor(colors.HexColor("#d2dce4"))
    canvas.line(12*mm,13*mm,w-12*mm,13*mm)
    canvas.setFont("Helvetica",7)
    canvas.setFillColor(GRAY)
    canvas.drawString(12*mm,9*mm, f"PT2VHF Mesh Analyzer v{__version__} | por Alex, PT2VHF")
    canvas.drawRightString(w-12*mm,9*mm, f"Página {doc.page}")
    canvas.restoreState()


ST = getSampleStyleSheet()
ST.add(ParagraphStyle(name="BigTitleMesh",parent=ST["Title"],fontName="Helvetica-Bold",
                      fontSize=24,leading=29,textColor=NAVY,spaceAfter=13))
ST.add(ParagraphStyle(name="ChapterMesh",parent=ST["Heading2"],fontSize=15,leading=18,
                      textColor=BLUE,spaceBefore=12,spaceAfter=9))
ST.add(ParagraphStyle(name="TextMesh",parent=ST["BodyText"],fontSize=9,leading=13,spaceAfter=7))
ST.add(ParagraphStyle(name="Cell",fontName="Helvetica",fontSize=7.3,leading=10))
ST.add(ParagraphStyle(name="HeadCell",fontName="Helvetica-Bold",fontSize=7.5,leading=10,textColor=colors.white))


def generate(db, params=None, connection_status=None):
    a=calculate(db,params,connection_status)
    c=a["counts"]
    output=BytesIO()
    page_w,page_h=landscape(A4)
    usable=page_w-30*mm
    pdf=SimpleDocTemplate(output,pagesize=landscape(A4),leftMargin=15*mm,
                          rightMargin=15*mm,topMargin=19*mm,bottomMargin=18*mm,
                          title="Relatório técnico PT2VHF Mesh Analyzer",
                          author="Alex, PT2VHF",pageCompression=1)
    story=[]
    def heading(title):
        story.append(Paragraph(escape(title),ST["ChapterMesh"]))
    def paragraph(value):
        story.append(Paragraph(escape(str(value)),ST["TextMesh"]))
    def table(rows,widths=None):
        story.append(_grid(rows,widths))
        story.append(Spacer(1,6*mm))

    story.append(Spacer(1,14*mm))
    story.append(Paragraph("PT2VHF MESH ANALYZER", ST["BigTitleMesh"]))
    story.append(Paragraph("Relatório técnico de rede Meshtastic", ST["BigTitleMesh"]))
    paragraph("Topologia | inventário | observações RF | tráfego | saúde | diagnóstico de interferências")
    paragraph("por Alex, PT2VHF")
    paragraph("Gerado: "+datetime.fromtimestamp(a["generated_ms"]/1000,timezone.utc).strftime("%d/%m/%Y %H:%M UTC"))
    paragraph("Período: "+a["filters"]["period"]+" | Conexão: "+str(a["filters"]["source"] or "Todas")+
              " | Nó: "+str(a["filters"]["node"] or "Todos")+" | Canal: "+
              str(a["filters"]["channel"] if a["filters"]["channel"] is not None else "Todos"))
    paragraph("Este documento descreve apenas recepções e transmissões registradas nas conexões "
              "conectadas, durante o intervalo selecionado. Não constitui levantamento espectral "
              "ou prova de cobertura RF total.")
    story.append(PageBreak())
    heading("1. Resumo executivo e metodologia")
    table([
        ["Indicador","Valor","Indicador","Valor"],
        ["Nós conhecidos",c["nodes_known"],"Originadores observados",c["active_originators"]],
        ["Pacotes observados",c["observations"],"Pacotes via MQTT",c["mqtt"]],
        ["Observações em rádios",c["receiver"],"Mensagens registradas",c["messages"]],
        ["Traceroutes observados",c["traceroutes"],"Telemetrias recebidas",c["telemetry"]],
        ["SNR médio",number(c["mean_snr"]," dB"),"RSSI médio",number(c["mean_rssi"]," dBm")],
        ["Relações observadas",c["relations_observed"],"Enlaces RF diretos comprovados","Sem classificação conclusiva"],
        ["Pontos de atenção",c["alerts"],"Críticos",c["critical"]],
    ],[usable*.22,usable*.28,usable*.26,usable*.24])
    paragraph("Critérios: nós ativos = originadores de pacotes efetivamente arquivados no período; "
              "contagem de pacotes = observações armazenadas (não volume total no ar). SNR/RSSI "
              "consideram somente amostras presentes e não-MQTT. Nenhuma relação origem-destino "
              "é classificada automaticamente como enlace direto.")
    heading("2. Conexões receptoras e escopo de observação")
    table([["Conexão","Tecnologia","Pacotes","Estado atual"]]+
          [[s["name"],s["kind"],s["count"],s["connection"]] for s in a["source_breakdown"]],
          [usable*.32,usable*.20,usable*.18,usable*.30])
    heading("3. Inventário e nós sem atividade recente")
    silent=[n for n in a["nodes"] if n["last_seen_ms"] and n["last_seen_ms"] < a["generated_ms"]-7200*1000]
    table([["Nó","Node ID","Role","Hardware","Última observação"]]+
          [[n["long_name"] or n["short_name"] or "—",n["node_id"],
            n["role"] or "—",n["hw_model"] or "—",
            datetime.fromtimestamp(n["last_seen_ms"]/1000,timezone.utc).strftime("%d/%m/%Y %H:%M UTC")]
           for n in silent[:25]], [usable*.28,usable*.16,usable*.15,usable*.22,usable*.19])
    paragraph(f"Nós sem atividade no catálogo há mais de duas horas: {len(silent)}. "
              "O catálogo pode conter registros importados e não substitui confirmação de atividade pela conexão.")
    heading("4. Tráfego e composição por tipo")
    story.append(_bar_chart([(r["name"],r["count"]) for r in a["packet_types"]],width=usable*.95))
    table([["Tipo/Portnum","Observações"]]+[[x["name"],x["count"]] for x in a["packet_types"]],
          [usable*.72,usable*.28])
    heading("5. Top originadores e distribuição de saltos")
    table([["Origem","Pacotes observados"]]+
          [[x["name"],x["count"]] for x in a["top_originators"]],
          [usable*.72,usable*.28])
    table([["Saltos observados (quando calculáveis)","Observações"]]+
          [[x["hops"],x["count"]] for x in a["hops"]],
          [usable*.72,usable*.28])
    heading("6. Topologia: evidência e limitações")
    table([["Categoria registrada","Relações","Observações"]]+
          [[x["quality"],x["count"],x["observations"]] for x in a["link_types"]],
          [usable*.5,usable*.2,usable*.3])
    paragraph("Um traceroute pode revelar saltos, mas não comprova que origem e destino "
              "estão adjacentes por RF. Nenhum ranking de maior enlace direto será "
              "produzido com evidências inconclusivas. Posições históricas de nós móveis "
              "não serão usadas para esticar enlaces até o local atual.")
    heading("7. Engenharia RF: amostras do dispositivo")
    table([["Receptor/nó","Amostras","Canal","Air TX","RX inválido","CRC"]]+
          [[x["node"],x["samples"],number(x["channel_util"],"%"),
            number(x["air_util"],"%"),
            number(x["rx_invalid_percent"],"%"),"Não medido"]
           for x in a["rf_samples"][:30]],
          [usable*.27,usable*.12,usable*.12,usable*.12,usable*.16,usable*.21])
    paragraph("RX inválido não é sinônimo de CRC incorreto. Um contador verdadeiro "
              "de CRC requer sinalização específica do hardware/driver; LocalStats "
              "não permite atribuir esses erros automaticamente a colisões.")
    heading("8. Diagnóstico de coexistência, ruído e possíveis interferências")
    table([["Indicador","Estado atual"]]+[[k.replace("_"," ").capitalize(),v]
                                      for k,v in a["diagnosis"].items() if isinstance(v,str)],
          [usable*.27,usable*.73])
    paragraph("Possíveis causas de falhas: "+ "; ".join(a["diagnosis"]["possible_causes"])+
              ". Estas são hipóteses, não diagnósticos confirmados. SNR negativo pode "
              "ser normal em LoRa e não prova canal ruim. Outros sistemas LoRa só "
              "podem ser identificados com recepção/demodulação ou instrumentos compatíveis; "
              "um Meshtastic normal não é analisador de espectro universal.")
    heading("9. Pontos de atenção")
    table([["Severidade","Nó","Ocorrência"]]+
          [[x["severity"],x["node"],x["description"]] for x in a["alerts"][:45]],
          [usable*.15,usable*.20,usable*.65])
    _advanced_sections(db, params or {}, heading, paragraph, table, usable)
    heading("15. Recomendações técnicas e próximos testes")
    for line in [
        "Compare amostras contemporâneas de RSSI/SNR em receptores diferentes e anote BW, SF, CR, frequência e hardware.",
        "Para colisões, correlacione utilização do canal, horários e RX inválido; uma correlação não prova causalidade.",
        "Para interferência externa, use receptor secundário/SDR e observe espectro, largura de banda e linha de base de ruído.",
        "Inspecione antena, conectores, cabo, alimentação, fontes chaveadas e localização dos rádios antes de alterar presets.",
        "Não altere automaticamente região, potência, frequência, role ou configuração de uma rede em produção.",
        "Dados indisponíveis são explicitamente identificados e não devem ser confundidos com nível zero de ruído ou ausência de problemas."
    ]:
        paragraph("- "+line)
    heading("16. Proveniência e proteção das informações")
    paragraph("Origem: banco SQLite local independente do MeshMonitor, Home Assistant e Traffic Analyzer legado. "
              "Filtros e versão do aplicativo constam na capa. A geração exclui texto de mensagens "
              "privadas, PSKs, credenciais MQTT, tokens e payloads crus. Apenas agregados e identificadores "
              "de nós necessários ao diagnóstico são usados.")
    pdf.build(story,onFirstPage=_footer,onLaterPages=_footer)
    return output.getvalue()


PERIOD_HOURS = {"1h": 1, "6h": 6, "24h": 24, "7d": 168, "30d": 720, "all": 2160}


def _advanced_sections(db, params, heading, paragraph, table, usable):
    """#177: saúde da malha, repetidores, gargalos, cobertura, presença, alertas e mensagens."""
    from datetime import datetime as _dt
    from . import insights
    from .database import now_ms
    hours = PERIOD_HOURS.get(str(params.get("period") or "all"), 2160)
    since = now_ms() - hours * 3600000
    when = lambda ms: _dt.fromtimestamp(ms / 1000).strftime("%d/%m/%Y %H:%M") if ms else "—"
    rep = insights.repeaters(db, hours)["repeaters"]
    heading("10. Saúde dos repetidores")
    paragraph("Nós com papel ROUTER, REPEATER, ROUTER_LATE ou ROUTER_CLIENT. Disponibilidade = horas em que o "
              "repetidor deu sinal de vida (pacote dele, salto em rota ou vizinho em NeighborInfo) ÷ horas em que o "
              "app estava ouvindo a malha. Em rotas = traceroutes do período que passaram por ele.")
    table([["Nó", "Papel", "Disponib.", "Última vez", "Bateria", "Canal", "Airtime", "Em rotas"]] +
          [[r["name"], r["role"], "sem dados" if r["availability"] is None else number(r["availability"], "%"), when(r["last_seen_ms"]),
            "EXT" if (r["battery"] or 0) > 100 else number(r["battery"], "%", 0),
            number(r["channel_util"], "%"), number(r["air_util"], "%"), r["route_hops"]] for r in rep[:40]],
          [usable * w for w in (.22, .12, .1, .16, .1, .1, .1, .1)])
    routes = insights.routes(db, hours)
    heading("11. Rotas e nós gargalo")
    paragraph("%d rotas de traceroute no período. Um gargalo é um nó intermediário presente em muitas rotas; "
              "se ele parar, essas rotas se quebram." % routes["total_routes"])
    table([["#", "Nó", "Papel", "Rotas", "% das rotas"]] +
          [[i + 1, b["name"], b["role"] or "—", b["routes"], number(b["share"], "%")] for i, b in enumerate(routes["bottlenecks"][:20])],
          [usable * w for w in (.06, .4, .2, .14, .2)])
    cov = insights.coverage(db, hours)
    cells = sorted(cov["cells"], key=lambda c: -c["count"])
    heading("12. Cobertura observada")
    paragraph("%d recepções diretas (0 salto, sem MQTT) de nós com posição, agrupadas em %d células de ~1 km. "
              "Mostra onde estão os transmissores que este receptor ouve diretamente e com que qualidade." % (cov["samples"], len(cells)))
    table([["Célula (lat, lon)", "Recepções", "Nós", "SNR médio", "Melhor SNR", "RSSI médio"]] +
          [["%.3f, %.3f" % (c["lat"] + c["size"] / 2, c["lon"] + c["size"] / 2), c["count"], c["nodes"],
            number(c["snr"], " dB"), number(c["best_snr"], " dB"), number(c["rssi"], " dBm", 0)] for c in cells[:25]],
          [usable * w for w in (.26, .12, .1, .17, .17, .18)])
    heading("13. Presença dos nós (checagem automática)")
    has_table = bool(db._rows("SELECT 1 FROM sqlite_master WHERE type='table' AND name='auto_node_queries'"))
    rows = db._rows("""SELECT q.node_num,q.state,q.attempts,q.sent_ms,q.last_reply_ms,n.long_name,n.short_name,n.node_id
                       FROM auto_node_queries q LEFT JOIN nodes n ON n.node_num=q.node_num
                       WHERE q.kind='ping' AND q.sent_ms>=? ORDER BY q.attempts DESC,q.sent_ms DESC LIMIT 40""", (since,)) if has_table else []
    replied = sum(1 for r in rows if r["state"] == "replied")
    paragraph("%d nós checados no período: %d responderam, %d sem resposta." % (len(rows), replied, len(rows) - replied))
    table([["Nó", "Resultado", "Tentativas", "Última checagem", "Última resposta"]] +
          [[r["long_name"] or r["short_name"] or r["node_id"] or r["node_num"],
            {"replied": "respondeu", "timeout": "sem resposta", "awaiting_reply": "aguardando"}.get(r["state"], r["state"]),
            r["attempts"], when(r["sent_ms"]), when(r["last_reply_ms"])] for r in rows],
          [usable * w for w in (.3, .16, .12, .21, .21)])
    heading("14. Alertas e mensagens do período")
    alerts = db._rows("SELECT kind,COUNT(*) AS n FROM alerts WHERE created_ms>=? GROUP BY kind", (since,)) \
        if db._rows("SELECT 1 FROM sqlite_master WHERE type='table' AND name='alerts'") else []
    labels = {"silent": "Favorito calado", "battery": "Bateria baixa", "channel": "Canal congestionado",
              "dm": "Mensagem privada", "mention": "Menção"}
    msgs = db._rows("SELECT direction,COUNT(*) AS n FROM messages WHERE timestamp_ms>=? GROUP BY direction", (since,))
    talkers = db._rows("""SELECT m.from_node,COUNT(*) AS n,n.long_name,n.short_name FROM messages m LEFT JOIN nodes n ON n.node_num=m.from_node
                          WHERE m.timestamp_ms>=? AND m.direction='rx' GROUP BY m.from_node ORDER BY n DESC LIMIT 10""", (since,))
    counts = {r["direction"]: r["n"] for r in msgs}
    paragraph("Mensagens: %d recebidas e %d enviadas. O texto das mensagens não é incluído no relatório."
              % (counts.get("rx", 0), counts.get("tx", 0)))
    table([["Alerta", "Ocorrências"]] + [[labels.get(r["kind"], r["kind"]), r["n"]] for r in alerts],
          [usable * .5, usable * .2])
    table([["Quem mais escreveu", "Mensagens"]] +
          [[r["long_name"] or r["short_name"] or "!%08x" % (r["from_node"] or 0), r["n"]] for r in talkers],
          [usable * .5, usable * .2])
