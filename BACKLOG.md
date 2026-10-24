## v0.6.47 — Implementado nesta entrega

- #191: conexão Bluetooth mais tolerante no Windows; conectar antes de parear; erros por etapa. Aceite físico pendente com os rádios do relato (sem PIN, que conectam no celular).
- #189: escolher no topo a conexão (rádio ou MQTT) cujos dados aparecem em todas as abas.

## v0.6.46 — Implementado nesta entrega

- #190 etapa 2 do MeshCore: colisões de prefixo, caminhos e mudanças de caminho, traceroute com SNR por trecho, vizinhos de repetidores, painel de repetidor (login, status, CLI), gestão de contatos e canais, anúncio, protocolo no mapa e presets MeshCore no planejamento.
- #188: coleta periódica de telemetria/status MeshCore nas Automações, em bloco próprio.
- Fora desta etapa: room servers (mensagens e histórico do servidor), configuração do rádio MeshCore (etapa 3).
- Aceite físico pendente: repetidor MeshCore real (login, status, vizinhos, traceroute) e coleta periódica.

## v0.6.45 — Implementado nesta entrega

- #185 etapa 1: conexão e recepção de rádios MeshCore Companion (USB, BLE, TCP), mensagens, tráfego e detecção automática.
- Aceite físico pendente: rádio MeshCore Companion real por USB, Bluetooth (com PIN) e Wi-Fi.
- Próximas etapas: (2) traceroute/caminhos dos repetidores na topologia, consultas remotas (status/telemetria/vizinhos de repetidores com login), alertas e relatório; (3) configuração do rádio MeshCore e presets do MeshCore nas ferramentas de planejamento.

## v0.6.43 — Implementado nesta entrega

- #164: pareamento sem PIN e inclusão automática de rádios Bluetooth sem PIN definido. Aceite físico pendente no Windows (rádio sem PIN e rádio com PIN).

## v0.6.42 — Implementado nesta entrega

- Elevações por tiles Terrarium (correção do erro do Open-Meteo relatado em uso real nas ferramentas #179/#180). Testado aqui com tiles reais.
- Aceite pendente: rodar enlace e survey no Windows do usuário e comparar com enlaces conhecidos da malha.

## v0.6.41 — Implementado nesta entrega

- #179 e #180 implementados com testes automatizados.
- Aceite pendente: conferir com elevações reais (Open-Meteo) em enlaces conhecidos da malha e um survey numa região com morros; validar o veredito contra enlaces que funcionam e que não funcionam na prática.
- Limitações conhecidas: o modelo de terreno (~90 m) não inclui prédios, árvores e torres; o mapa do PDF é um esquema de relevo (sem a cartografia de fundo); a classificação por visibilidade (quantos nós cada ponto enxerga) ficou como evolução.

## v0.6.40 — Implementado nesta entrega

- #164 a #177 implementados com testes automatizados.
- Aceite físico pendente: PIN Bluetooth em Windows e Linux com rádio real; alertas por Telegram e e-mail com contas reais; mensagens agendadas e respostas automáticas em malha real; edição de canais no rádio; perfil de terreno e `{clima}` (dependem do Open-Meteo); restauração de backup entre Windows, Linux e container.
- Limitações conhecidas: a tradução EN/ES cobre menus, botões, configurações e diálogos; parte das mensagens de estado geradas dinamicamente continua em português. Login para acesso pela rede e aplicativo de celular ficaram para depois.

## v0.6.39 — Implementado nesta entrega

- #162 implementado com testes automatizados. Aceite físico pendente: instalação nova no Windows com o rádio ligado na USB antes de abrir (o diálogo não deve aparecer).

## v0.6.38 — Implementado nesta entrega

- #153, #155, #156, #157, #158, #159 e #160 implementados com testes automatizados.
- Aceite físico pendente: VHF3/VHF4/VHF6/VHF8 por Bluetooth (fila e PIN), rádio USB + Wi-Fi (prioridade), favoritos alterados pelo celular, ping de presença em malha real por algumas horas, `.deb` em Ubuntu/Mint reais e container em Raspberry Pi.
- Pendências conhecidas: pedir o PIN BLE dentro do app (hoje orienta para a janela do Windows); container com Bluetooth e acesso pela rede com login (#160, etapa 2); verificar se o pacote do GHCR ficou público após a primeira publicação.

## v0.6.37 — Implementado nesta entrega

- #149, #150, #151 e #152 implementados com testes automatizados (mocks de rádio e Chromium). Aceite físico pendente: plugar rádio USB real, BLE com PIN de pareamento, troca USB ↔ Wi-Fi com dois rádios reais.
- Limitações conhecidas: aviso BLE em segundo plano só para rádios próximos (RSSI ≥ −70 dBm); BLE que exija PIN aparece como erro no resumo em vez de solicitar o PIN; a disponibilidade Wi-Fi no seletor depende de o rádio aceitar conexão TCP naquele momento.

## v0.6.36 — Implementado nesta entrega

- Linux x64 e macOS (arm64/x64) adicionados ao pipeline e à release; ZIP de código-fonte removido dos downloads.
- #144, #145 e #146 implementados com testes automatizados (Python e Chromium). Aceite em campo pendente: confirmar com o rádio do usuário que os horários deixaram de ficar fixos em “há 3 minutos”.
- Pendências novas: assinatura/notarização Apple, atualização interna no macOS/Linux, janela nativa no Linux (GTK/Qt) e validação de BLE/serial nessas plataformas.

## v0.6.35 — Implementado nesta entrega

- Aviso de nova versão: pedido do mantenedor para o APRS Client, Sat Tool, Prop Tool, Mesh Analyzer e venus-8. Aqui, o diálogo de atualização existente abre automaticamente ao detectar versão nova; "Depois" adia 24 h.

## v0.6.34 — Implementado nesta entrega

Correções e critérios registrados no CHANGELOG: #138–#143; melhorias #59, #124, #125, #126 e #137. Aceite em rádio e Windows físicos pendente. A fila agrega consultas do backend com lotes da janela atual; persistência central dos lotes permanece pendente. Favoritos locais pendentes são mostrados separadamente da confirmação do dispositivo.

Continuam pendentes: tradução integral (#1), relatório avançado completo do modelo (#13), validação física de atualização (#103), confirmação de som/WebView2 (#126), e demais critérios não contemplados nas issues antigas abaixo. Esta versão não encerra automaticamente todas as issues.

## v0.6.33 — Entregas e pendências

- #80: novos padrões RF e Salvar automação destacado.
- #134: Sobre com WhatsApp +55 61 98402 3634 e e-mail alexpmr@gmail.com.
- #129: seletor emoji, contador 220 bytes UTF-8.
- #130: responder com citação textual em canal/DM; reply_id nativo ainda não garantido.
- #131: reenvio manual com aviso de duplicação e nova tentativa de TX. Falhas em sessão não necessariamente estão persistidas, investigar histórico de rejeições.
- #132: Canal primário fixo e favoritos do rádio em seção fixa.
- #136: aba Nós agora mostra estrela por rádio e permite Favoritar/Desfavoritar; o SDK oficial recebe o comando, mas a estrela só fica confirmada com o NodeDB. Aceite físico pendente.
- #137: Traceroute iniciado no mapa ainda não apresenta painel próprio de resultado; registrado para correção dedicada, não incluído nesta entrega.
- #79: importação read-only do NodeDB por origem implementada; escrita bidirecional/atualização sem reconexão depende de SDK e rádio real.
- Há muitas outras issues históricas abertas; não as fechar automaticamente nem alegar backlog integralmente sanado.

## P1 — Mensagens PING/CLIMA: preservar quebras de linha recebidas (18/10/2026)

- **Relato de campo:** o mesmo conteúdo de PING/CLIMA aparece corretamente com múltiplas linhas no Traffic Analyzer, mas no **PT2VHF Mesh Analyzer** é exibido como texto contínuo em uma única linha.
- O problema está no **renderizador/normalização do Mesh Analyzer**, não na origem da mensagem: a evidência mostra que o payload recebido contém quebras de linha e outro cliente as apresenta corretamente.
- Aplicar a correção a **PING, CLIMA e qualquer mensagem de texto multilinha**, sem tratamento especial que achate somente esses comandos.
- Preservar caracteres de nova linha (`\n` e `\r\n`) ao armazenar, recuperar via API e renderizar no balão da conversa.
- No HTML/CSS, usar renderização que respeite novas linhas, por exemplo `white-space: pre-wrap` ou equivalente seguro, sem exigir inserção de `<br>` não sanitizada.
- Não substituir quebras de linha por espaços durante sanitização, deduplicação, gravação SQLite, serialização JSON ou transformação para o modelo de mensagens.
- Manter quebra automática de linhas longas e largura responsiva do balão.
- Validar também mensagens recebidas por **Serial/USB, BLE e TCP/IP**, além de histórico recarregado após reinício.
- **Teste de regressão:** um payload `"linha 1\nlinha 2\nlinha 3"` deve continuar contendo as três linhas no banco/API e ser exibido visualmente em três linhas no WebView2.
- **Critério de aceite:** PING e CLIMA enviados pelo Traffic Analyzer devem aparecer no Mesh Analyzer com a mesma estrutura de linhas observada no cliente de origem.

## v0.6.32 — Atualização e reinicialização (#103)

- Teste de integração Windows com novo processo PyInstaller atrasado e launcher inicial encerrando exit=0.
- Exigir nonce, versão e UI pronta para confirmar atualização; ignorar servidor obsoleto ou respostas anônimas.
- Se o aplicativo correto já estiver em execução, diferenciar **instalado mas reinício não confirmado** de erro real de instalação.
- Pendente: comprovar atualização efetiva pelo aplicativo Windows 10/11 no PC afetado sem popup espúrio.

## v0.6.31 — Atualizador e ponte PDF/WebView2

- #103: logs de 17/10/2026 apontam regressão do `PDFExportBridge` público no `js_api`, levando pywebview a inspecionar propriedades nativas recursivamente. Alterado para atributo `_window` não exportado.
- #103: health check com versão/nonce/UI agora tem precedência sobre saída de PID transitório do PyInstaller; saída 0 sozinha é inconclusiva.
- Validar uma atualização real pelo app e exportar PDF no aplicativo Windows 10/11 após patch. Manter issue aberta até aceite.

## v0.6.30 — Interface Mapa e Mensagens

- #119: trocar legenda fixa grande por mini-legenda recolhível e conteúdo detalhado expansível.
- #120: autocomplete @ mantém sugestões mas insere nome longo sem @ e sem underscores.
- #121: filtrar a lista de nós em Mensagens enquanto digita, preservar canais e conversa selecionada.
- #118: indicador verde de versão atual já presente; validar regressão visual.
- Demais issues abertas exigem análise e testes separados, incluindo RF real, topologia e automações. Não declarar backlog global saneado.

## v0.6.29 — Reinício do Portable e confirmação pós-atualização (#103)

- Remove estado privado PyInstaller herdado no processo externo e antes do relançamento; usa ProcessStartInfo com UseShellExecute=false e reset explícito do runtime.
- Mantém perfil e porta na linha de comando; confirmação /health exige versão, nonce da tentativa e interface pronta. Janela de inicialização de 180 s com último estado HTTP diagnosticado.
- Aviso de falha persistido informa data e versão atualmente executada, sem declarar instalação manual defeituosa nem apagar evidência.
- Teste Windows pós-build com EXE real, nome versionado, pasta/perfil com espaços, ambiente temporário inválido, substituição, backup e preservação do nó salvo; UI readiness simulada via API em modo headless. Mantido teste onefile com encerramento do bootloader anterior.
- Não foi reproduzida a causa exata no PC afetado; ausência de logs e versões de origem/destino impede concluir causa única. Aceite físico Portable N→N+1 e WebView2 permanece pendente. Bootstrap manual necessário para versões com runner antigo. Ícone Windows #77 e botão verde #118 continuam fora deste escopo.

## v0.6.28 — Ícones por role do dispositivo

- Mapa com 13 ícones SVG customizados, papel desconhecido explícito e legenda recolhível. Atividade continua no contorno verde/âmbar; cliques e menu contextual preservados.
- `role` importada do NodeDB do device e das respostas NodeInfo em dicionário/protobuf, incluindo CLIENT numérico zero. Metadados parciais não apagam papel conhecido.
- Recuperação única de roles ausentes nos pacotes históricos, sem criar nós nem alterar last_seen ou posições.
- Testes de roles oficiais, consulta inicial, NodeInfo ao vivo, recuperação e SVGs reais. Validação física no rádio permanece necessária. Atualizador interno do Portable continua pendente (#103).

## v0.6.27 — Continuação: mensagens, automações e cabeçalho

Implementada correlação de ACK/NAK de texto, incluindo broadcasts, com timeout e sem inferir leitura. Automações ativas com tipos selecionados por migração única; suporte real continua restrito às capacidades do rádio. Contador redundante de conexões removido. Preservadas mudanças v0.6.23–v0.6.26 (seleção/lote/radar/temas/PDF/Win10). Aceite físico de mensagens e firmwares pendente. Atualizador automático foi confirmado sem erro pelo usuário em 16/10/2026; preservar diagnóstico de eventuais regressões.

## v0.6.26 — Compatibilidade Windows 10/11

- Ajustar pipeline de build, Setup Inno com mínimo Windows 10 1809 x64 e Portable Win10/11.
- Verificar geração, nomes dos assets e atualização automática de clientes antigos usando aliases Win11-x64.
- Testes automatizados de regressão, release e PE no CI; **pendente** aceite em Win10 real com WebView2 Runtime e drivers de rádio.
- Outros itens do backlog permanecem com suas issues independentes, sem fechamento automático.

## v0.6.25 — Escopo abordado

- #112: seleção de tema da interface Escuro/Cinza/Claro com persistência.
- #113: corrigir exportação PDF em Windows/WebView2 e browser; testar backend, HTTP e download.
- #114: iniciar Estatísticas com período Todo.
- Não considerar backlog histórico integralmente saneado sem testes e aceite específicos. Revisitar #90 e exclusão em lote #105 em hardware real.

## v0.6.24 — Feedback da v0.6.23 e correções implementadas na candidata

- Seleção múltipla e atualizador aprovados pelo usuário na v0.6.23.
- #105: excluir em bulk com confirmação individual do rádio, preservar banco em falhas e histórico; consultas bulk agora são enfileiradas mesmo quando já existe um lote em andamento.
- #108: opção Enlaces ligada somente para perfis sem escolha anterior; alterações de Ver persistidas.
- #109/#110: radar sem exibição quando OFF, invalidação de downloads antigos, slider maior/tempo real.
- #90: várias relações constam no mapa, mas linhas não aparecem; detalhar motivo e corrigir comparação de IDs. Aceite com dados reais/screenshot ainda pendente.
- Não considerar todo o backlog saneado sem a validação física.

## v0.6.23 — Implementação candidata da issue #105

- Seleção da aba Nós: clique simples, duplo clique, Ctrl, Shift e Ctrl+A sobre nós filtrados; seleção e contexto de múltiplos nós persistem entre atualizações da interface.
- Consultas em lote: NodeInfo/Posição/Telemetria/Traceroute com fila TX conservadora (60 s mínimo; 6/h neste lote), resposta individual/timeout, cancelamento dos próximos envios e relatório por nó. Nenhuma exclusão em massa.
- **Pendente de aceite:** pipeline Windows, testes físicos USB/BLE/TCP, observação de duty cycle conforme configuração regional, reinício automático do atualizador #103 e validação da remoção #102 em rádio real.
- Outras issues do backlog não são encerradas automaticamente pela publicação da v0.6.23.

## v0.6.22 — Exclusão individual e estilo dos fluxos RF

#102 implementada em menu contextual e detalhes, com confirmação nominal, comando ao rádio local, ACK/NAK correlacionado, timeout e preservação de histórico. Aceite físico pendente. #106 padroniza também communications.transport=radio em amarelo contínuo sem alterar evidência/ranking. #105 seleção múltipla e lote segue pendente. Não declarar remoção física universal sem teste de firmware.

## v0.6.21 — #103 / #106

Correções de ambiente PyInstaller, espera do bootloader, destino/log do Setup e estilo dos trechos RF. Testes automatizados locais e ciclo congelado Windows no CI. Aceite físico ainda pendente; não fechar issues por compilação. Instalação manual da v0.6.21 necessária para passar a usar o runner corrigido em atualizações futuras. #102 e #105 continuam pendentes.

## v0.6.20 — Consultas RF (#104)

Implementado timeout uniforme de 30 s contado após envio pelo SDK, com relógio monotônico, recuperação sem polling, proteção de duplicatas em envio e invalidação ao trocar interface. Testes automatizados cobrem os quatro tipos. Aceite físico pendente. #102 (exclusão em dois destinos), #103 (updater) e #105 (seleção/bulk) permanecem abertas, não implementadas nesta release.

## P1 — Rota de 3 nós desaparece parcialmente após minutos (15/10/2026)

- **Relato v0.6.7:** usuário viu caminho com três nós e, após alguns minutos, um nó/trecho sumiu da visualização, sobrando apenas duas estações. **Issue [#53](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/53)**, vinculada à [#22](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/22). Confirmar se desapareceu o **marcador** ou um dos dois **segmentos** da rota.
- **Regra esperada:** enlaces, nós e rotas históricos **não expiram** por ficar offline nem por terminar a animação. Retenção padrão SQLite é **Nunca** (`0`); somente apagar por exclusão explícita ou retenção configurada. Não sobrescrever a topologia A→B→C quando uma observação mais nova mostrar apenas A→B. Nunca substituir trechos comprovados por ligação artificial A↔C.
- **Diagnóstico necessário:** instrumentar contagem e razão por trecho `gravado no SQLite / oculto pelo período / fonte incompatível / observações mínimas / pesquisa / ponta sem GPS / coordenada temporal inadequada / desenhado`. `renderMap()` recria overlays; separar desaparecimento visual de remoção de dados. `sourceMapNodes()` usa somente nós observados na conexão selecionada; `mapWindow` filtra `last_seen_ms`; ambas as pontas precisam `validPos()`. Guardar versões históricas das posições para móveis.
- **Critérios de aceite:** vista padrão **Todos** com três nós e dois trechos históricos preservados por horas/dias, inclusive offline, F5/reinício, nova rota parcial e múltiplas fontes; distinguir atividade recente de histórico por estilo e rótulo, sem falsos enlaces RF. Lista de enlaces inclui relações sem posição com motivo. Configurações do usuário jamais alteradas silenciosamente.
- **Triagem:** conferir **Configurações → Mapa → Janela = Todos**, **mínimo de observações = 1**; na aba Mapa, **Conexão = Todas**, busca vazia e **Ver → Enlaces** habilitado. Se reproduzir nessas condições, coletar Node IDs dos três nós e diagnóstico do SQLite; não limpar banco. **Status:** reportado e registrado, não corrigido na v0.6.7.

## v0.6.7 — Correções em validação (15/10/2026)

- **Instalador bloqueado (#15/#34):** script externo fecha exclusivamente as instâncias do Mesh Analyzer do mesmo usuário e mesmo caminho de EXE, com encerramento gracioso e fallback restrito aos PIDs validados, ou interrompe instalação se falhar. Registrar `installer-close.log`. Não garante ainda que a atualização automática funcione até teste físico.
- **Ícone antigo (#40):** ICO instalado em caminho estável, usado também pelos atalhos e pela janela WebView2. Confirmar comportamento do Windows 11 e cache de atalhos fixados.
- **Cabeçalho:** verde quando rádio USB/BLE/TCP realmente conectado, vermelho quando desconectado; MQTT não conta como rádio. Tooltip por conexão.
- **Enviar offline (#45):** popup com “Não há conexão ativa com um rádio Meshtastic para enviar mensagens”, opções **Ir para Conexões** e **Fechar**, sem perder o texto digitado e sem TX.
- **Popup de enlace (#51):** primeira implementação de `linkPopupHtml()`/`attachLinkPopup()` para RF, rota observada e comunicação lógica: nós clicáveis, qualidade da evidência, fonte, datas, contagens e distância geográfica temporalmente confiável. **Pendentes:** evidências RF detalhadas e métricas RSSI/SNR/hops por segmento, filtros de pacotes e validação visual WebView2.
- **Não concluídos:** consultas remotas, ACK/REJ de entrega com correlação, leitura humana comprovada, LAN autenticada, i18n integral e dezenas de outras issues. Nenhum recurso depende de criar dados fictícios.

## #51 — Popup completo ao clicar em enlace no mapa (15/10/2026)

- **Pedido com imagem de referência:** clicar em qualquer linha de enlace ou fluxo lógico no Mapa deve abrir uma **janela de detalhes do enlace**; atualmente `renderMap()` utiliza somente `bindTooltip` e não disponibiliza popup com métricas.
- **Conteúdo:** nomes amigáveis e Node IDs de ambas as pontas, tipo/qualidade da relação, fonte, primeira/última observação, quantidade de pacotes, horários, distância entre coordenadas confiáveis, origem da descoberta e evidências de traceroute/neighbor/RF/MQTT. SNR, RSSI, saltos e histórico apenas quando o banco conseguir rastrear amostras daquela aresta; sem valores artificiais.
- **Classes distintas:** **RF direto comprovado**, **trecho de traceroute observado**, **vizinhança anunciada**, **comunicação lógica com caminho físico desconhecido**, **Internet/MQTT**. Linhas lógicas não entram em rankings RF direto e nunca recebem rótulo de hop confirmado só por unicast.
- **Ações:** abrir informações completas de cada nó (#27), ver pacotes relacionados, copiar metadados e fechar; preservar filtros de Conexão/período, enlaces antigos/offline e contexto de nós móveis (posição no tempo do evento, não atual se incoerente).
- **Implementação:** `links`/`communications` existentes trazem metadados agregados, mas não armazenam necessariamente RSSI/SNR por aresta. Criar identificação estável da relação, API de evidências associadas com limites/segurança e popup Leaflet/compartilhado, sem cruzar medição de pacote multissalto como se fosse do segmento. Clique/teclado/Escape, responsividade, nomes sanitizados, Win11 WebView2.
- **Issue:** [#51](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/51). **Status:** popup básico implementado em branch v0.6.7; métricas de RF detalhadas ainda pendentes, e recurso não está publicado na v0.6.6.

## v0.6.7 — Mensagens: aviso quando rádio estiver desconectado (14/10/2026)

- **#45:** botão Enviar permanece clicável mesmo sem rádio TX ativo para abrir popup explícito **“Não há conexão ativa com um rádio Meshtastic para enviar mensagens”** com as ações **Ir para Conexões** e **Fechar**. Ir abre `Configurações → Conexões`; Fechar retorna à conversa. Mensagem digitada preservada. Nenhum pacote é transmitido enquanto desconectado.
- **Critério de aceite:** sem rádio cadastrado, rádio desligado, conexão desativada, MQTT observador e driver sem TX exibem explicação adequada; ao conectar rádio realmente capaz de transmitir, Enviar opera normalmente. Testar Win11/WebView2 e reconexão.
- **Status:** implementação em branch e testes automatizados; pendente merge/publicação e validação real.

## v0.6.6 — Itens em revisão (14/10/2026)

- **Implementação candidata:** #49 migração de Camadas para Ver, #48 broadcast amigável, #47 e #35 tipos/hardware amigáveis.
- **Correções parciais:** #8 saltos por pacote e identidade local para distância; #45 rádio TX elegível com explicação; #4 estados honestos de envio; #46 menu contextual compartilhado apenas nas operações disponíveis.
- **Sem falsas confirmações:** ✓ significa aceitação do rádio local; ACK não é leitura e não gera ✓✓. Consultas remotas RF não suportadas permanecem desabilitadas.
- **Validação pendente:** hardware Meshtastic real, Windows 11 WebView2, atualização/reinício #34, mensagens/ACK #45/#4, BLE/Serial/TCP, distância GPS, menu Ver com radar/relevo. O backlog não está integralmente encerrado.

## Mensagens e menu do nó — pendências v0.6.5 relatadas em campo (14/10/2026)

- **P0 — [#45](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/45): Enviar desabilitado.** Na aba Mensagens, o botão Enviar permanece cinza e o usuário não consegue enviar. Análise: `renderChat()` desabilita a ação se `state.sources` não tiver fonte habilitada, diferente de MQTT, com `state.connections[source_id].status === 'connected'`. **Não assumir falta de rádio como causa sem diagnóstico**: validar estado TX real dos drivers Serial/BLE/TCP, reconexão, seleção de fonte, channel, WebView2, dados de resposta de `/api/state`, e corrigir divergência UI/backend. Exibir razão específica de indisponibilidade; reabilitar com rádio utilizável e texto válido; manter rascunho na falha. Testes reais de TX, privadas e canais.
- **P1 — [#4](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/4): interface de mensagens no estilo WhatsApp.** Balões TX direita/RX esquerda, lista de conversas organizada por atividade, cabeçalho do nó, avatar genérico, prévia/horário/não lidas, agrupamento de mensagens, separadores de data, tema e compositor responsivo/contador de bytes UTF-8. O design terá identidade PT2VHF, com experiência visual familiar ao mensageiro, sem reproduzir marca proprietária.
- **P1 — #4: estados verdadeiros.** Relógio durante fila/envio; **✓** quando o rádio local aceitou enviar; **✓✓** **exclusivamente** quando um aplicativo compatível do nó remoto comprovou ter aberto/lido aquela mensagem. ACK Meshtastic de transporte/entrega é **separado** de confirmação de leitura; nunca gerar ✓✓ artificial ou tratar ACK como leitura humana. Falha/REJ/timeout com erro e reenvio controlado, histórico de estados e correlação por fonte/Node ID/canal/packet ID. Sem recibo remoto suportado, manter ✓ e tooltip de ACK eventual. Não marcar canal/broadcast como lido por destinatário único.
- **P1 — [#46](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/46) / [#27](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/27): menu contextual compartilhado.** Botão direito sobre nó do **Mapa**, linha da aba **Nós** e contato/nome de remetente/cabeçalho da aba **Mensagens** abre mesmas opções: **Enviar mensagem**, **Informações completas**, **NodeInfo**, **Posição**, **Telemetria**, **Traceroute**, **Ping**, Vizinhos e outros somente se firmware e driver suportarem; **Copiar Node ID** e **Mostrar no mapa** quando possível. Reusar mesmo executor/estado de consultas, acompanhar respostas e timeouts individualmente, sem enviar TX até ação explícita. MQTT RX e rádios desconectados têm comandos RF bloqueados com explicação. Nó sem GPS continua acessível.
- **UI atual:** `marker.on('click',()=>showNode(n))` não define contextmenu, tabela `renderNodes()` navega para Mapa ao clicar e `renderChat()` não define ações contextuais; botões de consulta em `nodePopupHtml()` permanecem desabilitados, sem endpoints reais no backend. Portanto a UI futura não deve prometer consultas não implementadas nem fingir resposta a ping.
- **Aceite:** em Win11/WebView2, com 0/1/vários rádios USB/Serial, BLE e TCP/IP, MQTT observador, rede em funcionamento, canais/privadas, acentos, timeout/reenvio e nós sem posição. Validar visualização, disponibilidade do Enviar, transmissão real, estados de mensagem corretos, clique direito em três abas e respostas reais das consultas. **Status: backlog registrado, não implementado na release v0.6.5.**

## v0.6.5 — Implementação parcial, aceite em campo pendente (14/10/2026)

- **#22:** descoberta passiva de comunicações unicast origem→destino a partir de pacotes normais e recuperação histórica em lotes idempotentes, com linhas lógicas pontilhadas distintas de RF comprovado; zero-hop RF somente receptor local conhecido + SNR presente + sem retransmissão informada.
- **#11:** novos pacotes normais produzem atividade no mapa sem exigir traceroute ou controle "Realçar origem", mesmo sem posição há feedback textual. Continua pendente a animação de percurso de saltos conhecidos reais, replay avançado, múltiplos receptores e telemetria fina.
- **#2:** iniciar download ao clicar no indicador do cabeçalho, sem confirmação do browser nem modal intermediário, cancelável durante a transferência do pacote; nunca cancelar após a fase de instalação irreversível.
- **#34 — REINCIDÊNCIA CONFIRMADA:** após download o app fecha e instalação/reabertura **aparentemente não acontecem** no Win11 do usuário. O runner candidato detecta Setup em caminhos personalizados, registra relançamento e usa alerta externo em caso de falha; antes de fechar a versão atual, exige confirmação do processo externo via nonce em disco. O Setup agora usa /SILENT para mostrar seu progresso e registra as etapas de instalação em log; **sem logs do Win11 ainda não há causa raiz demonstrada nem solução confirmada**. Coletar `update.log` / `update_complete.json`. Testar tanto Inno Setup quanto Portable com dados reais; não encerrar essa issue só por compilação.
- **Pendente:** paridade integral legado, parser completo relayNode, recepção direta validada com hardware, rotas RF temporais, segurança LAN, i18n, NodeDB e todo o restante do backlog. Nenhuma issue com aceite físico deve ser encerrada sem ensaio.

## P1 — Recuperar descoberta passiva pelo tráfego comum do Traffic Analyzer legado (15/10/2026)

- **Correção do usuário:** o Traffic Analyzer legado visualiza comunicação/atividade e relações detectadas ao ouvir pacotes normais; não depende apenas de traceroutes. O Mesh Analyzer tem de reconstruir topologia **passivamente a partir do fluxo recebido**, preservando níveis de certeza. Referência de código: `alexpmr/traffic-analyzer/traffic_analyzer_web.py::_archive_links_query()` (agrega from→to lógico) e `animatePacketActivityNow()` (pulsos no originador e relay), além de `traffic_analyzer.py::build_topology()` (hops de traceroute).
- **Três categorias distintas:** (1) **Comunicação lógica observada** entre `from` e `to` de pacote normal (caminho desconhecido, não RF direto); (2) **Retransmissor/recepção observados** por `relayNode` univocamente resolvido e receptor local conhecido, quando origem do rádio comprovada; (3) **Adjacência física RF confirmada** por evidência do hop rastreável (não por TTL/hop counts ou endereço remoto apenas). Segregar adicionalmente transportes RF vs MQTT/Internet e broadcast.
- **Ingestão de cada pacote:** salvar fonte, receptor, origem, destino, timestamp, direção, canal, portnum, `relayNode`, SNR/RSSI, `hopStart`/`hopLimit`, transporte e referência à evidência bruta; não duplicar mesma recepção nem colapsar receptores diferentes. `relayNode` de 8 bits pode ser ambíguo: não atribuir Node ID por mera similaridade.
- **Mapa `Ver → Enlaces`:** apresentar as classes observadas com legenda e subfiltros, inclusive comunicações lógicas quando nenhum traceroute foi realizado, sem fingir salto direto entre nós. Persistir agregados e histórico de nós antigos/offline; usar coordenadas válidas da época ou listar relações sem geometria; evitar enlaces esticados de móveis.
- **Animação `Ver → Animar tráfego`:** animar tráfego normal com pulso em nó/receptor e relay apenas quando resolvido, movimento em trechos realmente observados, evento em painel quando faltar posição, indicação própria para MQTT. Tornar controle independente de `Realçar origem`, manter desempenho e deduplicação; não executar TX nem disparar traceroutes automáticos para desenhar o mapa.
- **Reprocessamento histórico:** buscar evidências já salvas em `packets` e `raw_json`, em lotes idempotentes, sem perder histórico ou transformar fluxo A→B em enlace físico. Distinguir contagem de comunicações, adjacências, RF direto e enlaces efetivamente desenhados. Ranking RF direto continua rigoroso.
- **Aceite:** centenas de pacotes normais sem traceroutes geram comunicações lógicas e animações quando elegíveis; relays confirmados aparecem como eventos com fonte; caminhos desconhecidos ficam rotulados; RF direto exige evidência; filtro, retenção, múltiplas fontes, MQTT/broadcast e nós móveis não criam falsos enlaces.
- **Rastreio:** [issue #22](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/22) e [issue #11](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/11) atualizadas após comparação com o código legado. **Status:** backlog documentado; a v0.6.4 ainda não implementa essa integração passiva.

## P1 — v0.6.4: enlaces ausentes e animação do tráfego não funciona (15/10/2026)

- **Relato direto em campo:** mesmo após instalar/usar v0.6.4 e ter o novo menu **Ver**, **os enlaces continuam ausentes** e **a animação de tráfego não aparece**. Problemas não resolvidos: [#22 — Enlaces](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/22) e [#11 — Animação](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/11). Não fechar por haver checkboxes ou testes de compilação.
- **Causa/limites identificados no código:** extração topológica baseada em `TRACEROUTE_APP` e `NEIGHBORINFO_APP`; `renderMap()` exige arestas do SQLite elegíveis por Conexão/período/mínimo de observações/busca + posições válidas para AMBAS pontas + `showMapLinks`. O menu `Ver → Enlaces` só controla visibilidade; não cria evidência.
- **Animação atual é incompleta:** `pulseNewPackets()` recebe atualização por polling de 4 s, ignora primeira carga e pacotes MQTT, exige `mapAnimateNodes` E `mapHighlightSource`, posição válida de `from_node`; apenas pulsa círculo no originador. **Ainda não há deslocamento de pacotes por segmentos RF efetivamente confirmados**, nem indicação visual/diagnóstica adequada para pacotes sem GPS.
- **Implementação requerida:** (a) diagnóstico estruturado e visível das etapas recepção→topologia→SQLite→API→filtro→geometria→Leaflet, com motivações de exclusão e correções de parser/conversão; (b) reprocessamento seguro de históricos não interpretados; (c) animação baseada em eventos RF observados, vários pacotes simultâneos, fonte, sentido, portnum e timestamps, velocidade/pausa, feedback para eventos sem posição, sem caminhos RF fictícios nem confusão MQTT; (d) desvincular `Animar tráfego` de um toggle independente `Realçar origem` que hoje silencia a funcionalidade, sem perder preferência de destaque; (e) assegurar que selecionar/ocultar camadas não apague histórico.
- **Aceite obrigatório:** teste ponta a ponta em Windows 11/WebView2 com fonte rádio e banco real, incluindo enlaces que têm GPS, os que não têm, relays/multissalto, móveis com posições temporais, MQTT, 0/1/N fontes, filtros e histórico. Indicar total existente, desenhado e causa de invisibilidade; validar animações em evento real. **Estado: pendente — não publicado/corrigido na v0.6.4.**

## P0 — Atualizador v0.6.3 → v0.6.4: dois defeitos reproduzidos em campo (15/10/2026)

- **#2 — Fluxo de atualização ainda possui dois diálogos indevidos:** primeiro o modal de changelog/"Atualizar agora", depois a confirmação nativa do navegador ("127.0.0.1:8789 diz"). A partir do indicador laranja, o usuário quer **um único clique**, início do download oficial e um único modal de progresso em tempo real, sem intermediação. Changelog só depois do reinício realmente concluído.
- **#34 — Fechou e instalou, mas não voltou a abrir:** reincidência do problema em Windows 11 no upgrade v0.6.3 para v0.6.4. A implementação atual do runner PowerShell oculto não oferece mecanismo externo visível de recuperação; investigar caminho de EXE, PID, porta local, /health, ui_ready, Setup/Portable e logs.
- **Evidência para coleta:** `%LOCALAPPDATA%\PT2VHF-Mesh-Analyzer\update.log` e `update_complete.json` (se presentes); registrar edição Setup vs Portable, se atalho abre manualmente e qual versão instalada aparece. Não descartar logs nem apagar banco.
- **Critérios para fechamento:** atualização em um clique, SHA256 válido, progresso real, encerramento controlado, nova versão reaberta automaticamente com confirmação de WebView2 e versão; falha diagnosticada e recuperável por janela externa. Validar Setup→Setup e Portable→Portable no Windows 11; preservar o SQLite e a configuração do usuário.
- **Status:** apenas documentado no backlog/issue nesta etapa; correção ainda pendente, não foi publicada nos binários v0.6.4.

## v0.6.4 — Implementado em código, requer aceite no Windows 11

- **#40:** ícone nativo `.ico` atribuído à janela `pywebview.start` e incluído no PyInstaller; aguarda captura real da barra de tarefas e validação com atalhos antigos.
- **#42:** `mapSourceState` excluído de CSS/HTML/JS, preservado `mapSource`, suas opções e o contador de Conexões ativas em Resumo.
- **#20:** menu **Ver** na faixa secundária: Nós / Enlaces / Waypoints / Animação do tráfego, selecionar/remover tudo, filtros imediatos, contagens; configurações de visualização persistentes quando salvas. Backend `WAYPOINT_APP` com SQLite, API e camada do mapa; remover nunca apaga históricos.
- **Pendente para encerrar #20:** teste real com múltiplas fontes e waypoints/Protobuf de diferentes firmwares, performance, período histórico e experimento com WebView2; complementos avançados do filtro de proveniência dos nós (#20) não são automaticamente considerados prontos.
- **Não foram implementadas nesta release todas as 32+ issues, entre elas:** LAN autenticada #3, detecção BLE/rede #31, i18n #1, edições remotas completas #6, sincronização NodeDB/favoritos #29, paridade integral Traffic Analyzer #10, estados de entrega Chat #4 e fechamento definitivo do updater #34.
- **Status:** build automatizado e teste offline necessários; não fechar issues com pendências sem verificação.

## Menu VER na faixa secundária/inferior do Mapa — referência visual (15/10/2026)

- **Solicitação atualizada do usuário:** adicionar botão drop-down **`Ver ▼`** à faixa de controles da aba **MAPA**, situada abaixo do menu principal (faixa secundária/inferior), com visual semelhante à captura fornecida do PT2VHF APRS Client. A posição mais recente substitui o requisito anterior de ficar obrigatoriamente ao lado de Conexão se o layout assim exigir.
- **Itens independentes:** checkboxes **Nós**, **Enlaces**, **Waypoints** e, opcionalmente, **Animação dos pacotes**. Cabeçalho **VER**, **Selecionar tudo** e **Remover tudo**, suportando indeterminação do checkbox pai quando houver subcategorias.
- **Grupos facultativos:** papéis reais Meshtastic para nós (se disponíveis), tipos de enlace por evidência real (RF direto comprovado, rota observada, MQTT/Internet); **não** copiar indiscriminadamente categorias APRS como iGate/digipeater.
- **Persistência e segurança:** refletir imediatamente no Leaflet sem refresh; sincronizar com `showMapNodes`/`showMapLinks`, fonte, busca, período e preferências do SQLite; a ação de ocultar nunca remove informações históricas, nem altera TX, retenção ou evidência RF.
- **Waypoints:** implementar ingestão e armazenamento de `WAYPOINT_APP` com posição válida, origem, tempo e fonte, endpoints e camada de ícones próprios; em ausência de waypoints usar contagem zero sem elementos fictícios. Hoje não há suporte especializado completo no backend.
- **Layout:** menu não pode cobrir permanentemente outros controles; usar Escape/clique externo, teclado, contraste e responsividade Win11/WebView2.
- **Integração:** [issue #20](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/20) foi refinada com os detalhes da captura. **Status: backlog, não implementado nos binários v0.6.3.**

## #42 — Retirar texto redundante da barra superior do Mapa (15/10/2026)

- **Relato com captura:** remover o indicador textual **“Todas as conexões · N”** ao lado do seletor de Conexão na barra de controles do mapa. Quando uma conexão específica for selecionada, **também não mostrar** o texto lateral “Nome · status”.
- **Onde:** `mesh_analyzer/ui.html`: retirar o elemento `<span id="mapSourceState">` na faixa `#playback`, a atribuição `$('mapSourceState').textContent` em `renderMap()` e o CSS dedicado a `#mapSourceState`.
- **Manter:** o próprio seletor `Conexão:` / `Todas as conexões`, seleção/filtro `mapSourceFilter`, persistência, contador independente de conexões ativas no resumo e informações disponíveis em Configurações.
- **Aceite:** zero/uma/várias conexões, status online/offline, Win11 WebView2, sem espaços desnecessários ou erros JS. Issue [#42](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/42).
- **Status:** backlog registrado; aguarda implementação na próxima release, sem alteração nos binários da v0.6.3.

# Backlog — PT2VHF Mesh Analyzer

Esta é uma linha nova: não confundir com o projeto PT2VHF Traffic Analyzer v1.x.

## v0.6.3 — Progresso no backlog (pendências preservadas)

- **#34/#15/#2:** correção de *falso sucesso* no atualizador com verificação de versão e carregamento do frontend via `/health`, erro persistido e rollback limitado para Portable. **Manter aberta até teste real no Windows 11.**
- **#33:** implementados indicadores de saúde e backup transacional. **Pendente:** prévia de limpeza, restore testado, monitoramento de crescimento e recomendações.
- **#35:** apelido local de nós persistente e apresentação preferencial em partes da interface. **Pendente:** abrangência em todas as visualizações e conflitos com múltiplos nomes.
- **#30:** LEDs TX/RX baseados em contadores novos do driver, sem falso RX MQTT e TX baseado em solicitação aceita. **Pendente:** telemetria fina e validação com hardware.
- **#37:** F5 não reapresenta popup na sessão e modal de novidades tem prioridade. **Pendente:** testes UI reais e reinício WebView2.
- **As demais issues #1–#37 continuam abertas no GitHub até cumprirem integralmente seus critérios de aceite.** Esta release não resolve integralmente o backlog.

## v0.6.2 — Implementações para testar no Windows 11 (14/10/2026)

- **#37 (código):** popup inicial condicionado a `/api/state.sources.length === 0`; botões Ir para conexões e Agora não. Clique direciona para Configurações → Conexões e foca o formulário, sem reexibir em polling de 4 s. Fontes cadastradas porém desconectadas não ativam o aviso.
- **#36 (interface):** rótulos e documentos renomeados para Conexões preservando identificadores `sources`/SQLite/API. Conferir se há textos residuais e futuras traduções não cobertas.
- **#21 (UI):** versão e título com tamanho equivalente, marca ampliada, estado de conexões removido da linha de marca, contador mantido nos indicadores, menu Mensagens depois de Mapa.
- **URLs de Configurações:** `/configuracoes/conexoes`, `/dispositivo`, `/retencoes`, `/mapa`, `/sistema`, `/geral` com renderização após F5.
- **Qualidade:** testes offline e rotas HTTP adicionados. **Issues só devem ser encerradas após validação real de Setup/Portable, teclado/sem conexão e diferentes resoluções.** Nenhum compromisso de concluir integralmente as demais issues do projeto nesta release.

## v0.6.1 — Identidade visual instalada no projeto (revisão Windows pendente)

- Logo exclusivo **PT2VHF Mesh Analyzer** (antena + ondas LoRa + relevo + nós mesh), arquivo matriz PNG base64 SHA256 em `branding/`; ícone multirresolução gerado como `.ico`/PNG por `branding/build_icons.py`.
- A mesma identidade foi integrada no cabeçalho, favicon, build do EXE PyInstaller, instalador Inno Setup, atalhos Iniciar/Área de Trabalho e AppUserModelID estável da janela Windows WebView2 para barra de tarefas. **Verificar em Win11 real, incluindo atalhos já fixados**. Alteração somente visual/empacotamento.
- As issues abertas de RF/enlaces, atualizador, idiomas, chat, favoritos/sincronização, fontes e outras funcionalidades não são declaradas resolvidas por esta alteração.

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

## v0.6.0 — progresso de implementação (sem alegar conclusão total)

- **#15/#2**: desligamento ordenado e autoencerramento do aplicativo após preparação do pacote; teste real Setup/Portable com Windows 11 e dispositivos conectados ainda necessário. Não há força contra processos de terceiros.
- **#8**: ordenação padrão Distância ▲ desde rádio local já implementada; validar preferências antigas, GPS e múltiplas fontes.
- **#25**: botão Salvar com persistência de Mapa/Sistema/Retenções no SQLite e status de mudanças pendentes. Editor rádio e Fonte separados; faltam transação multi-grupo e testes UI operacionais.
- **#26**: aviso de Automações em breve na interface, sem execução fictícia.
- **#27**: popup redimensionável/arrastável com dados do banco, posição opcional e histórico; **consultas individuais/Tudo e respostas reais ainda pendentes** (não simuladas).
- **#10**: formato das tabelas de ranking/rotas/tráfego/consultas/chat/energia/atenção ampliado, sem inferência RF direta. Paridade integral das dez subabas e consultas correlacionadas ainda pendente.
- **NÃO IMPLEMENTADO/VALIDADO NESTA RELEASE:** #1 idiomas completos, #3 LAN autenticada, #6 edição integral e backup/restauração completos, consultas ao rádio #27, #13 PDF avançado com todos os relatórios, #4 chat integral e critérios pendentes em #9–#12, #16, #18, #20–#22. **Todas as issues continuam abertas até seus critérios de aceite serem cumpridos.**

## Nós: distância crescente por padrão (14/10/2026)

- [**#8 — Ordenação automática por distância**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/8): primeira execução deve ordenar **Distância ▲**, do nó mais próximo ao mais distante, com referência no rádio local conectado Serial/USB, BLE ou Wi-Fi/TCP, sem referência arbitrária em MQTT. Distância numérica real em km, empates estáveis, sem coordenadas no final (sempre) e atualização com mudança da fonte/posição. Respeitar ordenação escolhida e persistida pelo usuário. A v0.5.0 ordena por `Última interação ▼`; **pendente para a próxima release**.

## Interface: salvar Configurações e aviso em Automações (14/10/2026)

- [**#25 — Botão global "Salvar configurações"**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/25): adicionar botão fixo/visível em Configurações, como no PT2VHF APRS Client, com estado **Alterações não salvas**, **Salvando**, **Salvo às HH:mm:ss** e erro recuperável. Gravar preferências de Mapa, Sistema, Geral e Retenções somente após confirmação da persistência (preferencialmente SQLite), preservar alterações ao trocar subabas, avisar ao sair com mudanças pendentes e não confundir mudanças já aplicadas com alterações ainda não salvas. **Salvar fonte e Salvar todas as alterações do rádio continuam operações separadas**; o botão global não pode enviar comandos RF, apagar dados nem instalar atualização. Sem salvar automaticamente alterações perigosas. **Pendente após v0.5.0.**
- [**#26 — Automações: mostrar aviso "Este recurso será implementado em breve"**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/26): manter a aba e a URL `/automacoes`, substituir o atual cartão "Arquitetura preparada para bots" por mensagem explícita de **funcionalidade em desenvolvimento**, com texto **"Este recurso será implementado em breve."** e **"Nenhuma automação está ativa nesta versão."**. Podem ser mencionados bots PING/CLIMA, consultas programadas e regras de eventos como ideias futuras, sem indicar que já funcionam ou prometer prazo/release. Aviso legível em desktop/resize, sem botão de ativação ou transmissão RF. **Pendente de implementação após v0.5.0.**

## Cabeçalho ampliado — logo, título/versão proporcionais e status menos poluído (14/10/2026)

- [**#21 — Identidade visual, ajuste da captura da v0.6.1**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/21): **aumentar um pouco** a área completa da marca (logo ~54–58 px, título e subtítulos), exibindo **vX.Y.Z no mesmo tamanho e peso visual do nome PT2VHF Mesh Analyzer**, sem `<small>` diminuindo a versão. **Remover `N fonte(s) conectada(s)` somente da primeira linha da barra superior** (`#connectedStatus`), preservando contagem operacional de conexões na faixa de KPIs ou telas próprias. Não prejudicar o botão de atualização, menus/LEDs ou janelas menores. Também respeitar a terminologia **Conexões**, conforme #36. Pendente na v0.6.1.

## Primeira execução sem conexões e nomenclatura Conexões (14/10/2026)

- [**#37 — Primeira inicialização sem conexões cadastradas**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/37): ao entrar no app, **somente quando o SQLite/API informar `state.sources.length === 0`**, mostrar **popup central**: **"Configure sua primeira conexão"** e texto explicando que é preciso cadastrar USB/Serial, BLE, Wi-Fi/TCP ou MQTT RX para receber dados. Botão **"Ir para Conexões"** fecha o modal e executa **`setView('settings')` + `showSettings('sources')`**, abrindo **Configurações → Conexões → Adicionar conexão** com foco no primeiro campo. Botão **"Agora não"** fecha sem bloquear a navegação.
- **Não confundir sem cadastro com desconectado:** uma conexão salva porém desativada, indisponível ou offline **não** dispara aviso. Erro de consulta/API e estado carregando **não** devem gerar falso alerta. Verificar apenas após o **primeiro GET /api/state bem-sucedido**, mostrar uma vez por sessão/inicialização (não a cada polling de 4 segundos, troca de aba ou F5); se continuar sem conexões, reapresentar em próximo início real. Se changelog pós-upgrade também for exibido, sequenciar janelas sem sobrepor.
- [**#36 — Renomear Fontes → Conexões na interface**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/36): aplicar **Conexões** em Configurações, textos dos blocos (Adicionar/Editar/Salvar conexão), filtros Mapa/Tráfego/Estatísticas, Conexão TX em Mensagens, status, notificações, tooltips, Ajuda, CSV/PDF e futuras traduções. **Não renomear variáveis, tabelas SQLite `sources`, IDs DOM, rotas `/api/sources` ou JSON `source_id`**; preservação retrocompatível. Na primeira inicialização, o botão vai para **Conexões**, embora o ID interno da subaba permaneça `sources`.
- **Ambos são backlog** e não foram implementados na v0.6.1. Validar em Windows 11 WebView2, Portable/Setup, em sistemas sem cadastro, com conexão desativada, banco indisponível, múltiplas conexões, modal de novidades e reinicialização.

## Cabeçalho: LEDs TX/RX e Mensagens após Mapa (14/10/2026)

- [**#30 — LEDs de tráfego estilo modem antigo**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/30): inserir no cabeçalho superior dois LEDs compactos com rótulos fixos: **TX vermelho** (atividade real de envio pelo rádio local conectado) e **RX verde** (pacote realmente recebido por Serial/USB, BLE ou Wi-Fi/TCP). LEDs apagados quando inativos, pulsos rápidos de cerca de 150–250 ms, independentes e simultâneos. Multiplas fontes com proveniência; nunca piscar por F5, refresh/contagem histórica, cache de NodeDB, MQTT como falso RF TX nem por apenas clicar no botão Enviar. Tooltips/estados e acessibilidade, Win11 WebView2, desempenho sob rajadas e testes com hardware. **Pendente após v0.6.0.**
- [**#21 — Alterar ordem do menu superior**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/21): **Mapa | Mensagens | Nós | Tráfego | Estatísticas | Automações | Configurações | Ajuda**. A aba **Mensagens passa imediatamente após Mapa**, preservando ordem relativa das demais; não alterar nomes técnicos `data-view`, rotas, abas ativas, favoritos, navegação/teclado nem a linha abaixo do título. Layout responsivo sem sobreposição com TX/RX da #30. **Pendente após v0.6.0.**

## Mapa: enlaces ausentes, Mostrar/Ocultar e animação; instalador multilíngue (14/10/2026)

- [**#22 — Enlaces não aparecem, reincidência na v0.6.0**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/22): **prioridade alta**. Investigar toda a cadeia RF/route/neighbor → SQLite → API → filtros → Leaflet, mesmo após correções anteriores. Contar links armazenados, observados, elegíveis e desenhados; explicar se há ausência de posição válida, filtro Fonte, janela temporal, mínimo de observações, busca ou erro de geometria. Não confundir `0 desenhados` com `0 detectados`; não fabricar RF direto nem projetar posições históricas de móveis para o local atual. Teste de ponta a ponta com tráfego Meshtastic físico e banco histórico.
- [**#20 — Mostrar/Ocultar ao lado de Fonte, barra superior do Mapa**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/20): criar menu pull-down `Mostrar/Ocultar ▼` com checkboxes **Nós**, **Enlaces** e **Waypoints** e, opcionalmente, **Animação do tráfego**. Padrão visível; ações imediatas sem apagar SQLite; filtros combináveis com Fonte, busca, período e camada. Preferências sincronizadas com Configurações → Mapa e persistidas ao clicar em Salvar. **WAYPOINT_APP** exige decodificação, armazenamento e renderização de coordenadas reais em camada independente; se ainda não houver suporte, deixar ausência explícita, sem marcador inventado.
- [**#11 — Animação real de tráfego**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/11): evoluir dos pulsos atuais no nó emissor para animações das transmissões RX/TX e trechos **efetivamente comprovados**, múltiplos eventos, controle de pausa/velocidade e desempenho. Nunca interpolar RF entre origem e destino sem evidência do hop; distinguir MQTT/Internet, posições móveis e nós sem GPS, e preservar enlaces históricos sem expirar ao terminar o efeito visual. **Pendente após v0.6.0**.
- [**#1 — Seleção de idioma no instalador Inno Setup**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/1): oferecer **Português (Brasil), English, Español, Français, Deutsch e Italiano**. Detectar idioma do Windows, permitir seleção manual no início, traduzir todas as etapas, mensagens, erros e textos personalizados de `[Tasks]`/`[Run]` por `[Languages]`/`[CustomMessages]` e arquivos `.isl` compatíveis. Preservar idioma na atualização/desinstalação; instalação silenciosa automática não pode ficar aguardando seleção; testar compilação CI e fluxo real Win11. `windows/installer.iss` da v0.6.0 **não contém `[Languages]`**. **Pendente**; relacionado à [#15](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/15).
  
## Mensagens — estados de envio e leitura com relógio, ✓ e ✓✓ (14/10/2026)

- [**#4 — Mensagens no estilo WhatsApp**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/4): em **Mensagens**, balões **enviados à direita e recebidos à esquerda**; ícone **relógio** enquanto a mensagem está na fila/em envio; **um check ✓** após o rádio local aceitar o envio; **dois checks ✓✓ somente após recibo explícito e correlacionado de leitura real no destinatário por aplicativo compatível**. **ACK Meshtastic (confirmação técnica de recebimento) não confirma leitura** e deve manter um check, distinguido por tooltip/estado de entrega. Sem suporte a read receipt remoto, nunca mostrar ✓✓.
- **Falha/timeout/REJ:** símbolo de erro e opção segura para reenviar, mantendo tentativas e IDs distintos, sem criar check falso. Exibir horário local, tooltips de status e semântica acessível em tema claro/escuro.
- **Backend:** persistir `queued`, `sending`, `accepted_by_radio`, `acked`, `read`, `rejected`, `timeout` e `failed` (conforme aplicável) no SQLite e correlacionar confirmações por origem/fonte, pacote, destinatário/canal e período. Recibo de leitura por protocolo próprio deve ser **opcional, consentido e bilateral**, sem transmissão automática silenciosa e sem presumir compatibilidade com qualquer nó Meshtastic. Em canais/broadcast não indicar leitura individual.
- **Aceite:** teste com fila offline, envio RF, ACK sem confirmação de leitura, recibo de leitura compatível, falha/reenvio, múltiplas fontes e reinício, mantendo histórico e evitando avanço falso de estado. **Status: backlog, não implementado na v0.6.0.**

## Solicitações de backlog ainda não encerradas

As melhorias abaixo são **itens de backlog**, não funcionalidades já entregues. O detalhamento e os testes de aceite estão nas respectivas issues:

1. [**#1 — Idiomas na aplicação e no instalador Windows**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/1): PT-BR, EN, ES, FR, DE e IT; tradução de todas as telas, popups, notificações e atualizador, persistência e troca sem reinício. **Inno Setup:** detectar idioma do Windows, oferecer seleção manual na instalação, traduzir etapas, tarefas e erros com [Languages]/[CustomMessages]; reutilizar escolha em upgrades/desinstalação, sem bloquear atualização silenciosa.
2. [**#2 — Indicador superior de versão e atualização interna (parcial)**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/2): exibir **vX.Y.Z · ATUALIZADO** (verde), **NOVA VERSÃO DISPONÍVEL** (laranja com destaque), ou **Verificando/Indisponível** (neutro). Clique quando atualizado força a checagem; clique quando há nova versão abre changelog e confirmação de **Atualizar agora**, baixando Setup/Portable, validando SHA256 e instalando/reiniciando com encerramento seguro da issue #15. Intervalo padrão de 15 minutos, configurável, avisos e novidades uma vez por versão, sem falsamente afirmar que está atualizado em falha de rede. **A consulta simples já existe; barra clicável e instalação interna continuam pendentes.**
3. [**#3 — Acesso Web pela LAN**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/3): **desligado por padrão**, acesso local via aplicativo; habilitação explícita com autenticação, senha, proteção das APIs/mensagens, endereço IP/porta e opção de desligar sem afetar localhost.
4. [**#4 — Mensagens com visual de mensageiro**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/4): conversas/canais, balões RX/TX, horários, dias, não lidas, notificações e campo inferior; **relógio enviando, ✓ enviado, ✓✓ somente com recibo explícito de leitura de cliente compatível**, mais erro/reenvio. ACK Meshtastic não é confirmação de leitura humana; preservar estado correto na ausência de suporte remoto.
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

## Banco local e sincronização com dispositivos — nós, favoritos e metadados (14/10/2026)

- [**#29 — Banco local e sincronização contínua**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/29): **todas as informações de nós, favoritos, notas, tags, nomes amigáveis locais, proveniência por fonte e demais metadados** devem residir de modo persistente no **SQLite próprio**, inclusive offline, e refletir atualizações recebidas de dispositivos Meshtastic Serial/USB, BLE e Wi-Fi/TCP. Integração MQTT é observação RX, nunca escrita automática no rádio.
- **Ao conectar/reconectar:** importar/atualizar NodeDB e demais dados suportados por **merge idempotente**, registrando origem, timestamp, nó local do receptor e idade; preservar nós e enlaces históricos offline que estejam ausentes do cache do dispositivo. Durante uso, integrar NodeInfo, Position, Telemetry, mensagens e demais evidências incrementais sem F5, distinguindo cache do rádio de pacotes recém-observados.
- **Favoritos**: estrela e filtro na aba Nós, estado compartilhado com Mapa/popup/Chat/Ranking; favoritos/notas/aliases são preferências **do usuário cuja autoridade é o SQLite local**. Nunca apagá-los por ausência do nó no NodeDB ou por troca de fonte. Sincronizar para o rádio somente se funcionalidade suportada e mediante consentimento explícito, com verificação posterior; nunca supor que o firmware suporta favoritos.
- **Gerenciamento:** `Configurações → Dispositivo` terá última sincronização e status por fonte, contagem de nós importados/atualizados, falhas e botão `Sincronizar agora`; periodicidade incremental limitada para evitar saturar rádio. Resolver conflitos por dados válidos mais recentes e proveniência, sem trocar métricas de receptor nem herdar posições de nós móveis; preservar offline, backups, retenções e integridade em upgrades.
- **Aceite:** testes com 2+ rádios, NodeDB parcial, favoritos alterados offline, reinício/upgrade, timestamps divergentes, desconexões, falha de SQLite e leitura do próprio rádio, sem perda de favoritos/histórico. **Pendente após v0.6.0.** Relacionada às issues #8, #6, #20 e #27.

## Popup de nó em duas etapas — ações rápidas e Informações completas (14/10/2026)

- [**#27 — Popup compacto de ação rápida no Mapa**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/27): clique no marcador abre **popup pequeno** com nome/Node ID/última atividade e atalhos **Enviar mensagem**, **Solicitar NodeInfo**, **Solicitar telemetria** (Energia/Dispositivo/Ambiente/Qualidade do ar conforme firmware), **Posição**, **Traceroute** e **Vizinhos**, quando disponíveis. **Não enviar nada só por abrir o popup.** Solicitação só habilitada com backend/radio conectado e suporte real; caso contrário mostrar **Não disponível** em vez de simular RF/ACK. Mensagem abre conversa privada sem envio implícito.
- **Botão ao final: `Informações completas`** — fecha o popup rápido e abre **a janela grande já existente** (Resumo, Informações do nó, Consultas, Últimos metadados), reaproveitando componente/estado/correlação de pedidos. O modal grande **não deve ser aberto diretamente** no primeiro clique no marcador, alterando o comportamento da v0.6.0.
- Um popup compacto por vez, com foco/teclado/Esc, suporte a nó sem GPS via aba Nós, filtragem da fonte e identidade do destinatário estáveis; sem duplicar consultas nem confundir ACK com resposta de telemetria. **Pendente após v0.6.0.**

## Referências do legado: oito telas de Estatísticas e popup de nó (14/10/2026)

- [**#10 — Estatísticas, oito referências visuais detalhadas**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/10): capturas da v1.62.1 para **Visão Geral, Ranking, Routing, Tráfego, Consultas, Chat, Energia, Pontos de atenção**; as outras duas subabas **Rede e RF** permanecem abrangidas pela especificação anterior. A issue detalha **estrutura, cálculos, interações, estados vazios, filtros e evidências**. O legado serve somente de referência, **sem dependência do MeshMonitor**. **Não reintroduzir Acessos** (total de 10 subabas).
- **Visão Geral:** grade compacta 4×2 de oito KPIs e faixa amarela de resumo narrativo sincronizado; seções inferiores `Tipos de tráfego` e `Nós mais ativos`.
- **Ranking:** `10 enlaces RF diretos mais longos`: **# | Nó A | Nó B | Distância | Obs. RF | SNR médio | Última RF**, nome/Node ID em duas linhas, clique para destacar ligação no Mapa e tooltip com evidências. Exigir hop **RF direto comprovado**, não somente traceroute/NeighborInfo/MQTT. Manter `Diagnóstico de elegibilidade` com justificativa para exclusões e ausência de posições.
- **Routing:** cartões de métricas, **Distribuição por hops** e **Nós intermediários observados** lado a lado, abrindo detalhes de rota/nó mediante clique e diferenciando evidência real de hipótese.
- **Tráfego:** KPIs e `Volume por tipo` com **Tipo | Pacotes | Participação**, porcentagens corretas, TX e RX somente quando capturados.
- **Consultas:** KPIs e `Atividade de consultas observada` com **Tipo | TX | RX | Total observado**; estados correlacionados de ACK/REJ, resposta, timeout e erro, sem simular taxa de sucesso.
- **Chat:** KPIs e `Nós com mais interações no canal primário`, tabela **Nó | Interações acumuladas**, dados de mensagens reais e tratamento de privacidade.
- **Energia:** KPIs e `Bateria e energia dos nós`, tabela **Nó | Bateria | Tensão | Última interação**; distinguir bateria 0–100%, alimentação externa e telemetria ausente/antiga.
- **Pontos de atenção:** cabeçalho, **Severidade (Todas/Crítica/Atenção/Informativa)**, `Reanalisar`, indicadores de severidade, `Pontos identificados` e `Como interpretar`. Heurísticas documentadas não são comprovação de defeito.
- [**#27 — Mapa: popup rápido → Informações completas**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/27): ao clicar no nó abrir **primeiro um popup compacto de ações rápidas** (mensagem/NodeInfo/telemetria); botão **Informações completas** abre janela móvel, redimensionável e expansível, replicando seções **Resumo | Informações do nó | Consultas ao nó | Últimos metadados recebidos** da v1.62.1. Botões **NodeInfo, Posição, Energia, Traceroute, Dispositivo, Ambiente, Qualidade do ar, Vizinhos, Tudo** com progresso/status independente, respostas assíncronas, proveniência e consultas apenas em rádios capazes. Compartilhar popup com aba Nós, Mensagens, Tráfego e rankings; **sem GPS, ainda abrir detalhes**. Não usar MeshMonitor e não inventar retorno de consulta. **Pendente em v0.5.0.**

## Estatísticas — paridade visual e funcional com Traffic Analyzer v1.62.1 (14/10/2026)

- [**#10 — Clonar Visão Geral e as demais 9 subabas de Estatísticas**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/10): usar como referência fiel as telas e os componentes da v1.62.1 legada; preservar estilo, organização compacta, cálculos, filtros, gráficos, tabelas, rankings, consultas, drill-down, PDFs e CSV, mas **adaptar tudo ao SQLite e às fontes nativas Serial/BLE/TCP/MQTT**. A aba **Acessos foi explicitamente removida do escopo**; ficam **10 subabas**.
- **Visão Geral (layout obrigatório):** 8 cartões em grade 4×2 com `Nós ativos (conhecidos)`, `Pacotes (RX/TX)`, `Mensagens`, `Traceroutes`, `Relações observadas`, `SNR médio`, `RSSI médio`, `Pontos de atenção (críticos)`, e **faixa textual de resumo automático com borda amarela** cobrindo a largura total. Incluir nós originadores, período, contagens de RX/TX, mensagens, traceroutes, telemetria, nó mais ativo real, anomalias/críticos. Captura do Traffic Analyzer é **somente referência estética e de funcionalidades**; não copiar números/nó-fonte dela.
- **Demais 9 subabas:** `Rede`, `RF`, `Ranking`, `Routing`, `Tráfego`, `Consultas`, `Chat`, `Energia`, `Pontos de atenção`. Realizar auditoria de paridade **componente a componente** frente à v1.62.1; recriar funcionalidades ausentes, não apenas menus/placeholders. Manter filtro comum Período/Nó/Fonte, botões Atualizar tudo / Relatório PDF / Exportar CSV, indicador de atualização real e URLs dedicadas.
- **Rigor analítico:** somente apresentar métricas realmente existentes; sem RF direto inferido de traceroute, sem duplicar pacotes multi-receptor como transmissões únicas, sem inventar CRC/ruído, taxas de ACK, energia ou histórico indisponíveis. Reconciliação SQL → API → card → narrativa → exportação com testes automatizados e validação operacional no Windows.
- **Status:** em backlog, **não implementado integralmente na v0.4.0**. Issue #10 contém matriz detalhada e critérios de aceite por subaba.

## Alteração posterior à v0.4.0 — Estatísticas sem Acessos (14/10/2026)

- [**#10 — Remover Acessos de Estatísticas**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/10): retirar a subaba `Acessos`, mantendo somente 10 subabas, sem remover dados de auditoria técnica armazenados. Garantir navegação e URLs antigas sem tela em branco. **A v0.4.0 ainda exibe essa subaba; pendente de implementação.**

## BLOQUEANTE — atualização baixou e fechou, mas não reiniciou o aplicativo (14/10/2026)

- [**#34 — Atualização baixa e fecha a versão antiga, mas não abre a nova**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/34): **relato real na atualização da v0.6.1, gravidade bloqueante**. Não afirmar sucesso sem verificar instalação/substituição e inicialização do EXE. Diagnosticar `%LOCALAPPDATA%\PT2VHF-Mesh-Analyzer\update.log`, modo Setup/Portable, destino real do instalador, PID/caminho, permissões e saúde da nova instância.
- **Falha concreta no runner:** `mesh_analyzer/updater.py` grava `status=installed` em `update_complete.json` **antes** de executar `Start-Process`, sem confirmação de WebView2/`/health`. Exigir relançamento com diretório e caminhos corretos, handshake de prontidão na versão de destino, log de fases/erro e **mensagem de recuperação** se nova instância não subir. Falha de relançamento não pode gerar changelog falso de sucesso.
- Integrar às [#15 — Encerramento/instalador](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/15) e [#2 — Atualização/progresso](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/2). Testar **Setup→Setup e Portable→Portable em Win11**, caminhos personalizados, rádio conectado, falhas de instalação/restart, garantia de **exatamente uma instância** e preservação SQLite/fonte/histórico. **Pendente; não implementado**.
  
## Atualização em um clique — progresso central e changelog somente após reinício (14/10/2026)

- [**#2 — Fluxo do botão Nova versão**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/2): o botão laranja de nova versão disponível deve, **com um único clique**, iniciar automaticamente o download do pacote oficial correto e abrir **um único popup centralizado de progresso**, com barra, percentual, MB baixados, versão atual → nova e etapas Preparando / Baixando / SHA256 / Fechando / Instalando / Reiniciando. **Remover a confirmação nativa `127.0.0.1 diz` e o popup prévio de novidades/segundo botão Atualizar agora.** O clique inicial é a autorização explícita do usuário; a verificação periódica de 15 minutos, por si só, não deve instalar nada. Possibilitar Cancelar **somente antes de começar a instalação**, sem interromper tráfego por desistência durante o download.
- [**#15 — Parada e instalação**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/15): depois de o pacote passar na conferência SHA256, fechar fontes Serial/BLE/TCP/MQTT, servidor, SQLite e WebView2, esperar liberação do EXE; script externo independente executa Setup/atualização Portable e reinicia **exatamente uma** instância sem Gerenciador de Tarefas. O progresso em popup só é visível enquanto o aplicativo está aberto; após o fechamento, o worker prossegue independentemente com logs e tratamento de falhas.
- **Novidades após o sucesso:** ao abrir a versão recém-instalada, apresentar **changelog no centro uma única vez por versão**, com botão `Fechar/Entendi` e estado persistente, não antes do download; nenhuma falsa mensagem se houve falha/rollback. Preservar histórico SQLite, configurações, fontes e segurança.
- **Código atual v0.6.0:** `mesh_analyzer/ui.html` ainda usa `$('topUpdate').onclick = showUpdateDialog(...)` com changelog antes, seguido por `$('updateApply').onclick` com `confirm()`. Remover esses passos extras e reutilizar os endpoints `/api/update/prepare`, `/api/update/progress`, `/api/update/install`, `/api/update/notice`. **Pendente para próxima versão; não implementado na v0.6.0.**
- **Validação Win11:** Setup→Setup e Portable→Portable, com rádio conectado, janela minimizada, download interrompido, hash inválido, processo que não encerra, direitos de instalação e aviso pós-upgrade único. Não concluir #2/#15 com CI sem teste real.

## DEFEITO BLOQUEANTE — atualizador v0.5.0 não encerra o aplicativo (14/10/2026)

- [**#15 — Shutdown/instalador bloqueado**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/15) / [**#2 — Atualização direta**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/2): ao atualizar pelo próprio Mesh Analyzer, o processo **continua ativo**, e o instalador só avança depois que o usuário o encerra no Gerenciador de Tarefas. **Prioridade alta / bloqueante. Ainda não corrigido.**
- **Pontos identificados em código:** `/api/update/install` aciona `threading.Timer(0.8, shutdown)`; `request_shutdown` chama `webview.windows[0].destroy()` e assume que o loop encerrou, sem verificar conclusão; o worker externo aguarda até **90 s** pelo PID principal e falha, sem handshake ou alternativa segura. Investigar também tarefas fontes LoRa USB/Serial, BLE, TCP, MQTT, servidor HTTP e processos PyInstaller onefile; relatório do usuário é evidência da falha, mas diagnóstico técnico definitivo depende dos logs Win11.
- **Corrigir:** shutdown gracioso verificável em etapas (interromper TX/reconexão, fechar WebView2 pelo caminho correto, HTTP, fontes e SQLite), sinalização IPC de encerramento, espera PID e filhos identificados por identidade/caminho, execução do Setup/Portable somente após liberação dos arquivos, log de fases, timeouts e retries. Plano B de término forçado **somente do próprio Mesh Analyzer identificado e com confirmação expressa**, sem encerrar apps ou processos terceiros. Se falhar, interromper a atualização preservando banco e instalação anterior.
- **Aceite:** atualizar sem abrir Gerenciador de Tarefas, com janela aberta/minimizada, rádios ativos, WebView2, Setup/Portable Win11; após instalação reiniciar uma única instância e mostrar changelog. **Não fechar #2/#15 pelo CI; exigir ensaio real.**

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

## Fontes: autodetectar USB/Serial, Bluetooth LE e rede local (14/10/2026)

- [**#31 — Autodetectar fontes**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/31): em **Configurações → Fontes → Adicionar fonte**, incluir botão **Autodetectar**, varrendo **USB/Serial**, **Bluetooth LE** e **rede local Wi-Fi/TCP** mediante clique explícito. Abrir modal central com resultados, identificação/porta, status Meshtastic confirmado/provável, fonte já cadastrada, checkboxes de seleção individual, Marcar/Desmarcar tudo, Repetir/Cancelar e botão **Adicionar selecionados (N)**. Persistir **somente fontes confirmadas e escolhidas** no SQLite, evitando duplicatas, mantendo opção de conexão sob consentimento; não fazer varredura IP pública/VPN nem TX LoRa. Detalhes e testes em #31; **pendente, não implementado na v0.6.1**.

## Fontes — esclarecer o checkbox de ativação automática (14/10/2026)

- [**#6 — Checkbox `Conectar automaticamente ao iniciar`**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/6): esclarecer e destacar a legenda que pode parecer ausente na tela. Hoje `sourceEnabled` começa marcado, e o valor `enabled` ativa a conexão da fonte após salvar e nos próximos inícios, **não apenas na inicialização**. Sugerir legenda **`Ativar e conectar automaticamente esta fonte`** e ajuda `Marcado: conecta após salvar e tenta reconectar ao iniciar; desmarcado: fica cadastrada, mas desativada até ativação manual`. Distinguir de `TLS` (checkbox exclusivo do MQTT, que protege o transporte e não ativa/desativa a fonte). Garantir contraste, label clicável, tooltip, acessibilidade, salvamento/edição e status coerente. **Pendente após v0.6.1.**

## Identificação amigável consistente em toda a aplicação (14/10/2026)

- [**#35 — Sempre mostrar nomes amigáveis dos nós e dispositivos**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/35): adotar **alias local SQLite → nome longo NodeInfo → nome curto → Node ID somente como último recurso**. Para fontes/radios usar nome atribuído à fonte; Node ID, COM/BLE/IP e número de nó são detalhes secundários, mas mantidos para auditoria/homônimos. Aplicar em Mapa (marcadores, popups, enlaces), Nós, Mensagens/menções, Tráfego, Estatísticas/Ranking/Routing/Energia, Logs, Alertas, Fontes, Configurar dispositivo, PDFs/CSV. Resolver por **uma única função compartilhada** e atualizar online ao receber NodeInfo ou editar alias, sem perder os nomes amigáveis locais no resync da #29. **Pendente após v0.6.1.**

## Atualizador — interface de referência do PT2VHF Prop Tool (14/10/2026)

- [**#2 — Reaproveitar interface simples do Prop Tool**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/2): referência inspecionada no [commit `719c3d38` do Prop Tool](https://github.com/alexpmr/PT2VHF-Prop-Tool/commit/719c3d38ac45eb64c3483644cbc1afc448586240). **Botão único de versão** (verde atualizado / laranja nova versão), **modal central único** com estado e barra de progresso real, bytes recebidos/total e velocidade, sem `confirm()` ou changelog antes da instalação; bloquear cliques duplicados; modal independente com novidades somente na primeira inicialização confirmada da nova versão. Adaptar HTML/CSS/estado ao Python/WebView2; **não copiar Electron/NSIS**.
- [**#34/#15 — Garantir reinício**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/34): seguir o **princípio** de `ReadyFile`/handshake visto em `desktop/apply-update.ps1` do Prop Tool: validar que o Setup/Portable novo iniciou e responde `/health` com a versão correta antes de persistir status instalado/mostrar changelog; registrar timeout e recuperação quando falhar. O Mesh Analyzer hoje pode gravar falso sucesso antes de `Start-Process`. **Pendente após v0.6.1; falha bloqueante reportada em campo.**

## Fontes: botão Configurar dispositivo dentro de Editar Fonte (14/10/2026)

- [**#6 — Mover Dispositivo para Editar Fonte**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/6): **retirar a subaba independente `Configurações → Dispositivo`**; em **Configurações → Fontes → Editar Fonte**, acrescentar no **bloco "Editar fonte: [nome]"** o botão **"Configurar dispositivo"**. Ao clicar, abrir ali mesmo painel expansível/janela vinculada à fonte selecionada, com leitura/configuração de rádio, aplicação de alterações, snapshot e futuro backup/restore. Reutilizar a interface do `settingsLora`, sem perder funcionalidade. **Esse caminho novo substitui o antigo pedido de subaba Dispositivo.**
- **Fonte correta e operação segura:** vincular o editor a `sourceEditing`/ID persistido e Node ID do rádio realmente conectado, jamais usar por engano outra fonte. Para **Serial/USB, BLE e Wi-Fi/TCP** com rádio Meshtastic válido, habilitar conforme estado; **MQTT RX, fonte nova não salva e rádio desconectado não podem executar escrita no dispositivo**. Abertura do painel não deve enviar pacotes. Mostrar snapshot local identificado como cache quando offline.
- **Salvar fonte ≠ Configurar rádio:** botão **Salvar fonte** altera apenas conexão/autoconexão no banco SQLite. Botão próprio **Salvar todas as alterações** no painel é o único que solicita gravação de parâmetros no rádio, com diff/confirmar, resultado de cada grupo e readback. Botão global Salvar configurações (#25) não envia RF; avisar sobre mudanças não aplicadas e troca de fonte.
- [**#29 — Sincronização de NodeDB/favoritos**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/29): mover **Sincronizar agora**, última sincronização, contagens e status **para o painel Configurar dispositivo da fonte editada**, sem perder favoritos e histórico SQLite nem depender da subaba removida. Validar vários rádios e estados desconectados.
- **Estado atual v0.6.0:** a interface ainda exibe `data-panel="lora">Dispositivo`, `settingsLora` e seletor `loraSource`; migração **pendente**. Testar teclado, WebView2 Win11, fontes alteradas e independência do MeshMonitor.

## Sistema — Saúde, diagnóstico e manutenção do banco SQLite (14/10/2026)

- [**#33 — Banco de Dados e Manutenção em Configurações → Sistema**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/33): criar seção de monitoramento do **SQLite próprio** com tamanho real do banco principal + WAL/SHM, espaço livre, totais por tabela (nós, mensagens, pacotes, posições, enlaces, eventos, fontes, telemetria, favoritos quando disponível), versão/migração, períodos armazenados, política de retenção e integridade. Mostrar indicadores só quando mensurados; não atribuir tamanho aproximado por tabela como fato.
- **Diagnóstico e sugestões com base em métricas reais:** análise sob demanda (`PRAGMA quick_check`, `foreign_key_check`), inspeção de WAL/freelist, último backup, recomendações de backup, otimização/VACUUM quando houver economia/espaço, `PRAGMA optimize` quando fundamentado, e limpeza **apenas** de dados vencidos conforme retenção diferente de **Nunca**. Exibir motivo, impacto e quantidade elegível. Em retenção **Nunca**, **nenhuma recomendação de exclusão por idade/tamanho**.
- **Manutenção segura:** botões `Analisar banco`, `Pré-visualizar limpeza`, `Fazer backup`, `Limpar selecionados`, `Otimizar`, `Ver log`; tabela de prévia por categoria com cutoff/total/elegíveis, confirmação explícita e backup online consistente **antes de exclusões**, validação de espaço e recuperação. Proteger favoritos, fontes, nomes locais, histórico RF/nós offline e auxiliares `node_sources`/`topology_processed`; preservar dados padrão. Não bloquear indefinidamente as fontes RF, não expor backups/credenciais pela LAN.
- **Código v0.6.1:** `db.stats()` e `db.cleanup()` existem, e a subaba Retenções possui limpeza direta; **painel de saúde, manutenção com prévia e backup consistente ainda pendentes**. Aceite e testes detalhados na issue #33.

## Configurações → Sistema / Dispositivo — complementos (14/10/2026)

- [**#18 — Sistema: frequência de verificação de novas versões**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/18): exibir em **Configurações → Sistema → Atualizações** o campo **Verificar novas versões a cada [15] minutos** (padrão **15 minutos**, intervalo permitido de 5 a 1.440 min). Persistir na configuração do aplicativo, com agendador único para janela desktop e acesso web opcional, evitando verificações duplicadas. Mostrar última/próxima checagem, estado atual e botão **Verificar agora**; alteração deve valer imediatamente e sobreviver a F5/reinício/upgrade. Vincular à [**#2 — Atualização interna**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/2). Na v0.2.0 a frequência já existe em localStorage, mas ainda não está consolidada em Sistema nem é aplicada por agendador global.
- [**#6 — Dispositivo: editor por fonte no bloco Editar Fonte (pedido posterior prevalece)**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/6): em **Configurações → Dispositivo**, menu pull-down para rádios conectados via Serial/USB, BLE ou Wi-Fi/TCP/IP; ao selecionar, leitura atualizada de **todos os parâmetros disponíveis** e apresentação em uma só tela editável (identificação, LoRa, canais, GPS, energia, display, Bluetooth, rede, segurança e módulos). Permitir alterar múltiplas categorias e clicar **Salvar todas as alterações** uma única vez; confirmar diff, aplicar comandos de forma sequencial e segura, reler cada seção, mostrar sucesso parcial, falha, timeout e necessidade de reboot. Nenhum dispositivo MQTT somente RX pode receber comandos de configuração. Proteger chaves/PSKs e backups. Apenas os sete campos LoRa disponíveis na v0.2.0 foram implementados parcialmente; o editor abrangente está pendente.

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