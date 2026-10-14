# Changelog — PT2VHF Mesh Analyzer

## v0.6.1 — 14/10/2026 — Identidade visual PT2VHF Mesh Analyzer

- **Marca própria:** logotipo circular verde sobre fundo escuro, com antena rádio, ondas de comunicação, montanhas e nós conectados, criado especificamente para o Mesh Analyzer.
- **Aplicativo:** cabeçalho com logotipo, título PT2**VHF** destacado e assinatura visual `Explore · Analise · Conecte`; favicon local usa a mesma imagem mesmo sem internet.
- **Windows 11:** ícone ICO real com resoluções de 16 a 256 px incorporado ao EXE PyInstaller; mesmo em Portable. Instalador Inno Setup utiliza a marca e seus atalhos na área de trabalho e Menu Iniciar apontam para o ícone do executável.
- **Barra de tarefas/janela WebView2:** AppUserModelID estável `PT2VHF.MeshAnalyzer` tanto no processo como nos atalhos do instalador, para agrupamento consistente.
- **Build auditável:** PNG base64 versionado é a fonte única da marca, com SHA256 e gerador de PNG/ICO; CI verifica recursos de ícone no PE e regressões de logo/favicons.
- **Sem alteração de funcionalidades Meshtastic ou SQLite:** esta é uma release visual e de empacotamento, permanecendo as demais issues do backlog em aberto.

**Validação pendente em campo:** cache de ícones e agrupamento no Windows 11, especialmente em atalhos fixados anteriormente na barra de tarefas, devem ser conferidos no computador real.

## v0.6.0 — 14/10/2026 — Estabilidade e evolução parcial do backlog

- **#15/#2 (correção em código):** desligamento ordenado de monitor, servidor HTTP, fontes/radios, workers e banco SQLite, seguido de saída explícita do próprio processo para liberar Setup/Portable externo. Mantida validação SHA256 e reinício. **Ainda requer teste real com Win11 físico; não encerrar issue com CI.**
- **#8:** aba Nós ordenada inicialmente por distância Haversine crescente, preservando ordenações manuais persistidas; nós sem referência/GPS válidos por último.
- **#25 (parcial):** botão "Salvar configurações", com alterações pendentes, persistência no SQLite das preferências do Mapa, Sistema e Retenções. Fonte e Aplicar no Rádio seguem fluxos separados; validação ampla/transactional e múltiplas janelas ainda pendentes.
- **#26:** aba Automações informa recurso em breve, sem sugerir bots ativos.
- **#27 (parcial):** modal de nó arrastável/redimensionável, disponível com/sem GPS, com dados locais e metadados; consultas RF apresentam indisponibilidade até haver backend e ACK/readback correlacionados.
- **#10 (parcial):** Visão Geral com tabelas de tráfego/nós, ranking RF conservador e diagnóstico, Routing com percentuais de hops, tabelas em Tráfego, Consultas, Chat, Energia e alertas, usando SQLite sem inventar RF direto, taxa ACK ou TX.

**Escopo pendente:** não foi concluído todo o backlog — especialmente LAN autenticada, i18n completo, edição/restauração abrangente do rádio, execução de consultas, links RF sem coordenadas ou evidência, PDF/relatórios equivalentes ao legado e várias regras analíticas. **Compilação/testes CI não comprovam utilização em dispositivos físicos.**

## v0.5.0 — 14/10/2026 — Atualização interna, Mapa e Estatísticas

- **Atualização pelo aplicativo (primeira implementação):** indicador superior abre janela de novidades e opção para baixar nova versão sem navegador; seleção automática de Setup/Portable, comparação SHA256, barra de progresso, instalador externo que aguarda encerramento do Mesh Analyzer antes de substituir arquivos e reiniciar; popup de novidades exibido uma única vez. Log em `%LOCALAPPDATA%\\PT2VHF-Mesh-Analyzer\\update.log`. Necessita teste em Windows 11 instalado e portátil antes de encerrar issues #2 e #15.
- **Configurações → Mapa:** painel de topologia, janela/min. observações, mapa-base, brilho, máximo de relevo, cores/espessuras RF e MQTT, linhas/nós/nomes, mapa de calor com observações reais, filtros, Auto Zoom em novos traceroutes, sons sintetizados localmente e animação com duração/velocidade.
- **Barra Mapa:** remover Reprodução histórica e Velocidade inoperantes, mover mapa-base para Configurações → Mapa e manter controles operacionais.
- **Estatísticas:** 10 subabas (Acessos removida); Visão Geral no formato 4×2 com 8 cartões e narrativa amarela; aprimoradas outras subabas com dados próprios e direção/canal de mensagens, energia/voltagem, ranking de observações e análise de rotas. Relações filtradas por período/fonte/nó, respeitando a ausência de evidência de RF direto e TX de pacotes quando não medido.

**Limitações conhecidas:** instalação via atualizador não testada em Windows 11 físico (Setup/Portable); não há autenticação LAN e ela permanece desligada; paridade integral com o legado ainda pendente; várias métricas RF, ACK, taxa de sucesso e TX não são verificáveis por todos os rádios. CI não prova execução em hardware real.

## v0.4.0 — 14/10/2026 — Correção de topologia e fontes do mapa

- **Correção prioritária #22:** portas oficiais Meshtastic corrigidas: TELEMETRY_APP 67, TRACEROUTE_APP 70, NEIGHBORINFO_APP 71 e STORE_FORWARD_APP 65. Interpretar RouteDiscovery de payload protobuf, JSON conhecido e bytes codificados, rotas de ida e volta e anúncios de vizinhança quando disponíveis. Evidências de traceroute e vizinhança continuam *não comprovadas como RF direto*.
- **Histórico:** migração SQLite incremental de proveniência por fonte/nó, marcação de pacotes de topologia processados e reprocessamento em lote de até 10.000 pacotes antigos com dados suficientes. Não apaga banco nem presume RF direto de pacotes de texto.
- **Mapa:** contagem de relações gravadas, desenhadas, sem posição e ocultas; fonte específica (USB/Serial, BLE, Wi-Fi/TCP, MQTT) ou Todas, filtro persistente. Relacionamentos e animações respeitam fonte selecionada, inclusive histórico quando a fonte está offline.
- **Nós:** coluna Distância passa a usar automaticamente o Node ID local reportado por rádio Serial/BLE/TCP conectado e com posição válida, sem controle de referência manual. Havendo vários rádios conectados sem uma fonte ativa inequívoca, distância indisponível em vez de referenciar outro nó arbitrariamente.
- **Cabeçalho:** menu Mapa/Nós/Tráfego/etc. movido para linha própria abaixo do título e do indicador de versão, com rolagem horizontal em telas estreitas.
- **Testes:** portas protobuf oficiais, resposta traceroute `route`/`route_back`, vizinhos, MQTT/telemetria, fonte de nó, ausência de coordenadas e replay idempotente.

**Limitações:** desenhos exigem posições válidas dos nós; certas rotas históricas criptografadas não podem ser recuperadas sem dados decodificados; nem todos os relays RF podem ser reconstruídos de broadcasts multissalto. O reprocessamento inicial limita a análise a 10.000 registros candidatos por execução; nenhum resultado de RF direto pode ser afirmado por inferência. Compatibilidade real das fontes e instâncias WebView2 precisa de validação em rádio e Windows.

## v0.3.0 — 14/10/2026 — Janela desktop, Sistema e Dispositivo

- Execução padrão em **janela própria do aplicativo**, usando WebView2 no Windows 11. O HTTP continua restrito a 127.0.0.1; navegadores externos não são abertos automaticamente.
- Nova aba **Configurações → Sistema**: escolha independente de abrir também o navegador ao iniciar (não por padrão), intervalo de atualização no SQLite (15 minutos padrão, 5–1.440 ajustável) e status da checagem. **Acesso LAN permanece bloqueado**, pois autenticação ainda não foi implementada.
- Um monitor de atualizações por processo consulta o GitHub Releases e compartilha estado entre interface desktop e navegador local. Indicador superior verde/laranja/neutro clicável; nova versão abre release para download manual.
- **Configurações → Dispositivo**: seleção de rádios conectados USB/Serial, BLE e Wi-Fi/TCP/IP; leitura do cache sincronizado pelo driver Meshtastic; campos escalares não sensíveis disponibilizados por grupo conforme protobuf; revisão e um botão "Salvar todas as alterações", enviando grupos de forma sequencial, com aviso sobre falhas parciais. Canais, módulos e campos sensíveis são somente leitura, e não há transação atômica nem ACK garantido.
- Instalador Inno Setup informa/processa aplicativos que mantêm arquivos em uso pelo Restart Manager. O encerramento do WebView agora fecha o serviço local, fontes e SQLite. **O fechamento automático do instalador ainda requer testes reais com processo PyInstaller ativo**.
- Adicionados testes de preferências persistentes, bloqueio de LAN, validação de dados, revision stale e tratamento de falha de gravação.

**Limitações:** atualização automática com download/instalação verificados ainda não implementada; opção LAN desabilitada até autenticação; módulo/channels/secret backup ainda não editáveis; WebView2 Runtime precisa estar disponível; testes de campo com rádio e de instalação/atualização ainda necessários.

## v0.2.0 — 14/10/2026 — núcleo analítico independente e relatório técnico

- Estatísticas com 11 subabas: Visão Geral, Rede, RF, Ranking, Routing, Tráfego, Consultas, Chat, Energia, Pontos de atenção e Acessos, com consultas SQLite filtráveis.
- Relatório PDF técnico **offline** pelo próprio aplicativo: inventário, métricas, fontes, tráfego, topologia, telemetria, diagnóstico RF e hipóteses de interferência. Inclui origem/limitação dos dados e não exporta mensagens privadas.
- Engenharia RF: amostras `LocalStats` quando fornecidas, ocupação do canal e TX airtime quando disponíveis; RX inválido não é confundido com CRC específico; hipóteses de colisão/interferência não são declaradas como diagnóstico comprovado.
- Nós: tabela compacta com 11 colunas base, ordenação, busca, visibilidade de colunas e referência de distância selecionável.
- Tráfego: tabela compacta, filtro por fonte/tipo, detalhe de pacote, pausa e exportação CSV do conteúdo visível.
- Mensagens: sugestões de nós para menções `@` com busca incremental; o texto não aciona notificação especial no firmware do destinatário.
- Mapa: opções de mapas claro/escuro, radar meteorológico externo (RainViewer), relevo sombreado e relevo com corte DEM/slider; controle de opacidade e preferências locais.
- Animação de **pulsos no nó observado** para pacotes novos; não inventa uma trajetória RF entre origem e destino quando o caminho é desconhecido.
- Migração incremental de banco para tensão e telemetria `rf_samples`, preservando histórico/retencão.
- PDF e Estatísticas reutilizam o mesmo núcleo `analytics.py` e testes de regressão offline.

### Limites ainda não encerrados

- Não é paridade integral com o Traffic Analyzer v1.62.1: faltam métricas históricas avançadas, relatório geográfico/APRS, ranking RF direto comprovado quando não há evidência persistida, gráficos completos de todas as 11 subabas, consultas correlacionadas com ACK/timeout, gestão integral de roles, e auditoria autenticada de acessos.
- Não existe analisador de espectro LoRa nem contador de hardware específico para CRC via fontes normais Meshtastic; precisa de hardware/driver compatível ou SDR externo. Radar e DEM exigem provedor online e CORS permitido.
- Permanecem abertas as melhorias de tradução integral, atualização instalável por dentro do aplicativo, acesso LAN autenticado, menções, e editor completo de configurações/backup de segredos (issues #1–#6).
- Alterações devem ser validadas em Windows 11 e com rádio físico. CI cobre lógica simulada e build, não comprovação de RF.

## v0.1.1 — 14/10/2026 — Configuração LoRa e distribuição

- Configurações → LoRa: seleção de fonte rádio conectada, leitura e apresentação dos parâmetros da configuração local do dispositivo.
- Edição confirmada e com valores validados de parâmetros LoRa selecionados: região/preset (enums disponíveis), hops, potência, transmissão, frequência de slot e modo preset, conforme o firmware/biblioteca.
- Gravação da configuração solicitada via Meshtastic Python, registrando evento; confirmação real de persistência/readback após reboot depende de teste de bancada.
- Visualização das seções adicionais e dos canais em modo somente leitura, com omissão de chaves/segredos; exportação JSON redigida, sem função de restauração.
- Consulta ao GitHub Releases no aplicativo: checagem inicial e periódica (padrão 15 min), configurável por navegador; download e instalação manuais.
- Página inicial do GitHub com atalhos de download estáveis para Setup, Portable, EXE e SHA256 da release mais recente.
- Pipeline Windows versionado pelo arquivo VERSION, adicionando nomes estáveis aos artefatos e testes de CI em PR.
- Testes de validação de parâmetros LoRa, bloqueio de MQTT e proteção de credenciais.

**Pendente:** confirmação em rádio real e validação de build/instalação Windows após execução do CI. Idiomas completos, atualização totalmente automática, acesso LAN autenticado, menções @ e backup/restauração integral continuam no backlog.


## v0.1.0 — 14/10/2026 — Primeira implementação de referência

- Novo projeto próprio e independente do MeshMonitor, com banco SQLite por perfil de usuário.
- Interface de navegação semelhante ao Traffic Analyzer: Mapa, Nós, Tráfego, Mensagens, Estatísticas, Automações, Configurações, Ajuda.
- Cadastro, edição, ativação/desativação e exclusão de fontes USB/Serial, TCP/IP, BLE e MQTT; múltiplas fontes por banco.
- Listener de pacotes da biblioteca Meshtastic; registro por origem; importação de NodeDB sem falsificar estado online de nós antigos.
- Recepção e histórico de texto, posições, metadados e traceroutes; aliases observados por Node ID.
- Envio de mensagens nos canais e para destinatário privado por interface de rádio conectada; status "aceito pelo rádio", não confirmação de leitura.
- Modo MQTT de recepção de envelopes; armazenamento de pacotes sem prometer decriptação de conteúdo.
- Retenção de nós, pacotes, mensagens, posições, traceroutes, enlaces e eventos, individualmente configurável, padrão nunca.
- Linha de análise RF conservadora: não classificar um hop como RF direto sem evidência de RF adequada.
- Projetos de build para EXE portátil e instalador Windows 11 x64 via PyInstaller/Inno Setup/GitHub Actions.
- Testes automatizados de banco, retenção, ingestão, aliases, envio mock e API local/CSRF; inspeção visual local sem acesso a mapa online.

**Limites:** build Windows e operação com rádios físicos não validadas neste ambiente; bots e análises históricas avançadas do Traffic Analyzer ainda não foram migradas.