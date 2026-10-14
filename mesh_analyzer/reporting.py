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
    heading("10. Recomendações técnicas e próximos testes")
    for line in [
        "Compare amostras contemporâneas de RSSI/SNR em receptores diferentes e anote BW, SF, CR, frequência e hardware.",
        "Para colisões, correlacione utilização do canal, horários e RX inválido; uma correlação não prova causalidade.",
        "Para interferência externa, use receptor secundário/SDR e observe espectro, largura de banda e linha de base de ruído.",
        "Inspecione antena, conectores, cabo, alimentação, fontes chaveadas e localização dos rádios antes de alterar presets.",
        "Não altere automaticamente região, potência, frequência, role ou configuração de uma rede em produção.",
        "Dados indisponíveis são explicitamente identificados e não devem ser confundidos com nível zero de ruído ou ausência de problemas."
    ]:
        paragraph("- "+line)
    heading("11. Proveniência e proteção das informações")
    paragraph("Origem: banco SQLite local independente do MeshMonitor, Home Assistant e Traffic Analyzer legado. "
              "Filtros e versão do aplicativo constam na capa. A geração exclui texto de mensagens "
              "privadas, PSKs, credenciais MQTT, tokens e payloads crus. Apenas agregados e identificadores "
              "de nós necessários ao diagnóstico são usados.")
    pdf.build(story,onFirstPage=_footer,onLaterPages=_footer)
    return output.getvalue()
