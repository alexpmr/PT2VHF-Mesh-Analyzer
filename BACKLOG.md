# Backlog — PT2VHF Mesh Analyzer

Esta é uma linha nova: não confundir com o projeto PT2VHF Traffic Analyzer v1.x.

## v0.1.0 (implementado no código)

- Núcleo Python próprio e banco SQLite independente; fontes USB/Serial, TCP/IP, BLE, MQTT RX com reconexão prevista.
- Abas e visual alinhados ao Traffic Analyzer, incluindo Configurações → Fontes e Retenções.
- Nós e mensagens persistentes com filtros e busca, canais e DM via rádio selecionado, mapa com posição histórica.
- Retenção configurável individual para sete categorias, default Nunca.
- Build Windows preparada para compilação por GitHub Actions/Windows; validação real pendente.

## v0.1.1 — implementado no código (aguarda CI e campo)

- Configurações → LoRa: ler o rádio selecionado, alterar parâmetros LoRa validados após confirmação, registrar comando e exportar snapshot com segredos removidos; readback persistente e alteração de todas as outras seções **ainda pendentes**.
- Menu Geral: checar releases a cada 15 minutos (ajuste local entre 5 e 1440 min); baixar/instalar diretamente pelo aplicativo **ainda pendente**.
- README: atalhos com nomes estáveis em releases/latest/download; publicação via GitHub Actions e versão extraída de VERSION. Links só ficam ativos quando assets da release v0.1.1 estiverem publicados.

## v0.3.0 — implementado no código (validação de CI e bancada pendentes)

- **#17**: Janela desktop WebView2 por padrão; navegador externo apenas por preferência do Sistema ou opção CLI explícita.
- **#18 / #2**: Aba Sistema, navegador ao iniciar desligado por padrão, intervalo compartilhado de atualizações (15 min padrão) persistido no SQLite, monitor único por processo e botão superior de consulta à release. LAN continua bloqueada até implementação de autenticação; atualização instalável interna pendente.
- **#6**: Aba Dispositivo com seleção Serial/BLE/TCP conectado, leitura por grupo, editor seguro de campos escalares protobuf, revisão e aplicação em sequência com resultado por grupo. Canais, configurações de módulos, segredos, readback de persistência e backup/restauração completa ainda pendentes.
- **#15**: Encerrar a janela termina backend/SQLite/fontes; o Inno Restart Manager detecta aplicativos que ocupem executável. Encerramento gracioso pelo Setup e atualização em execução continuam **pendentes de validação/aperfeiçoamento**.
- **#16**: Paridade integral das opções de configuração do Mapa e sonificação ainda pendente.

A existência de código e o êxito da compilação não comprovam comportamento em rádio conectado ou instalador aberto.

## v0.2.0 — implementado no código (aguarda publicação e validação em campo)

- **#8 Nós (parcial):** tabela compacta, 11 colunas, pesquisa/ordenação, seleção de colunas. **Remover seleção manual da referência de distância**: distância automática desde o nó próprio da fonte rádio Serial/BLE/Wi-Fi ativa, usando posição conhecida e identificação comprovada. Na ausência de referência válida, mostrar `—`. Hops por nó sem evidência permanecem indisponíveis; faltam detalhes históricos.
- **#9 Tráfego (parcial):** filtro de fonte/tipo, painel de detalhe, pausa e CSV. RX observado; contabilidade TX integral e dump raw auditável ainda não incorporados.
- **#10 Estatísticas (parcial):** a v0.4.0 contém 11 subabas; **remover Acessos** e manter exatamente **10 subabas**: Visão Geral, Rede, RF, Ranking, Routing, Tráfego, Consultas, Chat, Energia e Pontos de atenção. KPIs, médias SNR/RSSI, tendências e LocalStats permanecem. A paridade funcional avançada com o legado ainda é parcial.
- **#13 PDF (parcial):** relatório técnico offline nativo, com diversas seções de topologia/tráfego/diagnóstico RF, hipótese de colisão/interferência e proteção de privacidade. Não identifica LoRa externo, ruído real ou CRC específico sem instrumento/firmware compatível.
- **#11 Mapa (parcial):** cor de enlaces amarelo, pulsos por pacote no nó emissor conhecido, sem inventar caminho entre nós; controle completo de animação de tráfego ainda pendente.
- **#12 Mapa (parcial):** bases claro/escuro/OSM/topo/satélite, radar meteorológico e overlays de relevo/hillshade/corte DEM com slider; exige teste de provedores/CORS e de dispositivos reais.
- **#5 Menções (parcial):** autocomplete de nomes/Node IDs ao digitar @ no chat e inserção textual, sem qualquer garantia de menção/notificação remota.
- **Não implementados/sem conclusão:** idiomas integrais (#1), instalação automática segura de atualização (#2), LAN autenticada (#3), experiência de chat integral (#4), configuração completa/backup restaurável LoRa (#6), análises espectrais reais/medição CRC sem hardware adicional.

**Não fechar issues de backlog somente por existência de telas; exigem evidência e critérios de aceite completos.** Todos os dados permanecem no banco próprio e nenhuma instalação mexe no Traffic Analyzer legado.

## Nós: distância crescente por padrão (14/10/2026)

- [**#8 — Ordenação automática por distância**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/8): primeira execução deve ordenar **Distância ▲**, do nó mais próximo ao mais distante, com referência no rádio local conectado Serial/USB, BLE ou Wi-Fi/TCP, sem referência arbitrária em MQTT. Distância numérica real em km, empates estáveis, sem coordenadas no final (sempre) e atualização com mudança da fonte/posição. Respeitar ordenação escolhida e persistida pelo usuário. A v0.5.0 ordena por `Última interação ▼`; **pendente para a próxima release**.

## Solicitações de backlog ainda não encerradas

As melhorias abaixo são **itens de backlog**, não funcionalidades já entregues. O detalhamento e os testes de aceite estão nas respectivas issues:

1. [**#1 — Idiomas na barra superior**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/1): PT-BR (padrão), EN, ES, FR, DE e IT; tradução completa de interface, notificações e atualizador, persistência e troca sem reinício.
2. [**#2 — Indicador superior de versão e atualização interna (parcial)**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/2): exibir **vX.Y.Z · ATUALIZADO** (verde), **NOVA VERSÃO DISPONÍVEL** (laranja com destaque), ou **Verificando/Indisponível** (neutro). Clique quando atualizado força a checagem; clique quando há nova versão abre changelog e confirmação de **Atualizar agora**, baixando Setup/Portable, validando SHA256 e instalando/reiniciando com encerramento seguro da issue #15. Intervalo padrão de 15 minutos, configurável, avisos e novidades uma vez por versão, sem falsamente afirmar que está atualizado em falha de rede. **A consulta simples já existe; barra clicável e instalação interna continuam pendentes.**
3. [**#3 — Acesso Web pela LAN**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/3): **desligado por padrão**, acesso local via aplicativo; habilitação explícita com autenticação, senha, proteção das APIs/mensagens, endereço IP/porta e opção de desligar sem afetar localhost.
4. [**#4 — Mensagens com visual de mensageiro**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/4): conversas/canais, balões RX/TX, horários, dias, não lidas, notificações, campo inferior, status de envio/ACK sem alegar leitura remota.
5. [**#5 — Menções de nós usando `@`**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/5): filtro incremental a cada caractere por nome curto/longo, personalizado, aliases e Node ID; inserir referência legível; teclado/mouse; suporte a vários `@`; mensagem transmitida como texto interoperável (não equivale a DM nem notificação nativa universal).
6. [**#6 — Configuração completa do rádio com backup/restore (parcial)**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/6): ler todos os campos **suportados pelo firmware/hardware** (LoRa, canais, dispositivo, posição, energia, BLE, rede, módulos, segurança), editar em uma única interface e **Aplicar tudo** com comparação, validação, envio sequencial, acompanhamento de ACK/readback e reinício quando necessário. Backup versionado, exportação de segredos protegida e restauração seletiva com validação de compatibilidade e backup prévio. **O envio não é uma transação RF atômica**.

7. **Downloads na página principal do GitHub**: implementado no README e no pipeline da v0.1.1; confirmar funcionamento real após release.

## Novas solicitações de interface — 14/10/2026 (pendentes)

Referência visual/funcional: **[PT2VHF Traffic Analyzer](https://github.com/alexpmr/traffic-analyzer)**. Reaproveitar experiência de navegação e regras analíticas, **não** a API/servidor do MeshMonitor. Os exemplos visuais foram enviados na conversa do projeto.

- [**#8 — Aba Nós, tabela analítica**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/8): cabeçalho compacto, total de nós, busca, limpar, Colunas e Atualizar, **sem pull-down de referência de distância**. Usar automaticamente coordenadas e identidade do **nó local efetivamente conectado à fonte Serial/USB, BLE ou Wi-Fi/TCP ativa**; se houver várias fontes conectadas, usar contexto de rádio ativo inequívoco, nunca um nó arbitrário ou MQTT. Sem coordenadas/identidade válidas, mostrar `—`, e indicar origem/idade dos dados. Mostrar Nome longo, Nome curto, Role, Hardware, Saltos, Bateria, Tensão, Distância, SNR, Última interação e Última posição; **ordenação padrão por Distância crescente** (Haversine numérico, nó mais próximo primeiro), referência automática no rádio conectado; sem distância válida, mostrar `—` e colocar no fim, inclusive ao inverter; desempate estável por nome/ID. Só aplicar como default quando não houver uma ordenação anterior escolhida pelo usuário; recalcular e reordenar ao trocar rádio ou coordenadas. Preservar filtros e evitar falso status online. **Pendente após v0.5.0.**
- [**#9 — Aba Tráfego, histórico avançado**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/9): tabela conforme referência, busca, filtros de período/origem/destino/canal/tipo/fonte, ordenação, colunas personalizáveis, detalhes de pacote, distinção RF vs MQTT, dados de SNR/RSSI/hops/ACK quando realmente presentes, respeito à privacidade e desempenho com grande histórico.
- [**#10 — Estatísticas: paridade funcional com o Traffic Analyzer v1.62.1 NO PT2VHF Mesh Analyzer, exceto Acessos**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/10): manter apenas as **10 subabas** de Visão Geral, Rede, RF, Ranking, Routing, Tráfego, Consultas, Chat, Energia e Pontos de atenção; **remover botão, renderização e rota Acessos**. Preservar cards de KPIs, resumo automático, filtros globais de período/nó/fonte, gráficos, tabelas, rankings RF interativos, **Relatório/PDF e CSV**, URLs individuais, drill-down e cálculos auditáveis baseados exclusivamente no SQLite próprio. Redirecionar favoritos antigos `/estatisticas/acessos` para Visão Geral, sem excluir logs técnicos necessários. O Traffic Analyzer é somente a referência; não modificar nem depender do MM. **Pendente para próxima release.**
  - Não inventar valores de firmware, telemetria, acesso, consulta ou enlace RF quando dados insuficientes.
  - Ranking RF direto requer comprovação de recepção/enlace e correlação espacial/temporal; rotas observadas/inferidas ficam explicitamente separadas.
  - Adaptar a arquitetura, os cálculos e os componentes a **múltiplas fontes** Serial/USB, TCP/IP, BLE e MQTT e às retenções configuradas.

- [**#11 — Mapa: enlaces amarelos e animação de tráfego**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/11): linha de enlace amarela por padrão (configurável/persistente), animação ao vivo dos pacotes como no Traffic Analyzer, controle de velocidade/pausa, filtros e múltiplos eventos simultâneos.
  - Não representar caminho RF desconhecido como salto direto; distinguir visualmente RF confirmado, rota apenas observada e Internet/MQTT. Não remover enlaces históricos quando a animação terminar.
- [**#12 — Mapa: mapas-base, radar meteorológico e relevo com corte**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/12): seletor Ruas/OSM, Topográfico, Claro, Escuro e Satélite; overlays independentes.
  - **Radar meteorológico** baseado no provedor disponível (legado: RainViewer), ligado por padrão, atualização normalmente a cada 5 minutos, transparência e indicação da idade/disponibilidade do quadro.
  - **Relevo com corte** baseado em DEM real (legado: Terrain Tiles/Terrarium), com máscara de terrenos >= cota definida, slider vertical direito, limite superior inicial de 3.000 m ajustável entre 100 e 9.000 m, opacidade e preferências persistentes.
  - **Relevo sombreado** permanece overlay independente; camadas meteorológicas/topográficas não ocultam nós, enlaces nem animações. Sem dados externos, mapa e banco continuam funcionais.

- [**#13 — Relatório PDF técnico completo nativo do Mesh Analyzer**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/13): relatório com perfis Executivo, Técnico completo e Diagnóstico detalhado, inspirado e ampliado em relação ao código usado no Home Assistant. Gerar **offline** via SQLite próprio (sem dependências HA/MM), com capa, sumário, KPIs, inventário, pico de nós ativos com comprovação histórica, topologia/relays, mapas, RF, tráfego, energia, anomalias, recomendações de role justificadas, histórico e metodologia. PDF e dados estruturados em JSON/CSV opcionais com filtros por período/fonte/nó/canal/meio, relatório paginado com proveniência, privacidade por padrão e métricas coerentes com as 11 subabas.
  - Correções obrigatórias do código original: ausência de flag MQTT **não comprova RF**; nome VHF3 não é critério de RF; relacionamento lógico/traceroute não é automaticamente enlace físico; cache não comprova pico online; Packet ID isolado não basta para deduplicação entre emissores; direção de pacote desconhecida não implica RX; não truncar a análise em 10.000 eventos sem informar; delimitações DF, raio 100 km e fonte única deixam de ser hardcoded. APRS/waypoints somente quando integrações estiverem implementadas e habilitadas.
  - **Nova seção de engenharia RF — diagnóstico de coexistência/interferência (#13):** inventariar frequência efetiva, banda/BW, SF, CR, preset, hardware/firmware e receptores; séries de utilização de canal, TX airtime, RSSI/SNR, noise floor **quando medido**, telemetria `LocalStats`, RX válidos/inválidos, erros CRC **somente se o firmware/driver fornecer métricas específicas**, queda de pacotes, retransmissão e horários de pico. Atribuir hipóteses com nível de confiança: enlace marginal, colisões, tráfego LoRa de redes externas na mesma frequência/BW, ruído não-LoRa, antena/coaxial, alimentação/EMI, desajuste de configuração. **`rx_bad` não equivale automaticamente a erro CRC; SNR negativo não prova degradação; CAD isolado não identifica outra rede.** Comparar diferentes receptores e permitir sensor SDR secundário opcional; não varrer a banda com o rádio Meshtastic principal sem autorização. Gráficos de correlação, baseline, evidência e recomendações não invasivas no PDF, com os mesmos dados em Estatísticas → RF e Pontos de atenção. Ausência de capacidade de medir = `indisponível`, nunca `zero` ou `sem interferência`.
  - Vinculada à [**#10 — Estatísticas completas**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/10). O relatório é uma funcionalidade **pendente**, não uma nova release.

**Situação:** itens #5, #8–#13 parcialmente implementados na v0.2.0; pendências e validações continuam nas issues.

## Estatísticas — paridade visual e funcional com Traffic Analyzer v1.62.1 (14/10/2026)

- [**#10 — Clonar Visão Geral e as demais 9 subabas de Estatísticas**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/10): usar como referência fiel as telas e os componentes da v1.62.1 legada; preservar estilo, organização compacta, cálculos, filtros, gráficos, tabelas, rankings, consultas, drill-down, PDFs e CSV, mas **adaptar tudo ao SQLite e às fontes nativas Serial/BLE/TCP/MQTT**. A aba **Acessos foi explicitamente removida do escopo**; ficam **10 subabas**.
- **Visão Geral (layout obrigatório):** 8 cartões em grade 4×2 com `Nós ativos (conhecidos)`, `Pacotes (RX/TX)`, `Mensagens`, `Traceroutes`, `Relações observadas`, `SNR médio`, `RSSI médio`, `Pontos de atenção (críticos)`, e **faixa textual de resumo automático com borda amarela** cobrindo a largura total. Incluir nós originadores, período, contagens de RX/TX, mensagens, traceroutes, telemetria, nó mais ativo real, anomalias/críticos. Captura do Traffic Analyzer é **somente referência estética e de funcionalidades**; não copiar números/nó-fonte dela.
- **Demais 9 subabas:** `Rede`, `RF`, `Ranking`, `Routing`, `Tráfego`, `Consultas`, `Chat`, `Energia`, `Pontos de atenção`. Realizar auditoria de paridade **componente a componente** frente à v1.62.1; recriar funcionalidades ausentes, não apenas menus/placeholders. Manter filtro comum Período/Nó/Fonte, botões Atualizar tudo / Relatório PDF / Exportar CSV, indicador de atualização real e URLs dedicadas.
- **Rigor analítico:** somente apresentar métricas realmente existentes; sem RF direto inferido de traceroute, sem duplicar pacotes multi-receptor como transmissões únicas, sem inventar CRC/ruído, taxas de ACK, energia ou histórico indisponíveis. Reconciliação SQL → API → card → narrativa → exportação com testes automatizados e validação operacional no Windows.
- **Status:** em backlog, **não implementado integralmente na v0.4.0**. Issue #10 contém matriz detalhada e critérios de aceite por subaba.

## Alteração posterior à v0.4.0 — Estatísticas sem Acessos (14/10/2026)

- [**#10 — Remover Acessos de Estatísticas**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/10): retirar a subaba `Acessos`, mantendo somente 10 subabas, sem remover dados de auditoria técnica armazenados. Garantir navegação e URLs antigas sem tela em branco. **A v0.4.0 ainda exibe essa subaba; pendente de implementação.**

## v0.5.0 — implementado no código (validação de campo pendente)

- **#2 / #15 Atualização direta:** botão de nova versão abre popup, download oficial Setup/Portable com SHA256 e progresso, fechamento controlado da UI, substituição por worker externo e reinício; popup de novidades uma única vez. Testar em Windows 11 instalado e Portable em uso antes de concluir as issues. Atualizações 0.4→0.5 ainda manuais.
- **#16 Configurações → Mapa:** janela, observações mínimas, mapa-base, brilho, relevo, estilos de enlaces RF/MQTT, nós/linhas/nomes/heatmap, Auto Zoom, sons sintetizados, realce de atividade com controles de velocidade e duração. Algumas formas de realce de retransmissor/ACK dependem de dados não coletados; não inventar.
- **Barra principal do mapa:** removidos controles inoperantes de Reprodução e Velocidade; mapa-base e velocidade migrados para a aba Configurações → Mapa.
- **#10 Estatísticas:** retirado Acessos, 10 subabas; 8 KPIs e resumo no padrão legado v1.62.1; dados adicionais nas outras 9, mantendo paridade integral como pendência. Nunca copiar números da captura nem inferir RF direto / TX não instrumentado.
- **#3:** interface web LAN permanece desativada até autenticação e segurança.

## v0.4.0 — Correções de topologia e interface (aguardando CI/validação de bancada)

- **#22**: corrigidos portnums de traceroute/telemetria, parser protobuf RouteDiscovery e NeighborInfo, armazenamento e reprocessamento histórico com idempotência, diagnóstico de links sem posição. Traceroute/neighbor ainda não são prova de enlace RF direto; validação com rádio real pendente.
- **#20**: mapa filtra fontes e seus nós observados, enlaces, animações, busca e enquadramento; Todas por padrão. Proveniência source_id/node_num persistida; antigas fontes removidas poderão exigir recuperação de histórico.
- **#8**: remoção do seletor manual Distância; referência de identidade local de rádio conectado via Serial/BLE/TCP, quando única e com posição válida. Mais de um rádio exige escolha explícita de fonte no Mapa, sem adivinhação.
- **#21**: menu de navegação logo abaixo do título. Validar em diferentes resoluções.
- **#16**: paridade integral da aba de Configurações → Mapa (temas sonoros, brilho etc.) continua pendente, assim como métricas RF impossíveis sem evidência.
- Problemas não devem ser marcados resolvidos somente pela passagem do CI. Testar com dados reais antes de encerrar as issues.

## Defeito prioritário — enlaces ausentes no Mesh Analyzer v0.3.0 (14/10/2026)

- [**#22 — Enlaces não processados ou exibidos no Mapa**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/22): investigar o fluxo recepção → decodificação/roteamento → SQLite `links` → API → mapa. Código atual só registra segmentos de traceroute quando `TRACEROUTE_APP` tem rota decodificada; outros pacotes não geram evidência de enlace, e a UI omite linhas quando qualquer ponta não tem coordenadas. Incluir proveniência e classificação rigorosa de RF direto comprovado, traceroute/rota, MQTT e desconhecido; sem fabricar enlaces por SNR/hops/origem-destino. Mostrar contadores distintos **enlaces observados / armazenados / desenhados / sem posição**, motivos de descarte, dados de vários receptores, timestamps compatíveis de nós móveis e reprocessamento confiável de histórico. Não excluir relações antigas nem confundir ausência de linhas com rede sem enlaces. **Prioridade alta, ainda não corrigido.** Relacionado a #10, #11, #16 e #20.

## Mapa: escolha de fonte e layout do menu principal (14/10/2026)

- [**#20 — Filtro de fontes na barra superior do Mapa**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/20): seletor `Fonte: [Todas as fontes ▼]` (padrão Todas), com fontes Serial/USB, BLE, Wi-Fi/TCP e MQTT, nome amigável e estado conectado/offline; selecionando uma fonte, mostrar **somente nós, enlaces, tráfego animado e observações efetivamente atribuídos a ela**, preservando a opção consolidada. Integrar à busca, Enquadrar, período, heatmap e camadas. Criar índice de proveniência por `(source_id,node_num)` porque o catálogo global de nós, isoladamente, não permite esse filtro com segurança. Distinguir recepções RF vs MQTT e não misturar SNR/posições entre receptores ou instantes. Seleção persistente, sem interferir no rádio usado para transmissão de mensagens; fontes offline mantêm histórico conforme retenção. **Pendente de implementação na v0.3.0.**
- [**#21 — Menu principal logo abaixo do título**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/21): reposicionar a navegação superior (Mapa, Nós, Tráfego, Mensagens, Estatísticas, Automações, Configurações, Ajuda) em linha própria abaixo do título/logotipo e subtítulo; manter botão de versão e status, KPIs em linha separada e controles específicos do Mapa abaixo. Layout responsivo sem ocultar controles ou reduzir excessivamente o mapa. **Pendente na v0.3.0.**

## Configurações → Mapa — paridade com o legado (14/10/2026)

- [**#16 — Configurações → Mapa, controles completos**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/16): replicar a subaba Mapa do Traffic Analyzer legado conforme as duas capturas; janela temporal, mínimo de observações, tipo/brilho do mapa, máximo do slider de relevo, estilos independentes RF amarelo contínuo (somente comprovado) e MQTT/não RF tracejado, espessuras e botão restaurar, opções mostrar nós/linhas/nomes/identificados/heatmap, Auto Zoom durante traceroutes com restauração. Incluir **sonificação** (tema Fliperama anos 70, testes, volume, densidade, intervalo, máximo simultâneo, categories e estéreo espacial) e **animações de atividade em tempo real** (origem/resposta/relay observado, duração). Configurações persistentes e sincronizadas com o mapa sem inventar RF/ACK/retransmissores. **Reconfirmação pelas capturas:** agrupar seções Mapa e topologia, Temas sonoros e Atividade em tempo real; **mover seletor de mapa-base da barra superior para Configurações → Mapa**, sem duplicidade, aplicando alteração em tempo real.  Relacionada às issues #11 e #12; **pendente**.

## Configurações → Sistema / Dispositivo — complementos (14/10/2026)

- [**#18 — Sistema: frequência de verificação de novas versões**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/18): exibir em **Configurações → Sistema → Atualizações** o campo **Verificar novas versões a cada [15] minutos** (padrão **15 minutos**, intervalo permitido de 5 a 1.440 min). Persistir na configuração do aplicativo, com agendador único para janela desktop e acesso web opcional, evitando verificações duplicadas. Mostrar última/próxima checagem, estado atual e botão **Verificar agora**; alteração deve valer imediatamente e sobreviver a F5/reinício/upgrade. Vincular à [**#2 — Atualização interna**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/2). Na v0.2.0 a frequência já existe em localStorage, mas ainda não está consolidada em Sistema nem é aplicada por agendador global.
- [**#6 — Dispositivo: lista de rádios conectados e editor completo**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/6): em **Configurações → Dispositivo**, menu pull-down para rádios conectados via Serial/USB, BLE ou Wi-Fi/TCP/IP; ao selecionar, leitura atualizada de **todos os parâmetros disponíveis** e apresentação em uma só tela editável (identificação, LoRa, canais, GPS, energia, display, Bluetooth, rede, segurança e módulos). Permitir alterar múltiplas categorias e clicar **Salvar todas as alterações** uma única vez; confirmar diff, aplicar comandos de forma sequencial e segura, reler cada seção, mostrar sucesso parcial, falha, timeout e necessidade de reboot. Nenhum dispositivo MQTT somente RX pode receber comandos de configuração. Proteger chaves/PSKs e backups. Apenas os sete campos LoRa disponíveis na v0.2.0 foram implementados parcialmente; o editor abrangente está pendente.

## Inicialização desktop e Configurações → Sistema — opções Web (14/10/2026)

- [**#17 — Abrir janela própria do aplicativo por padrão**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/17): corrigir o executável atual, que chama `webbrowser.open` e abre a interface no navegador por padrão. Abrir janela desktop independente (WebView2 ou equivalente) com ícone na barra de tarefas, mantendo servidor local em loopback sem navegador externo automático.
- [**#18 — Configurações → Sistema: duas opções Web independentes**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/18):
  1. **Abrir página web no navegador ao iniciar:** padrão **Não**. Quando Sim, abrir navegador **local** adicionalmente à janela desktop, sem abrir instância duplicada.
  2. **Permitir acesso via Web de outros computadores:** padrão **Não**. Quando Sim, disponibilizar LAN **somente após autenticação segura** (issue #3), seleção de IP/porta, status do listener, URL e botão de copiar; desligar retira acesso LAN imediatamente sem afetar o app local.
  - Quatro combinações testáveis: ambos Não (apenas desktop); navegador Sim/LAN Não (desktop + navegador local); navegador Não/LAN Sim (desktop + rede autenticada); ambos Sim (desktop + navegador local + rede autenticada). Persistir escolhas no perfil, informar erros e evitar conflito de porta e processos órfãos. Ativar uma opção nunca habilita a outra.
- [**#3 — Segurança do acesso Web pela LAN**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/3): autenticação em todas as APIs, sessão, CSRF, HTTPS/proxy e restrição de acesso remoto; **não abrir 0.0.0.0 sem essas proteções**.

**Status: backlog, ainda não implementado na v0.2.0.**

## Instalador — impedimento ao atualizar com aplicação aberta (14/10/2026)

- [**#15 — Instalação/atualização bloqueada por instâncias abertas**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/15): o instalador Inno Setup da v0.2.0 informa que existem aplicações abertas e não consegue pará-las. Detectar a instância correta do **PT2VHF Mesh Analyzer**; solicitar fechamento seguro, encerrar atividade de fontes LoRa e SQLite, aguardar liberação do executável (incluindo PyInstaller onefile), e continuar automaticamente. Se falhar, oferecer Tentar novamente/Cancelar e término forçado somente da instância validada, com consentimento. **Não encerrar navegadores, outros softwares/PT2VHF ou processos de terceiros.** Preservar banco, configurações e instalação anterior em caso de erro; testar em Windows 11 instalado, com aplicativo aberto e durante atualização. Pendente de implementação/validação.

## Próximos passos (não implementados ou ainda não validados)

1. **Validar rádio físico no Windows 11:** USB/Serial, TCP/IP e BLE; conferir recepção, envio privado, ACK/NAK, múltiplas fontes e reconexões.
2. **Validar os binários publicados para Win11:** EXE, Setup e Portable já foram gerados na release v0.1.0; testar em Win11 físico, SmartScreen, Defender, instalação/atualização e desinstalação preservando o banco.
3. **Mensagens:** aprimorar chat privado, confirmação de ACK/NAK, reenvio, mensagens pendentes e notificações.
4. **Análise RF/roteamento:** parsing completo de traceroutes SNR por hop, ranking RF sem enlaces falsos e trilhas de nós móveis com validade temporal da posição.
5. **Compatibilidade de protocolos:** mapear formatos protobuf/versionamento e validar MQTT public/private, TLS e BLE nas diferentes plataformas.
6. **Portar funcionalidades do Traffic Analyzer:** consulta NodeInfo/telemetria, automações PING/CLIMA, alarmes, estatísticas avançadas, exportação PDF, dashboards e camadas meteorológicas.
7. **Segurança:** proteção das credenciais MQTT em repouso via Windows DPAPI/Keyring; autenticação para acesso de rede; política de cookies/sessão e TLS.
8. **Distribuição multiplataforma:** pacotes Linux (service + AppImage/deb) e macOS (.app), testes e assinatura.
9. **Banco e backup:** migração de histórico do MeshMonitor e Traffic Analyzer atual, backup/restore com integridade, controle de tamanho.
10. **Fontes e coexistência:** descoberta BLE automática, gerenciamento de nomes de fontes, diagnóstico RSSI/SNR, reconexão com backoff, filas e limite de consumo RF.

O projeto anterior permanece inalterado e não deve ser desinstalado automaticamente.