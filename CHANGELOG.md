# v0.6.62 — Ferramentas no topo, cobertura completa, conteúdo no Tráfego e preferência USB

- Ferramentas no `#nav` (entre Automações e Configurações); `#mapToolsPanel` fora das abas; `.navbtn[data-view]` para não trocar de aba ao abrir o painel.
- Cobertura: `max_km` padrão 50 e até 100 (`MAX_KM`), campo "Raio da cobertura" acima de Calcular; busca do ponto mais alto até 50 km (zoom menor nos raios grandes) com validação; catálogo `RADIO_CATALOG` por marca/modelo com `hw` do Meshtastic e sugestão pelo hardware (cobertura e enlace A/B); nós com/sem cobertura e fora do raio (`classifyCoverageNodes`, `coverage.classify_nodes`), contorno vermelho e clique para o enlace com "Voltar à cobertura"; PDF da cobertura (`survey_pdf.coverage_pdf`, grade desenhada em faixas, sem depender do Pillow); versão do app no cabeçalho dos PDFs.
- Relevo: `survey.despike()` remove pixels/aglomerados com altitude impossível nos tiles Terrarium (mediana 5×5, limiar 250 m), aplicado no enlace, melhor ponto e cobertura.
- Conexões: `RADIO_RANK` (USB 0, BLE 1, Wi-Fi 2) na ordem de início e na prioridade de abertura; `SourceManager.better_radio()` + `DeviceWatcher._prefer_better()` trocam para o meio melhor do mesmo nó quando presente (porta enumerada / BLE visto), sem abrir a porta; `activate(..., manual=False)` nas trocas automáticas e `preferred_radio_manual` para respeitar a escolha manual.
- Tráfego: `mesh_analyzer/payload.py` (resumo e campos por tipo), `summary` em `/api/packets`, `/api/packet?id=` com campos e JSON; coluna "Conteúdo" e CSV.
- Mapa: etiqueta `nodeShortLabel` só com o nome curto; "Mostrar nomes curtos" ligado por padrão (migração única por perfil).
- Repetidores: disponibilidade = horas com sinal de vida (pacote, salto em traceroute, vizinho em NeighborInfo) ÷ horas em que o app ouviu; "sem dados" abaixo de 2 h; presença `heard_after`.
- Testes: `tests/test_release_v0662.py`.

# v0.6.61 — Menu Ferramentas, análise de cobertura e automações recolhidas

- Menu **Ferramentas** no mapa (`#mapToolsBtn`/`#mapToolsPanel`): Análise de cobertura, Analisar enlace, Melhor ponto, Relevo com corte, Relatório da malha (PDF) e Diagnóstico para suporte. Saíram da aba Ver.
- **Análise de cobertura** (`mesh_analyzer/coverage.py`, `/api/survey/coverage` e `/api/survey/highest`): radiais a partir do transmissor sobre os tiles Terrarium (baixados em paralelo e guardados em disco), perda em espaço livre, difração em dois gumes (horizontes do transmissor e do receptor, Epstein-Peterson) na Terra efetiva com k da refratividade, altura de obstáculos e margem por % de locais e % do tempo conforme o clima de rádio. A grade em dBm volta para a interface, que aplica mapa de calor ou contornos, escala, faixa e transparência sem recalcular.
- Indicador da conexão: verde/vermelho só pelo estado e tipo entre parênteses (`connectionTypeLabel()`: USB, BLE, WIFI, MQTT); removidas as cores por tipo.
- Relevo com corte: coluna de 68 px, slider de corte ocupando a altura e cor do sombreamento (`#terrainColor`, salva nas preferências do mapa). Relevo sombreado removido; a preferência antiga `mapHillshade` é descartada ao salvar.
- Automações recolhidas (`setupAutomationItems()`): Meshtastic, MeshCore e Mensagens automáticas viram itens fechados com estado e resumo; ao abrir, Salvar/Cancelar no rodapé; alterações não salvas são resolvidas ao trocar de item ou de aba.
- Testes: `tests/test_release_v0661.py`.

# v0.6.60 — Aviso do site oficial sem atrapalhar o aviso de versão nova

- O aviso "Downloads no site oficial" (www.pt2vhf.com) continua aparecendo sempre, a cada abertura, sem opção de "não mostrar novamente".
- `maybePromptUpdate()` espera o aviso ser fechado (`officialSiteNoticeOpen()`); antes, o pedido de atualização podia abrir escondido por baixo dele. Ao fechar o aviso, o aviso de versão nova abre em seguida.
- Testes: `tests/test_release_v0660.py`.

# v0.6.59 — Detecção USB não aciona PTT de rádios com CAT; MeshCore na USB

- `usb_serial_ports()` (detecção automática e "Adicionar automaticamente") só abre portas de chips de placas Meshtastic/MeshCore (`BOARD_USB_IDS`: Espressif 303A, Adafruit 239A, Seeed 2886, Nordic 1915, RP2040 2E8A, CP2102 10C4:EA60, CH9102/CH343) e descarta nomes de rádios/CAT (`RADIO_LABELS`). O CH340 comum (1A86:7523) fica de fora. Relato de PU2MUS: ao iniciar, rádios com CAT entraram em PTT (pyserial, meshtastic e meshcore ligam DTR/RTS ao abrir a porta no Windows; a sonda MeshCore ainda inverte o DTR sem resposta). No diagnóstico, COM3/COM4 eram CH340 de rádios.
- `SourceManager._open_serial()`: conexão USB marcada como Meshtastic que não responde é testada como MeshCore; se responder, o cadastro passa para `protocol: meshcore` (Heltec Wireless Paper na COM6, `MeshInterfaceError` em toda troca de rádio).
- Testes: `tests/test_release_v0659.py`.

# v0.6.58 — Downloads e OTA pelo site oficial PT2VHF

- Atualizador do Windows consulta somente `https://www.pt2vhf.com/update.php?product=mesh` e baixa pacotes hospedados no site oficial, validando tamanho e SHA-256 descritos na API, sem depender de releases do GitHub.
- Popup de abertura em português, inglês ou espanhol, respeitando o idioma configurado, com link clicável para `www.PT2VHF.com/mesh`.
- Contador cumulativo por instalador, usando a API de downloads do site; instaladores e contadores são publicados separadamente do código-fonte.
- O site exibe as variantes de build pendentes até que os binários reais estejam presentes na hospedagem.

# v0.6.57 — Contador de downloads por tipo de build

- #210: `scripts/download_stats.py` soma o `download_count` dos arquivos de todas as releases por tipo de build e grava selos (endpoint do shields.io) em `downloads/*.json` no ramo `badges`. Como `retain_latest_release.py` apaga as releases antigas, o histórico fica em `downloads/state.json` (maior contagem vista por versão/arquivo), então o total nunca diminui.
- Workflow `download-stats.yml` (a cada hora e manual) e um passo no `publish-release` que atualiza o contador antes de apagar as releases antigas (`scripts/download_stats.sh`).
- README: coluna "Downloads" nas tabelas e selos de total, Windows, macOS e Linux.
- Testes: `tests/test_release_v0657.py`.

# v0.6.56 — Favoritos sem reenvio contínuo

- `_push_favorites()`: a cópia do NodeDB na biblioteca Meshtastic não muda com o comando admin; com o intervalo de 60 s, o app reenviava `removeFavorite`/`setFavorite` a cada minuto para os mesmos nós (visto no diagnóstico #198: ~17 vezes cada um de 10 nós em 3 minutos). Agora cada (nó, estado) vai uma vez por conexão (conjunto guardado na interface) e é tentado de novo só ao reconectar.
- Testes: `FavoriteResendLoop` em `tests/test_favorites_v0633.py`.

# v0.6.55 — Apelido para nós

- #206: o "Nome amigável local" (`friendly_name`, só no banco do app) passa a se chamar **Apelido**.
  - `editNickname()` é compartilhado pelo menu de contexto ("Dar/Editar apelido") e pelo botão "Apelido…" do painel do nó.
  - Nova coluna "Apelido" na lista de nós, adicionada uma vez também para quem já tinha colunas salvas.
  - O título do painel mostra "Apelido (nome real)". Textos em EN/ES.
- Teste de UI da v0.6.37: espera o texto "Trocando para…" em vez de dormir 50 ms (falhou no runner do Windows da main na v0.6.54).
- Testes: `scripts/test_ui_v0655.cjs`.

# v0.6.54 — Cores por tipo de conexão

- A barra do rádio ganha `data-kind` (serial, ble, tcp, mqtt) com cores próprias: USB verde, Bluetooth azul, Wi-Fi laranja, MQTT violeta. Há variantes do tema claro e cores nos pontos do menu do rádio e de "Mostrar dados de". A cor violeta passa a valer só para MQTT (antes era para qualquer conexão vista que não fosse o rádio ativo).
- Testes: `scripts/test_ui_v0654.cjs`, que confere as cores calculadas no Chromium.

# v0.6.53 — Bluetooth no Windows: sessão ativa antes de ler os serviços

- #191: o usuário conseguiu conectar pelo client.meshtastic.org (Web Bluetooth) no mesmo PC em que o app recebia `Unreachable` em ~12 ms. O Chromium abre o `GattSession` com `MaintainConnection` e espera `SessionStatus.Active` antes de `GetGattServicesAsync`; o bleak pede os serviços logo de saída.
  - `ble_link.windows_prewarm()` abre o `BluetoothLEDevice` + `GattSession` (`maintain_connection=True`) e espera ficar ativa (até 20 s) antes do `BleakClient.connect()`.
  - A sessão é mantida durante a conexão do bleak e liberada depois, no sucesso ou na falha.
  - Se não ficar ativa, a mensagem diz isso.
  - Só no Windows; erros nessa etapa não impedem a tentativa normal.
- Testes: `tests/test_release_v0653.py`.

# v0.6.52 — Correções do primeiro diagnóstico real

- #191: o primeiro diagnóstico (Windows 11 build 26300, Realtek Bluetooth 4.2 USB) mostra o pareamento sem PIN falhando em ~130 ms e a sessão GATT com `Unreachable` ~12 ms depois de "getting services", em todos os rádios: o Windows recusa sem transmitir.
  - `ble_link.LinkError` guarda a duração das tentativas e, abaixo de 1,5 s, diz "recusado pelo Windows em N ms, sem chegar a falar com o rádio".
  - Duração das tentativas e do pareamento vai para o log.
- `/api/meshcore/results` sem `node` dava `TypeError` (`int(0, 0)`), quebrando "Últimas leituras" em Automações.
- `diagnostics._versions()`: no app empacotado (sem metadados) usa a versão do módulo.
- Testes: `tests/test_release_v0652.py`; `test_release_v0647` cobre a nova mensagem.

# v0.6.51 — Diagnóstico para suporte (.zip)

- #198: novo `diagnostics.py`.
  - `build()` monta o .zip em memória com `resumo.txt`, `conexoes.json`, `bluetooth.json` (adaptador, varredura de 5 s com `is_paired`, "Adicionar automaticamente", avisos), `usb.json`, `configuracao.json`, `banco.json`, `eventos.txt` (7 dias) e `log.txt`.
  - `clean()` mascara campos de segredo (senha, PIN, PSK, chaves, tokens, credenciais) em qualquer nível. Mensagens e posições não entram.
  - `RingLog` guarda as últimas 8000 linhas de log em memória; `verbose(min)` põe bleak/meshtastic/mesh_analyzer/meshcore em DEBUG por alguns minutos.
  - Os arquivos ficam em `diagnostics/` no perfil (mantém os 5 últimos).
- API: `POST /api/diagnostics/build`, `GET /api/diagnostics/download`, `POST /api/diagnostics/verbose`, `GET /api/diagnostics/status`. A janela desktop ganha `save_diagnostic()`, com o diálogo nativo de salvar, como o backup.
- UI: aba Configurações → Diagnóstico (última) e atalho no resultado do "Adicionar automaticamente" quando o Bluetooth falha.
- Testes: `tests/test_release_v0651.py`, `scripts/test_ui_v0651.cjs`; a lista de métodos expostos pela janela inclui `save_diagnostic`.

# v0.6.50 — Bluetooth: parear antes de conectar, nome do rádio e modelo do adaptador

- #191: `DeviceWatcher.verify()` volta a parear sem PIN antes de conectar quando o rádio não está pareado (`is_paired()`), e nunca remove nem desfaz pareamento. Evidência de campo: na v0.6.46, 5 de 7 rádios parearam e falharam só por tempo (`TimeoutError`, já tratado pelo `ble_link` da v0.6.47); da v0.6.47 em diante, conectar antes fazia o Windows recusar o pareamento (`FAILED`) e devolver `Unreachable`.
- O resultado do "Adicionar automaticamente" mostra o nome anunciado pelo rádio junto do endereço.
- `ble_pairing._windows_adapter_model()`: modelo, estado e InstanceId do rádio Bluetooth via `Get-PnpDevice` (o nome do WinRT é o nome Bluetooth do PC).
- Testes: `tests/test_release_v0650.py`; testes da v0.6.43 e v0.6.47 voltam à ordem "parear antes de conectar"; `test_ui_v0648` confere nome e modelo.

# v0.6.49 — Uma conexão de cada vez e diagnóstico Bluetooth

- #189/#194:
  - a barra superior mostra só a conexão escolhida, sem o rádio TX entre parênteses (ele vai para o título); o selo vira só "✕";
  - `/api/state?source=` devolve contadores da conexão (`Database.stats(source_id)`, com nós por `node_sources` observados);
  - as luzes TX/RX seguem a conexão escolhida.
- #191:
  - o "Informar PIN…" acompanha o aviso do rádio e mostra o resultado na própria linha;
  - `AutoAdd` informa o adaptador Bluetooth (`ble_pairing.adapter_info()`: WinRT `BluetoothAdapter`, ou `bluetoothctl show` no Linux) quando algum rádio BLE falha;
  - quando todos falham com `Unreachable`, a tela orienta o teste no cliente web oficial;
  - `verify()` deixa de remover pareamentos que já existiam no sistema; só desfaz o pareamento que ele mesmo criou.
- Testes: `tests/test_release_v0649.py`; `test_ui_v0647`/`v0648` atualizados (rota de `/api/state` com consulta, barra só com a conexão, progresso do PIN e diagnóstico).

# v0.6.48 — Barra superior com a conexão vista e PIN no "Adicionar automaticamente"

- #194: `updateRadioConnectionIndicator()` mostra a conexão escolhida em "Mostrar dados de" (nome · tipo, com o rádio TX entre parênteses) e `data-view="other"` com cor violeta. O selo vira o botão "✕ Todas as conexões", com `order:3`; antes ele ia para o início do cabeçalho flex, fora da vista.
- #191: os resultados BLE "sem resposta" do "Adicionar automaticamente" ganham "Informar PIN…", que chama `/api/devices/pair-address` → `DeviceWatcher.pair_address()` (abre ou reaproveita o aviso e segue o fluxo de PIN da v0.6.43), mais uma dica sobre o PIN padrão do Meshtastic.
- Testes: `tests/test_release_v0648.py` e `scripts/test_ui_v0648.cjs`; `test_ui_v0647` ajustado para o novo texto do selo.

# v0.6.47 — Bluetooth mais tolerante e visualização por conexão

- #191: novo `ble_link.py`. `MeshtasticBLE` substitui o `connect()` da `BLEInterface`:
  - procura o rádio uma vez (`find_device_by_address`, 10 s) e conecta pelo `BLEDevice`, evitando a segunda varredura do bleak e a varredura de 5 s depois de conectar;
  - prazo de 20 s para a sessão GATT e os serviços; segunda tentativa com `use_cached_services=False`;
  - leitura de FROMRADIO para confirmar o acesso;
  - erros por etapa em português; `auth` quando o rádio exige pareamento.
  
  Usado na verificação e na conexão das fontes BLE. `scan_ble` recusa varrer durante uma conexão.
- #191: `DeviceWatcher.verify()` conecta primeiro sem parear. Na falha:
  - rádio que exige pareamento → pareia sem PIN (ou pede PIN) e tenta de novo;
  - pareamento do sistema sem PIN guardado → remove e tenta de novo;
  - pareamento criado que não ajudou → é desfeito.
  
  `ble_pairing` ganha `is_paired()`/`unpair()` (WinRT e bluetoothctl) e fecha o `BluetoothLEDevice` após parear. Prazos de verificação BLE: 90 s (60 s na primeira abertura).
- #189: seção "Mostrar dados de" no menu do rádio, com Todas as conexões, o rádio ativo e o MQTT. O filtro vale para mapa, nós, mensagens, tráfego e estatísticas, com o selo "Vendo …" e preferência local. `/api/packets` e `/api/messages` aceitam `?source=`.
- Testes: `tests/test_release_v0647.py` e `scripts/test_ui_v0647.cjs`; testes da v0.6.43 ajustados para a nova ordem (conectar antes de parear).

# v0.6.46 — MeshCore etapa 2 e coleta periódica

- #190: `MeshCoreInterface` ganha operações síncronas (anúncio, zerar/redescobrir caminho, login, status, telemetria, vizinhos, CLI, traceroute, remover contato, autoadd, canais, link do contato, contadores) e avisa contatos, dados do rádio e resultados por `on_event`. Respostas de CLI (`txt_type` 1) vão para quem pediu, não para o chat. Traceroute usa o caminho de ida e volta (`saltos + alvo + saltos invertidos`) com tag própria; vizinhos (prefixo de 4 bytes) e traceroutes resolvidos viram pacotes NEIGHBORINFO/TRACEROUTE para a topologia.
- Novo `meshcore_data.py`: contatos por fonte, mudanças de caminho, resultados (status/telemetria/vizinhos/trace), colisões de prefixo de 1 byte e do tamanho de hash do rádio, caminhos resolvidos para o mapa, ocupação e contatos antigos. APIs `/api/meshcore`, `/api/meshcore/results`, `/api/meshcore/action`, `/api/meshcore/automation`.
- UI: aba Estatísticas → MeshCore, seção MeshCore no painel do nó, filtro de protocolo/anel violeta/caminhos no mapa, presets MeshCore no planejamento (`MESHCORE_SF<n>_BW<kHz>`) e valores lidos do rádio MeshCore.
- #188: Automações separadas em Meshtastic, MeshCore e Mensagens automáticas. `MeshCoreAutomation` pede telemetria/status de contatos escolhidos com orçamento por hora, intervalo mínimo, senha local opcional e recuo exponencial (15 min até 12 h).
- Testes: `tests/test_release_v0646.py` (FakeMeshCore com eventos reais) e `scripts/test_ui_v0646.cjs`.

# v0.6.45 — MeshCore, etapa 1: conexão e recepção

- #185: novo `mesh_analyzer/meshcore_driver.py` com a biblioteca oficial `meshcore` (MIT). `MeshCoreInterface` roda o cliente assíncrono numa thread própria e se apresenta ao `SourceManager` como interface comum (myInfo, localNode, nodesByNum, sendText, close), convertendo eventos em pacotes do formato já tratado pelo `PacketIngestor`: SELF_INFO e contatos → nós (nome, papel por tipo de anúncio: Companion/Repetidor/Room server/Sensor, posição); NEW_CONTACT/ADVERTISEMENT → NODEINFO e POSITION; CONTACT_MSG_RECV e CHANNEL_MSG_RECV → mensagens (remetente de canal resolvido pelo nome ou nó derivado do nome); RX_LOG_DATA → tráfego `MESHCORE_<tipo>` com SNR/RSSI e saltos (enlace RF direto quando ouvido sem saltos); envio por chave pública (privado) ou canal, ACK do MeshCore → "entregue". Número do nó = 4 primeiros bytes da chave pública.
- Conexões: campo `protocol` (meshtastic|meshcore) em USB, TCP e BLE, PIN opcional no BLE, porta TCP padrão 5000 para MeshCore; selo "MeshCore" no cartão da conexão.
- Detecção automática: na USB tenta MeshCore e depois Meshtastic (prazo de verificação 40 s); no Bluetooth reconhece rádios "MeshCore-…"; cadastro com o protocolo e o rótulo "MeshCore".
- Consultas remotas, favoritos no rádio, apagar nós e configuração recusam com mensagem clara em rádios MeshCore (etapas 2 e 3).
- Nova dependência: `meshcore>=2.3,<3`.

Validação: testes Python com um rádio MeshCore simulado sobre os tipos de evento reais da biblioteca (nós, papéis, posições, anúncios, mensagens diretas e de canal, tráfego e enlace direto, envio e ACK, validação da configuração, detecção na USB e no Bluetooth) e regressão Chromium v0.6.34–v0.6.45; biblioteca real contra porta inexistente e servidor TCP mudo (falha em ~2 s com mensagem clara). Não testado aqui: rádio MeshCore físico.

# v0.6.44 — Ajuste na análise de enlace

- #179: com a linha de visada bloqueada, "Fresnel livre" mostrava porcentagens negativas (ex.: −234%). Passa a mostrar "0% (sem visada)" e quantos metros o terreno fica acima da linha, na tela e no PDF.

# v0.6.43 — Bluetooth sem PIN pareado e incluído sem clique

- #164 (relato de uso real): rádios sem PIN definido não eram pareados nem incluídos. `ble_pairing.pair()` aceita PIN ausente: no Windows aceita o pareamento por confirmação ("Just Works") e devolve `pin_required` quando o rádio pede código; no Linux o `bluetoothctl` usa agente KeyboardDisplay, confirma pedidos sim/não e devolve `pin_required` ao pedido de passkey; no macOS segue com o diálogo do sistema. `DeviceWatcher.verify()` pareia sem PIN antes de verificar qualquer rádio Bluetooth (aviso, "Adicionar automaticamente", primeira abertura). Rádio BLE próximo e novo é pareado, verificado e cadastrado sem clique quando "Adicionar e conectar sem perguntar → Bluetooth" está ligado (novo padrão, aplicado uma vez também a perfis antigos); se pedir PIN, o aviso já abre com o campo de PIN. O campo de PIN deixa de aparecer em rádios que parearam sem código.

Validação: testes Python (sem PIN → cadastrado sem clique, pede PIN → campo de PIN, preferência desligada, clique no aviso, falha após pareamento sem pedir PIN, PIN digitado sem novo pareamento, diálogos do bluetoothctl, migração da preferência) e regressão Chromium v0.6.34–v0.6.41. Aceite físico pendente: rádio sem PIN e rádio com PIN no Windows.

# v0.6.42 — Elevações por tiles de terreno

- #179/#180: as consultas ao Open-Meteo falhavam no computador do usuário (enlace e survey), com uma mensagem que escondia o motivo. Fonte principal passa a ser os tiles Terrarium (`s3.amazonaws.com/elevation-tiles-prod`, zoom até 12, interpolação bilinear, decodificador PNG próprio sem dependências novas), com cache dos tiles em `terrain-tiles/` no perfil do app, além do cache de pontos no SQLite. Open-Meteo como alternativa, dividido em lotes de 100 coordenadas e com User-Agent. Erros com o motivo (HTTP, limite 429, tempo esgotado, certificado) das duas fontes.
- Survey de melhor ponto com ~2.500 amostras na grade (antes 900).
- O perfil de terreno do popup de enlace (#171) usa a mesma fonte e o mesmo cache.

Validação: testes Python (decodificador PNG com todos os filtros, interpolação, cache em disco offline, escolha de zoom, alternativa Open-Meteo e mensagens de erro) e regressão Chromium v0.6.34–v0.6.41; teste real com tiles: enlace de 28 km e survey de 1.666 km² no DF (ponto mais alto 1.344 m) pela API do app, com PDF.

# v0.6.41 — Análise de enlace entre 2 pontos e melhor ponto para instalar nó

- #179: ferramenta no menu Ver do mapa. Pontos por clique, nó ou coordenadas, arrastáveis. Perfil com 40–256 amostras pelo grande círculo, curvatura k = 4/3, 1ª zona de Fresnel e faixa de 60%. Orçamento do enlace: EIRP, perda em espaço livre, difração por gume de faca (Deygout, ITU-R P.526), sinal estimado, sensibilidade por preset LoRa (SF/BW, NF 6 dB), margem e SNR. Veredito Viável (margem ≥ 10 dB com visada), Marginal (margem 0–10 dB ou sem visada) ou Inviável (margem negativa), com o motivo e o pior obstáculo no mapa. Altura mínima de antena em A, em B ou nas duas para liberar 60% da zona de Fresnel. Valores do rádio ativo (região, preset, potência). SNR/RSSI medianos observados quando uma ponta é rádio próprio. PDF. O botão do popup de enlace abre a nova análise.
- #180: polígono desenhado no mapa (até 100 vértices, desfazer, fechar no primeiro vértice/duplo clique/Concluir, arrastar, inserir e remover vértices). Grade de ~900 amostras ajustada à área (limite 5.000 km², aviso acima de 1.000 km²), só topos locais (encostas do mesmo morro não entram), refinamento em volta de cada topo e separação mínima proporcional à área. Ranking do mais alto para o mais baixo (empate: mais perto da referência), indicação de ponto na borda, referência opcional, enlace de cada ponto, surveys salvos, CSV e PDF com mapa de relevo, tabela e perfis.
- Elevações do Open-Meteo em lotes de 100, com cache no SQLite (`elevation_cache`).
- Teste v0.6.38 do Chromium: corrigida uma falha intermitente causada pela atualização periódica dos nós durante o teste.

Validação: testes Python (orçamento, curvatura, obstáculo, cache offline, topos distintos, borda, referência, limites, surveys salvos, PDF, valores do rádio) e regressão Chromium v0.6.34–v0.6.41, com o servidor real e terreno sintético. Não testado aqui: elevações reais do Open-Meteo (bloqueado neste ambiente).

# v0.6.40 — Alertas, backup, análises da malha, mensagens automáticas, canais, busca, EN/ES e PIN Bluetooth

- #164: pareamento BLE com PIN digitado no aviso do dispositivo (`/api/devices/pair`, fase "pairing" cancelável). Windows: pareamento personalizado do WinRT respondendo ao pedido de PIN; Linux: `bluetoothctl` com agente de teclado; macOS: diálogo do sistema. Falha de verificação BLE passa a oferecer o campo de PIN.
- #165: central de alertas (`alerts`): favorito calado, bateria baixa (repetidores e favoritos), utilização do canal, mensagem privada e menção. Um alerta por situação até ser resolvida; histórico não gera alerta. Sino com contador e painel; envio por Telegram e SMTP (STARTTLS/SSL), segredos mascarados na API, botões de teste.
- #166: backup `.zip` (manifesto + cópia consistente do SQLite pela API de backup) e restauração em duas etapas: o arquivo é validado e preparado; no reinício, o banco atual é guardado em `backups/pre-restore-*.sqlite3` antes da troca. Upload inválido não descarta uma restauração já preparada. Botão de salvar no app de desktop.
- #167: camada de cobertura por células com o SNR médio das recepções diretas (sem MQTT, sem saltos).
- #168: linha do tempo do nó (presença, bateria, tensão, SNR, utilização do canal, airtime) em 24 h / 7 d / 30 d.
- #169: aba Repetidores em Estatísticas (disponibilidade por horas ouvidas, telemetria, participação em rotas, presença).
- #170: rotas de traceroute no mapa e aba Topologia com os nós intermediários mais usados (gargalos).
- #171: perfil de terreno entre dois nós com elevação Open-Meteo, curvatura k=4/3 e 1ª zona de Fresnel.
- #172/#173: mensagens agendadas (uma vez, diária com dias da semana, intervalo ≥ 15 min) e respostas automáticas (igual/começa/contém; privadas, canal ou ambos; pausa por remetente), variáveis de modelo incluindo `{clima}`, limite comum de envios por hora, nunca responde a mensagens antigas nem aos próprios rádios; registro recente e pré-visualização.
- #174: lista de canais do rádio ativo (sem expor chaves), canais secundários como conversas, edição dos canais 1–7 (nome, ativação, chave manter/padrão/aleatória/nenhuma/personalizada) com restauração em caso de falha.
- #175: busca no histórico de mensagens sem acentos/maiúsculas, por período, com contexto da conversa.
- #176: interface em inglês e espanhol (preferência `language` no Sistema). Tradução no navegador por dicionário, inclusive de conteúdo criado depois; textos das mensagens nunca são traduzidos; textos sem tradução ficam em português.
- #177: relatório PDF com seções de repetidores, rotas/gargalos, cobertura, presença e alertas/mensagens (sem conteúdo das mensagens).

Validação: testes Python (backup/restauração, busca, alertas, automação de mensagens, canais, análises, PIN, PDF, idioma) e regressão Chromium v0.6.34–v0.6.40. Não testado ao vivo neste ambiente: Open-Meteo (`{clima}` e perfil de terreno) e pareamento BLE com PIN em Windows/Linux reais.

# v0.6.39 — Primeira abertura detecta, adiciona e conecta o rádio

- #162: ao iniciar com interface e sem conexões cadastradas, o app dispara a busca de primeira abertura antes do diálogo "Configure sua primeira conexão". Etapa 1: todas as portas USB/serial com VID verificadas em paralelo pelo handshake Meshtastic (prazo de 20 s); cada rádio que responde é cadastrado com conexão automática e conectado na hora, com o cartão "adicionado" e Desfazer de #155. Etapa 2 (só se nada responder na USB): mDNS e Bluetooth próximo (prazos de 20/25 s). Respeita as preferências de detecção por tipo e os dispositivos "Nunca". A interface mostra "Procurando rádios Meshtastic…" com Cancelar; o diálogo só abre se nada for encontrado, com o resultado da busca e o novo botão "Procurar novamente". Também vale ao abrir sem conexões depois da primeira vez. Desligado em container e no modo sem interface.

Validação: testes Python (USB em paralelo, sem rede quando a USB encontra, retorno a Wi-Fi/BLE, preferências e "Nunca", cancelamento) e regressão Chromium v0.6.34–v0.6.39. Aceite físico pendente: instalação nova no Windows com rádio já ligado na USB antes de abrir.

# v0.6.38 — Prioridade USB, verificação com Cancelar, favoritos sincronizados, mensagens estilo WhatsApp, ping de presença, .deb e container

- #155: rádio USB novo verificado é cadastrado e conectado sem clique (aviso com Desfazer, que remove a conexão e marca "Nunca"). Prioridade USB > Wi-Fi > Bluetooth: USB plugado (novo ou já cadastrado) assume pela troca segura de #152; troca adiada enquanto houver consulta RF aguardando resposta. No início do app, sem rádio escolhido, a USB conecta primeiro. Preferências "Adicionar e conectar sem perguntar" (USB ligado; Wi-Fi/BLE desligados) e "Dar prioridade ao rádio USB".
- #156: verificação em segundo plano com prazo rígido (30 s USB/Wi-Fi, 45 s BLE), estados visíveis (na fila, verificando, cadastrando, falhou, concluído), Cancelar em qualquer etapa sem cadastro parcial e resultado tardio descartado; fila Bluetooth (uma verificação por vez) também usada por "Adicionar automaticamente", que ganhou Cancelar. Orientação de PIN no cartão.
- #157: tabela `app_favorites` (lista única, com data e remoções) migrada a partir dos favoritos confirmados. Mesclagem rádio ↔ app ao conectar e a cada 15 s: mudança no rádio entra no app se o app não mexeu no nó desde a última sincronização; senão o app vence e o comando vai ao rádio. Comandos `setFavorite`/`removeFavorite` em ritmo controlado (5 por ciclo, 1 s entre eles), limite seguro de 50 favoritos no rádio, nós desconhecidos pelo rádio ficam pendentes. Favoritar funciona sem rádio. Opção "Sincronizar favoritos com este rádio" por conexão e "Sincronizar favoritos agora" no menu do rádio.
- #158: balões com remetente colorido em cima (canais), nome curto e Node ID, agrupamento por remetente em até 5 min, avatar com iniciais, citação de resposta (`↪ Autor: trecho`) como bloco, horário e ✓/✓✓ no rodapé. Conversas privadas sem cabeçalho.
- #159: tipo "ping" implementado como checagem de presença (pedido de NodeInfo com resposta) para nós observados por RF calados entre 2 h e 72 h (configurável), prioridade para o silêncio mais longo, espera 30 min → 24 h, contagem zerada quando o nó volta sozinho, pausa com utilização do canal acima de 25% ou airtime TX acima de 7%, cota de 50% das consultas por hora, papéis silenciosos excluídos. Coluna Presença na aba Nós e nós sem resposta esmaecidos no mapa. Opção "Vizinhos" removida.
- #153: pacote `.deb` (amd64) para Ubuntu/Linux Mint com `/opt`, comando `pt2vhf-mesh-analyzer`, atalho e ícones; testado no CI com `apt install`, execução, `apt remove` e dados preservados.
- #160: imagem `ghcr.io/alexpmr/pt2vhf-mesh-analyzer` (amd64 + arm64), usuário sem root, volume `/data`, healthcheck, encerramento limpo com SIGTERM, acesso só pelo próprio servidor (checagem de Host e CSRF mantidas). Modo container no app (`PT2VHF_CONTAINER=1`) e aviso de atualização por imagem.
- CI: criação do DMG no macOS com até 3 tentativas (falha intermitente do `hdiutil`).

Validação: testes Python (prazo, cancelamento e fila BLE, prioridade USB, favoritos, presença, modo container), regressões Chromium v0.6.34–v0.6.38, `.deb` e container testados no pipeline. Aceite físico pendente: rádios BLE com PIN, USB + Wi-Fi reais, sincronização de favoritos com o celular, ping de presença em malha real e container em Raspberry Pi.

# v0.6.37 — Rádios detectados automaticamente e seletor do rádio ativo

Inclui todo o conteúdo da v0.6.36 (Linux, macOS, horários e rolagem das mensagens), que não chegou a ser publicada separadamente.

- #149: monitoramento em segundo plano de portas USB (ao plugar), anúncios mDNS e BLE próximos (RSSI ≥ −70 dBm, serviço GATT Meshtastic). Rádios USB são verificados pelo handshake Meshtastic antes do aviso. "Adicionar e conectar" verifica, cadastra com o nome lido do rádio, Node ID e conexão automática marcada, e conecta; com outro rádio ativo, o novo fica em espera e o aviso oferece "Usar este agora". "Agora não" vale até o dispositivo sair e voltar; "Nunca" é persistido. Preferência por tipo (USB, Wi-Fi, Bluetooth) em Configurações → Conexões. Portas já cadastradas nunca são abertas e nada é transmitido por RF.
- #150: botão "Configuração Automática" renomeado para "Detectar automaticamente".
- #151: botão "Adicionar automaticamente" ao lado de "Adicionar conexão manualmente": varre USB (somente portas com VID USB), mDNS e BLE próximo, verifica cada candidato pelo protocolo Meshtastic e cadastra os que ainda não existem (por porta, host, endereço BLE ou Node ID). Resumo com adicionados, já configurados, sem resposta e erros; execução repetida não duplica.
- #152: o indicador de conexão abre o seletor do rádio ativo, com somente a conexão ativa e as habilitadas cujo dispositivo está presente (porta COM enumerada, TCP respondendo, BLE visto), sem abrir a porta nem transmitir. A troca fecha o rádio atual e conecta o escolhido; se ele não conectar em 45 s ou der erro, o anterior volta. O escolhido vira o rádio preferido e conecta primeiro no próximo início. Nunca há dois rádios ativos (#139). Reconectar e Gerenciar conexões continuam no menu.
- O Node ID do rádio passa a ser guardado na conexão quando ela conecta, para evitar cadastro duplicado.

Validação: testes Python (detecção, adição automática, troca com sucesso e com retorno, disponibilidade) e regressão Chromium do seletor, do aviso e do resumo. Aceite com rádios físicos em USB, BLE e Wi-Fi pendente.

# v0.6.36 — Linux, macOS, horários e rolagem das mensagens

- Plataformas: novos pacotes **Linux x64** (`.tar.gz` com executável, ícone e `instalar.sh`) e **macOS** Apple Silicon e Intel (`.dmg`, app com assinatura ad-hoc e permissão de Bluetooth). No macOS a janela usa o WebKit do sistema; no Linux a interface abre no navegador padrão. Atualização interna permanece exclusiva do Windows; nas demais plataformas o botão abre a release.
- Downloads: o ZIP de código-fonte deixou de ser publicado na release. SHA256SUMS.txt cobre todas as plataformas.
- #144: o rxTime vem do relógio do rádio; quando ele difere até 15 min do PC, a mensagem usa o horário de recepção local (defasagem do relógio do rádio era a causa provável do “há 3 minutos” fixo). Histórico fora dessa janela preserva o horário original. Horário do rádio persistido em `radio_time_ms` e exibido no detalhe. Horário futuro mostra data/hora absolutas.
- #145: o refresh periódico só atualiza os horários relativos, sem reconstruir os balões nem mover a rolagem. Ao ler o histórico, a posição é preservada por âncora e novas mensagens mostram “↓ Novas mensagens”; no final da conversa, acompanha automaticamente. Troca de conversa e envio levam ao final.
- #146: botão da barra superior mostra somente “Atualizado” (verde) ou “Nova Versão” (laranja) após verificação bem-sucedida; “Verificando...” e “Verificação indisponível” como estados neutros. Versões no título do botão e no diálogo.

Validação: testes Python, regressões Chromium (v0.6.34 e v0.6.36) e empacotamento Windows/Linux/macOS no pipeline, com teste da API local em cada pacote. Rádio físico, BLE no macOS/Linux e janela nativa no macOS precisam de aceite em equipamento real.

# v0.6.35 — Aviso de nova versão

- Atualizações: ao detectar versão nova, além do indicador NOVA VERSÃO no menu superior, o diálogo de atualização abre sozinho perguntando "Deseja atualizar agora?", com Atualizar agora / Depois / Abrir release. "Atualizar agora" segue o fluxo existente (download, SHA256, instalação); "Depois" adia a mesma versão por 24 h. Não abre sobre outro diálogo (primeira execução, sem conexão) nem se a atualização já estiver em andamento.

# v0.6.34 — Conexões, mensagens e acompanhamento de consultas

- #138: pesquisa do mapa exige as duas pontas correspondentes também nos fluxos lógicos; contagens e autozoom respeitam o filtro. Pulsos deixam de aparecer em nós ocultos.
- #139: múltiplas conexões persistidas, primeira conexão de rádio bem-sucedida vence de forma atômica; demais ficam em espera e suas interfaces excedentes são fechadas. Timeout de conexão de 20 s por SDK. MQTT permanece receptor independente. Conexão automática marcada em novos cadastros e na descoberta; escolha anterior preservada. Nome longo detectado atualiza o nome da conexão. Salvar conexão destacado; formulário de adição não desaparece no refresh periódico.
- #140/#143: mensagens de hoje exibem tempo relativo, anteriores exibem data e horário; tooltip com instante completo. Balões preservam quebras de linha e texto literal seguro.
- #141: comando de favorito/desfavorito atualiza o estado local persistido; estado pendente explícito separado da confirmação do NodeDB. Cache antigo não desfaz a escolha. Erro de envio não altera o estado local.
- #142: indicador verde mostra o nome da conexão ativa; sem rádio conectado mostra “desconectado”.
- #124: painel recolhido no canto superior direito do mapa com consultas manuais/automáticas, histórico de resultado e contagem de lotes desta janela. Candidatas de automação são diferenciadas de consultas efetivamente enviadas. Lotes ainda pertencem à janela que os iniciou, não a uma fila persistida central.
- #125: Salvar automação habilita com edição; ao sair, Salvar/Descartar/Continuar. Erro de gravação mantém a edição e a tela. Fechamento do navegador usa aviso nativo.
- #126 parcial: áudio deixa de depender da opção de animar e é desbloqueado por interação; som físico/WebView2 ainda requer aceite.
- #59: ranking analisa todos os enlaces RF diretos selecionados, procura posições históricas próximas à observação e agrega pares invertidos/repetidos. Diagnóstico informa quantos foram excluídos por posição. Traceroute não é promovido a RF direto.
- #137 parcial: traceroute manual abre os detalhes do nó com acompanhamento da solicitação e da resposta. Ausência de resposta não cria enlace fictício.

Validação: testes automatizados Python, interface Chrome e empacotamento Windows no pipeline. Rádio físico e atualização no PC do usuário precisam de aceite. Tradução integral, relatório avançado equivalente ao modelo e demais pendências antigas não são declaradas concluídas.

# v0.6.33 — Mensagens, Contato e Automações

- #80: padrões de automação RF 1 min, 24/h, 60 s, 24 h, tipos permitidos; botão Salvar automação amarelo, preferências antigas preservadas.
- #134: nova aba Sobre em /sobre, banner de contato WhatsApp e e-mail, Ajuda preservada.
- #129: seletor de emojis e contador UTF-8; limite de 220 bytes respeitado antes da transmissão.
- #130: resposta contextual ao clicar no balão, prévia no compositor, citação textual curta para interoperabilidade básica.
- #131: reenvio de mensagem com erro por botão direito, após aviso de risco de duplicidade; nova tentativa via rádio TX ativo.
- #132: Canal primário fixo; favoritos importados do NodeDB têm área fixa e os outros contatos permanecem roláveis/pesquisáveis.
- #136: favoritos na aba Nós, indicador de estado conhecido/desconhecido e comandos locais ao rádio para Favoritar/Desfavoritar, leitura periódica do NodeDB e confirmação explícita (mocks validados; hardware real pendente).
- #79 parcial: cache radio-isolado de flags explícitas isFavorite/is_favorite, armazenado no SQLite; modificação no rádio e sincronização contínua permanecem pendentes de teste real.
- Backlog total NÃO foi encerrado; validar com usuário, rádios físicos, Windows 10/11.

# v0.6.32 — Validar atualização automática com execução real

- Regressão Windows: fixture PyInstaller com launcher finalizando exit 0 e processo sucessor lançando serviço HTTP com atraso e nonce único; confirma conclusão por /health sem confundir bootloader com GUI.
- Segurança: nonce não vazio e exato é obrigatório para aceitar /health; versão e ui_ready também exigidos.
- Estado da atualização: falha histórica da confirmação e versão já executada passa a ser aviso **reinício não confirmado**, sem declarar falha de instalação.
- Testes de estados failed/installed/unverified, migração visual e dismiss. Mantidas correções WebView2 de v0.6.31.
- Homologação do atualizador completo em Win10/Win11 com rádio real ainda depende de aceite de campo (#103).

# v0.6.31 — Correção da reinicialização WebView2 e confirmação do atualizador

- #103: diagnóstico fundamentado nos quatro logs reais v0.6.30. Inno Setup terminou com exit=0; nova instância foi iniciada, mas o monitor registrou `Updated application exited early: 0`.
- Causa principal altamente provável desde v0.6.25: `PDFExportBridge.window` público permitia ao scanner JS API do pywebview percorrer `Window.native`/objetos COM WebView2. Corrigido para `_window` privado, mantendo `save_pdf` exposto.
- Runner de atualização verifica `/health` autenticado por versão, nonce e UI pronta antes de avaliar saída do primeiro launcher. Saída normal com exit=0 não causa falha imediata; continua aguardando prontidão até o prazo configurado. Código não-zero sem prontidão reporta erro.
- Testes de regressão do scanner pywebview, do PDF Bridge e da ordenação do health check do PowerShell, além da suíte Windows.
- Aceite em hardware real requerido: atualização in-app de v0.6.30 para v0.6.31, Win10/Win11 Setup/Portable; não declarar bug encerrado apenas com CI.

# v0.6.30 — Legenda recolhível e pesquisa/menções em Mensagens

- #119 Mapa: legenda compacta no canto inferior esquerdo, recolhida por padrão, acessível por teclado e com detalhes da topologia recolhíveis. Os indicadores continuam atualizando em plano de fundo sem abrir o painel.
- #120 Mensagens: autocomplete acionado por @ insere somente nome longo literal, sem @ e sem trocar espaços por underscores; substitui somente a expressão selecionada, preserva texto adjacente e verifica limite UTF-8.
- #121 Mensagens: campo Pesquisar nó..., filtragem local progressiva de nome longo, curto, amigável, aliases e Node ID; preserva canais, conversa aberta e nós offline.
- Regressões confirmam estados de checks de mensagens e indicador de atualização verde quando a versão é a mais recente (#57, #118).
- Backlog histórico permanece rastreado; não confundir teste simulado/CI com aceitação de rádio físico.

# v0.6.29 — Reinício do Portable e confirmação pós-atualização (#103)

- Remove estado privado PyInstaller herdado no processo externo e antes do relançamento; usa ProcessStartInfo com UseShellExecute=false e reset explícito do runtime.
- Mantém perfil e porta na linha de comando; confirmação /health exige versão, nonce da tentativa e interface pronta. Janela de inicialização de 180 s com último estado HTTP diagnosticado.
- Aviso de falha persistido informa data e versão atualmente executada, sem declarar instalação manual defeituosa nem apagar evidência.
- Teste Windows pós-build com EXE real, nome versionado, pasta/perfil com espaços, ambiente temporário inválido, substituição, backup e preservação do nó salvo; UI readiness simulada via API em modo headless. Mantido teste onefile com encerramento do bootloader anterior.
- Não foi reproduzida a causa exata no PC afetado; ausência de logs e versões de origem/destino impede concluir causa única. Aceite físico Portable N→N+1 e WebView2 permanece pendente. Bootstrap manual necessário para versões com runner antigo. Ícone Windows #77 e botão verde #118 continuam fora deste escopo.

# v0.6.28 — Ícones por role do dispositivo

- Mapa com 13 ícones SVG customizados, papel desconhecido explícito e legenda recolhível. Atividade continua no contorno verde/âmbar; cliques e menu contextual preservados.
- `role` importada do NodeDB do device e das respostas NodeInfo em dicionário/protobuf, incluindo CLIENT numérico zero. Metadados parciais não apagam papel conhecido.
- Recuperação única de roles ausentes nos pacotes históricos, sem criar nós nem alterar last_seen ou posições.
- Testes de roles oficiais, consulta inicial, NodeInfo ao vivo, recuperação e SVGs reais. Validação física no rádio permanece necessária. Atualizador interno do Portable continua pendente (#103).

# v0.6.27 — Confirmações de mensagens e padrões de automação

- Mensagens: envio com wantAck também nos canais; tratamento de ACK/NAK correlacionado por conexão, packet ID e origem. ACK implícito confirma propagação, ACK do destinatário privado confirma entrega; nenhum confirma leitura humana.
- Um check verde ao aceitar pelo rádio; dois com propagação/entrega confirmada; relógio durante tentativa; vermelho em NAK ou após 180 s sem confirmação. Callback adiantado ao INSERT é armazenado até persistência; callbacks de interface substituída são ignorados.
- Automações ativas por padrão, com todos os tipos selecionados; migração única mantém cotas e intervalos e preserva alterações posteriores do usuário. Ping/Vizinhos permanecem indisponíveis até suporte real da API/firmware; não há transmissão fictícia.
- Retirado contador redundante X conexões ativas da faixa superior. Preservados radar, seleção/exclusão em lote, temas, PDF e período Todo das versões recentes.
- Mantida distribuição Windows 10 1809+/Windows 11 x64, WebView2 como pré-requisito e aliases compatíveis com clientes antigos.
- Testes de isolamento de fonte/ID/emissor, ACK antecipado, NAK, expiração e persistência da escolha do usuário. Hardware e ACK de diferentes firmwares ainda requerem validação de campo.

# v0.6.26 — Windows 10 (1809+) / Windows 11 x64

- Setup e Portable combinados para Windows 10 x64 (build 17763/1809+) e Windows 11 x64.
- MinVersion=10.0.17763 no instalador Inno Setup; arquitetura AMD64 obrigatória.
- Build PyInstaller e verificação de cabeçalho PE x64/subsystem; pipeline do GitHub Actions ainda executa em Windows Server 2022, então a abertura real em Windows 10 requer aceite físico/VM.
- Novos nomes Win10-Win11-x64 em releases, atualizador, hash e links do README.
- Aliases Win11-x64 na mesma release garantem atualização via aplicativo para clientes instalados v0.6.25 e anteriores.
- WebView2 Runtime é pré-requisito em Windows 10/11, podendo necessitar instalação separada.
- Conservadas configurações e dados SQLite existentes. Nenhuma migração destrutiva.

# v0.6.25 — Temas, PDF e período Todo

- Configurações → Sistema: temas Escuro (`#202126`), Cinza (`#333438`) e Claro, escolha imediata e persistência no SQLite (#112).
- Estatísticas: **Todo** selecionado no filtro de período inicial, usado também no relatório (#114).
- Relatório PDF: integração com diálogo de salvamento nativo em WebView2 e download padrão na Web; status apenas após gravação confirmada no aplicativo, cancelamento tratado (#113).
- Testes de regressão de geração PDF sem rádio, endpoint HTTP, SaveDialog simulado e configurações.
- Testes de campo no Windows e pendências anteriores do backlog continuam acompanhados.

# v0.6.24 — Exclusão bulk, fila de consultas RF, enlaces e radar

- Exclusão múltipla do NodeDB do rádio local e catálogo SQLite: confirmação dupla, ACK individual, tratamento de falhas parciais e cancelamento dos itens não enviados (#105).
- Novas consultas em lote são enfileiradas durante lotes existentes; fila FIFO com limite de RF compartilhado, progresso e resultados por nó (#105).
- Ver → Enlaces inicial ligado para perfis novos, com preferências explícitas preservadas e alterações salvas em SQLite (#108).
- Radar OFF respeitado durante inicialização e após downloads assíncronos; slider de opacidade ampliado e controle instantâneo (#109, #110).
- Mapa com diagnóstico de vínculos conhecidos, filtrados e desenhados, mais normalização de IDs de nós (#90).
- Pipeline de regressão Windows e verificações simuladas; testes físicos de exclusão e visualização em campo ainda necessários.

# v0.6.23 — Seleção múltipla de nós e consultas RF em lote (#105)

- Clique simples seleciona sem abrir, clique duplo abre detalhes; Ctrl e Shift selecionam nós individuais ou intervalos; Ctrl+A seleciona os nós do filtro atual.
- Menu contextual da seleção múltipla permite NodeInfo, Posição, Telemetria e Traceroute, com confirmação explícita e exatamente um rádio TX habilitado. Exclusão permanece individual, sem opção destrutiva em massa.
- Fila serializada com intervalo mínimo de 60 s, limite interno de 6 consultas/hora no lote, verificação do estado da resposta antes do próximo TX, timeout de backend de 30 s, resultados por nó e cancelamento dos envios futuros.
- Testes regressivos Node.js/CI para seleção, menu e envio RF simulado sem hardware. Validação física, atualizador Windows real e demais issues ainda pendentes. Não declarar backlog completo saneado.

# v0.6.22 — Apagar nó no rádio e no banco; padrão visual RF

- #102: menu contextual compartilhado e janela de detalhes ganham Apagar nó do banco e do rádio, com confirmação nominal e seleção inequívoca de um rádio direto conectado.
- Envia remove_by_nodenum ao próprio rádio conectado, com sessão administrativa e ACK/NAK correlacionado por ID do comando e emissor local. Somente após confirmação sem erro remove o cadastro SQLite e caches do SDK. Timeout de 30 s, desconexão e rejeição preservam o cadastro; falha posterior do banco informa estado parcial.
- Protege rádio próprio e IDs reservados; MQTT não pode executar exclusão. Mensagens, pacotes, posições e enlaces históricos permanecem no banco. Nó ativo pode reaparecer por novas recepções. Remoção física nos firmwares em uso ainda exige teste de bancada.
- #106: também fluxos lógicos recebidos por rádio usam cor/espessura RF configuradas, amarelo contínuo por padrão. Popup e ranking continuam diferenciando caminho desconhecido, rota e RF direto comprovado; MQTT permanece pontilhado.
- Novos testes: ACK/NAK, erro padrão do protobuf, emissor/ID incorretos, timeout, confirmação explícita, IDs protegidos, MQTT, concorrência, preservação do histórico, redescoberta, falha parcial do banco e endpoint com CSRF.
- Mantida retenção automática de somente uma release completa. Seleção múltipla/duplo clique e operações em lote (#105) continuam pendentes nesta versão; a exclusão implementada aqui é individual.

# v0.6.21 — Reinício independente e estilo dos trechos RF

- #103: runner reinicializa o ambiente PyInstaller antes do relançamento, evitando reutilizar temporários da instância encerrada; aguarda também o bootloader que ainda pode manter o EXE aberto.
- Setup recebe diretório explícito da instalação atual e grava update-setup.log para separar falha de instalação de falha de relançamento.
- #106: trechos RF de traceroute e vizinhança usam cor/espessura RF configuradas (padrão amarelo contínuo); popup preserva o grau de evidência. Ranking de RF direto não foi ampliado.
- Fluxo lógico duplicado não sobrepõe trecho topológico já desenhado no mesmo par/fonte/transporte. Fluxos sem caminho identificado continuam pontilhados; MQTT permanece distinto.
- Novos testes executam as funções JavaScript reais e um ciclo Windows com EXE onefile de teste, substituição Portable, PowerShell real e health check após reinício. Esse teste usa fixture sem rádio/WebView2.
- Instalar esta versão manualmente: o salto a partir da v0.6.20 ainda é executado pelo runner antigo. O novo runner passa a valer nas atualizações iniciadas pela v0.6.21.
- Causa de ambiente herdado identificada no código; não afirmar resolução universal do erro de campo sem teste no computador afetado. Validação física de Setup/WebView2/radio permanece pendente.

# v0.6.20 — Consultas RF com timeout de 30 segundos

- #104: NodeInfo, Posição, Telemetria e Traceroute passam a usar prazo de 30 segundos após retorno do envio pelo SDK, medido por relógio monotônico.
- A expiração é verificada também antes de nova consulta e antes de correlacionar resposta, sem depender da abertura do painel de status. Consultas expiradas liberam nova tentativa.
- Consultas em transmissão também impedem duplicatas. Desconexão ou substituição da interface finaliza pedidos antigos; respostas tardias não reativam pedido expirado.
- Testes de limite exato, retentativa sem polling, envio lento, resposta tardia, troca de conexão e alteração do relógio do sistema.
- Esta versão não implementa exclusão de nó no rádio/banco (#102) nem seleção e consultas em lote (#105). Falha de instalação/reinício pelo atualizador (#103) permanece em investigação; usar instalação manual se necessário.
- Validação em rádio físico e ciclo de atualização Windows ainda pendentes.

# v0.6.19 — Barra única do mapa, Mensagens e Dispositivo Wi-Fi

- #95: une os cinco contadores principais e os controles do Mapa em uma linha, preserva os IDs e os eventos dos elementos.
- #98: retira Conexão TX da barra de Mensagens e preserva o bloqueio de envio ambíguo quando vários rádios estão conectados.
- #96: integra PR #97 para expandir automaticamente seção Wi-Fi e evidenciar o campo protegido, mantendo senha fora do browser.
- Testes de integração de interface e pipeline Windows 11.
- Não resolve ainda as falhas de updater #69, enlaces #90, RX #91 ou NodeInfo #89; testes físicos pendentes.

# v0.6.18 — Interface de conexões, barra do mapa e indicadores de mensagens

- Incorporada PR #93 aprovada: formulário de novo cadastro só aparece automaticamente se nenhuma conexão estiver cadastrada; configuração manual sob demanda; Configuração Automática utiliza descoberta USB/Serial, BLE e mDNS e requer confirmação para ativar rádio.
- Retirado seletor Conexão do Mapa, preservadas fontes e dados armazenados; Ver, Pesquisar, Enquadrar e Atualizar permanecem na mesma barra.
- Indicadores de mensagens: relógio durante tentativa/espera; um check verde para envio aceito pelo rádio; dois checks verdes para estados de entrega/propagação explicitamente confirmados, se emitidos pelo backend. Mensagens privadas não apresentam leitura sem recibo real.
- Não resolve ainda P0 #90/#91 nem atualização do Windows #69, diagnóstico #56 e NodeInfo #89.

# v0.6.17 — Descoberta de rádios e diagnóstico de enlaces no mapa

- **#72 / #31:** Configurações → Conexões ganha autodetecção assíncrona de candidatos por USB/Serial, Bluetooth LE e anúncios mDNS de serviços Meshtastic TCP. Nenhuma conexão é ativada automaticamente; os resultados são classificados explicitamente como *não verificados pelo protocolo*.
- **#76:** mapa informa os trechos da topologia conhecidos no SQLite mas não desenhados por ausência de coordenadas. Continua a não converter traceroutes multissalto sem evidência em RF direto.
- **Windows:** PyInstaller inclui zeroconf; API de descoberta separa GET de consulta do POST que inicia a busca (CSRF obrigatório).
- **Testes:** regressões de descoberta com portas duplicadas e falha BLE, proteção CSRF da API e testes preexistentes. 
- **Atenção:** esta é uma versão de campo; não fecha automaticamente as demais 63 issues abertas. A validação de topologia real, BLE e mDNS depende do ambiente do usuário.

# v0.6.16 — Monitor TX/RX e aprimoramentos da topologia

- Consultas RF do usuário e da automação gravadas como TX com origem do rádio local e destino individual do nó, packet ID e tipo; separação de RX na aba de tráfego e exportação CSV (#85).
- Preserva histórico RX no SQLite com migração idempotente da coluna direction.
- Integra mudanças da PR #84 portando decomposição orientada de traceroute do Traffic Analyzer, com testes de integração pacote → SQLite → API. #76 permanece aberta até validação do mapa real.
- Não considera mensagens de broadcast RX como TX. Mantém a cautela sobre RF direto sem evidência.
- Pendências conhecidas: autodetecção de rádios #72, ícone Windows #77 e validação de atualização #69.

# v0.6.15 — Correção de inicialização do atualizador Windows (15/10/2026)

- Corrige o launcher PowerShell externo removendo a combinação DETACHED_PROCESS + CREATE_NO_WINDOW; mantém execução oculta.
- Captura stdout/stderr no perfil local em update-runner-output.log, além do update.log, para diagnosticar falhas de execução e ausência do marcador runner_ready.json.
- Adiciona teste de integração Windows que inicia PowerShell real em modo oculto e verifica marcador de prontidão autenticado com nonce.
- **Importante:** a correção ainda requer validação física do ciclo Setup → Setup e Portable → Portable; sem afirmar sucesso universal até teste no PC afetado. Outros itens do backlog permanecem abertos.

# v0.6.14 — Automação inteligente para completar informações dos nós (15/10/2026)

- **#80 (implementação inicial):** aba Automações com ativação explícita, consultas NodeInfo, Posição, Telemetria e Traceroute separadamente configuráveis, fila de nós com dados faltantes/desatualizados, simulação sem TX, execução manual e acompanhamento do estado.
- **Segurança RF:** default desligado, somente rádio ativo TX e nós realmente observados nessa fonte; nunca enviar consultas via MQTT. Aguarda anúncios iniciais de nós novos, apenas uma consulta aguardando resposta, intervalo mínimo, cota real de transmissões por hora, timeout com backoff progressivo e pausa com múltiplos rádios.
- **SQLite:** persiste preferências, tarefas, tentativas, resultados e histórico de transmissões. Histórico de nós antigos continua intacto.
- **Compatibilidade:** NeighborInfo e Ping são mostrados como futuras opções indisponíveis até haver suporte real do SDK/firmware (não são simulados). Nem todo nó fornece posição ou telemetria.
- **Testes:** casos offline e integração API/CSRF, janela de escuta dos novatos, rádio único, MQTT, limites de TX, backoff e persistência em reinicialização.

**Estado:** automação implementada em código, mas exige validação de campo com rádio Meshtastic e diferentes firmwares. Bugs anteriores de updater/instalador, ícone da barra de tarefas e descoberta automática de conexões permanecem abertos. Esta release não encerra todo o backlog.

# v0.6.13 — Consultas RF e senha Wi-Fi protegida (15/10/2026)

- **#76 (parcial):** respostas de traceroute passam a preservar listas de saltos de ida e retorno e os valores brutos de SNR; o painel do nó apresenta a sequência identificada. Respostas sem intermediários mostram aviso explícito e não geram enlaces RF diretos inventados. A camada topológica existente continua utilizando apenas evidências de saltos observadas.
- **#6 (parcial):** o editor do dispositivo agora permite substituir explicitamente a senha Wi-Fi da configuração *network* em firmwares que a oferecem, usando campo protegido sem revelar a credencial armazenada. Campos não editados, incluindo a senha, são preservados. O diff de confirmação nunca mostra segredos.
- **#75 (parcial):** instalador aguarda até 10 segundos a saída dos processos após encerramento, verificando o caminho executável real para evitar falso código 3 caso haja reciclagem de PID. Validação em Windows com a falha original ainda é necessária.
- **#74 (entrega):** adicionar EXE Portable direto aos assets da release, mantendo o ZIP original para compatibilidade com versões antigas do atualizador.
- **Testes:** casos de traceroute sem rota, rota com saltos, pacote protobuf nativo, não vazamento de Wi-Fi PSK, preservação da senha e validação de nova credencial.
- **Limites:** editor e consultas exigem validação física com rádios Meshtastic. Permanecem abertas as pendências de sincronização automática de favoritos, automações RF, descoberta USB/BLE/Wi-Fi, ícone em cache no Windows, instalador/atualizador e a evolução do mapa de topologia. Esta release **não resolve todo o backlog**.

# v0.6.12 — Laboratório de consultas remotas (experimental)

- Controles de NodeInfo, posição, telemetria e traceroute para testes com rádio Meshtastic conectado, com solicitações identificadas e status individual.
- Resultados recebidos exibidos no painel de detalhes; timeouts não são tratados como sucesso.
- Funções ainda experimentais: respostas dependem de firmware, rádio e protocolo; recomenda-se validação em bancada antes de uso regular.
- Ping e vizinhos, botão Tudo, histórico durável e refinamento de correlação continuam pendentes.

# v0.6.11 — Cabeçalho e atualização idempotente

- Navegação, LEDs de tráfego, status do rádio e botão de atualização na mesma linha em larguras adequadas, com adaptação responsiva em janelas menores.
- Requisição repetida de atualização da mesma versão retorna o progresso da operação já iniciada, sem gerar erro de atualização em andamento.
- Atualização e reconexão automática completas ainda dependem de testes em equipamento real; failover, ranking RF e demais recursos do backlog permanecem pendentes.

# v0.6.10 — Reconexão de rádio

- Clique no indicador de rádio conectado/desconectado inicia reconexão quando existe uma única fonte de rádio habilitada.
- Reconexão lógica aguarda o encerramento do worker anterior antes de reabrir a porta; falha explicitamente se não liberar em 10 segundos.
- Com nenhuma ou múltiplas fontes habilitadas, encaminha para Configurações > Conexões sem desconectar indiscriminadamente.
- Endpoint local de reconexão protegido por CSRF; fontes MQTT somente RX não são elegíveis.
- Permanecem pendentes validação com dispositivo físico, failover em grupo, ranking RF e consultas remotas completas.

# v0.6.9 — Layout e atividade multitransporte

- Seletor de conexões do mapa exibe Conectado somente quando a fonte está ativa; fontes offline não mostram error.
- Checkbox Conectar automaticamente ao iniciar alinhado ao texto.
- Cabeçalho organizado em identificação, navegação e indicadores operacionais.
- RX MQTT real participa da atividade agregada sem alegar recepção RF; suporte existente USB/BLE/TCP preservado.
- Bolhas de mensagens com espaçamento mais compacto.
- Reconexão forçada, failover, ranking RF e consultas remotas completas continuam pendentes de implementação e testes.

# v0.6.8 — Correções de atualização

- Mensagens de erro do atualizador mais claras e úteis para diagnóstico.
- Registro local de falha de handshake/abertura do instalador externo no update.log.
- Diálogo de falha deixa de mostrar progresso completo e botão de cancelamento incoerente.
- O fluxo continua sendo iniciado com um clique no indicador de versão; não há confirmação adicional do aplicativo no percurso bem-sucedido.
- Requisitos de consultas remotas completas, ranking RF e exportação de diagnósticos continuam no backlog para validação independente.

# Changelog — PT2VHF Mesh Analyzer

## v0.6.7 — 15/10/2026 — Instalação segura, conexões e popup de enlaces

- **#15 / #34 (parcial, prioritário):** instalador Inno Setup utiliza fechamento controlado antes de substituir o executável. Um processo PowerShell verifica o caminho exato do EXE e o SID do usuário, solicita fechamento gracioso, espera até 15 segundos e encerra **apenas** instâncias ainda vivas do próprio Mesh Analyzer, registrando resultado em `installer-close.log`. A instalação é interrompida se não puder parar os processos com segurança, para não travar aguardando o Gerenciador de Tarefas. **Necessário teste físico Win11 Setup e Portable**; atualização interna ainda depende de validação independente.
- **#40 (parcial):** o Setup agora instala uma cópia estável do ICO `{app}\branding\mesh-analyzer.ico` usada pelos atalhos Iniciar/Área de Trabalho, pela referência de desinstalação e pela janela WebView2. A edição Portable continua usando o ícone embutido. Testar a barra de tarefas e atalhos antigos no Windows 11.
- **Indicador de rádio:** status no cabeçalho, verde com pelo menos uma conexão Meshtastic USB/BLE/TCP ativa e vermelho quando nenhuma estiver conectada; tooltip mostra estados por dispositivo. MQTT observador não conta como rádio.
- **#45 — Rádio desconectado:** clicar **Enviar** sem rádio TX abre janela informativa com **Ir para Conexões** e **Fechar**, preservando rascunho e destinatário. Sem fonte TX, não envia pacotes. Ações acessíveis via teclado e Escape.
- **#51 (parcial):** clique em uma linha RF, rota observada ou comunicação lógica no mapa abre popup com os dois nós, classe de evidência, fonte, primeira/última observação, contagem e distância geográfica apenas com posições temporalmente válidas. Nomes clicáveis abrem a ficha do nó. RSSI/SNR por aresta permanecem indisponíveis até criar armazenamento de evidências por trecho.
- **Testes:** novos contratos de interface, identidade de ícone, proteção do instalador e exibição de enlaces.

**Limitações importantes:** esta release **não conclui todo o backlog**. Falhas de atualização automática e reinício (#34) ainda exigem verificação no Windows real; consultas remotas de NodeInfo/telemetria/posição/traceroute/ping (#46/#27), ACK/REJ correlacionados e recibos de leitura humana (#4) não são declarados operacionais. A confirmação Meshtastic de entrega não significa leitura. Nenhum processo de software de terceiros deve ser encerrado.

## v0.6.6 — 14/10/2026 — Menu Ver, rótulos, Nós e Mensagens

- **#49:** Camadas dentro do menu **Ver ▾** com radar, opacidade, relevo, nomes curtos, nós, enlaces e waypoints; botão redundante removido.
- **#48:** destino broadcast (!ffffffff) exibido como **broadcast** no Tráfego e exportação, mantendo dados técnicos originais.
- **#47/#35:** nomes em português para tipos de tráfego (Telemetria, Posição, Informações do nó, Mensagem) e nomes amigáveis para modelos de hardware conhecidos.
- **#8 (parcial):** saltos calculados com base em pacotes RF verdadeiros por nó e fonte, sem atribuir MQTT nem caminhos físicos inferidos; reconhecimento ampliado do nó local para distâncias quando as duas coordenadas são conhecidas.
- **#45 (parcial):** selector de rádio TX exige interface de envio real e apresenta motivo claro quando inoperante.
- **#4 (parcial):** relógio durante tentativa de envio, check único após aceitação do rádio, erro visível e lista de conversas com prévia. **Dois checks de leitura não implementados** pois ACK Meshtastic não comprova leitura humana.
- **#46 (parcial):** menu contextual comum para nós em Mapa, Nós e Mensagens com Mensagem, Detalhes, Localizar e Copiar Node ID. Consultas remotas sem backend estão explicitamente indisponíveis.
- **Qualidade:** testes para saltos, transmissão, identidade local, broadcast, rótulos e controles do menu Ver.

**PENDENTE:** backlog extenso continua aberto. Instalação/reinício via updater #34 e envio efetivo #45 exigem validação real Win11 com rádio. Consultas RF, recibos de leitura compatíveis, LAN autenticada, NodeDB contínuo e todos os demais itens não são declarados completos.

## v0.6.5 — 14/10/2026 — Descoberta passiva de tráfego e atualização assistida

- **#22:** cada pacote unicast normal aceito gera uma **relação lógica observada** entre origem e destino com quantidade, fonte, intervalo e separação por transporte (rádio x MQTT). Isto **NÃO é RF direto**. Broadcasts e endereços inválidos não produzem linhas fictícias. Tráfego histórico é recuperado incrementalmente pelo SQLite em thread de baixa prioridade, com chave idempotente por pacote.
- **#22 (experimental):** recepção de pacote com `hopStart == hopLimit`, RSSI/SNR físico disponível e nó receptor local efetivamente identificado permite registrar um enlace `confirmed_direct_rf` entre originador e o receptor local. Sem essas evidências não há promoção. Enlaces resultantes podem exigir coordenadas válidas dos dois nós para aparecer no mapa.
- **#11:** pulso de pacotes comuns da fonte, independentemente do checkbox "Realçar origem" e sem exigir traceroute; MQTT com tom visual separado; eventos sem coordenadas exibem mensagem de atividade e contador. **Não** simula movimento ao longo de saltos desconhecidos.
- **#22 mapa:** as linhas de comunicações lógicas usam traço pontilhado lilás e legenda explícita "caminho RF desconhecido", não são inseridas como RF direto; geradas separadamente de enlaces de traceroute, com contadores e diagnósticos.
- **#2:** clique no botão superior da nova versão inicia diretamente modal de progresso de download verificado com SHA256, sem changelog prévio nem confirmação do navegador; cancelar funciona enquanto o download não estiver finalizado.
- **#34:** execução de instalador externo recebe diretório de trabalho, detecta instalações Inno Setup em diretórios alternativos, aguarda até 90 s por WebView2/prontidão, e, antes de fechar o app, exige confirmação de execução do processo externo por nonce. O instalador Setup usa /SILENT para exibir progresso real (em vez de /VERYSILENT); logs registram fase de instalação e código de saída, além de diálogo de falha com opção de localizar log. **A causa do erro relatado no Win11 ainda NÃO foi confirmada com logs; teste físico é obrigatório antes de encerrar a issue.**
- **Testes:** unicast, broadcast, MQTT, zero-hop com receptor conhecido, repetição, arquivo histórico, controles do mapa, cancelamento de pacote parcial e sintaxe PowerShell.

**Limitações:** esta versão NÃO encerra as dezenas de questões de backlog, nem certifica automaticamente compatibilidade de todas as rádios, autodetecção BLE, API LAN autenticada, tradução integral ou todos os hops dos pacotes. O mapa não liga nós móveis com coordenadas temporalmente incompatíveis. Testes reais Win11 x64 Setup/Portable necessários.

## v0.6.4 — 15/10/2026 — Menu VER, waypoints e ícone da janela

- **#20 — Mapa:** novo botão **Ver ▾** na barra secundária, com checkboxes **Nós**, **Enlaces**, **Waypoints**, **Animar tráfego**, contagens por escopo e comandos **Selecionar tudo**/**Remover tudo**. Estados compartilhados com Configurações → Mapa, aplicados imediatamente; clique externo/Escape fecha o menu.
- **#20 — WAYPOINT_APP:** parser de coordenadas Meshtastic fixas em 1e-7 grau, payload Protobuf nativo ou dicionário decodificado; persistência SQLite com origem/fonte/timestamp/validade/descrição; API local para objetos não expirados e camada Leaflet própria. Filtros de fonte, busca e janela temporal aplicáveis. Nenhum ponto fictício.
- **#42 — Mapa:** removido o texto redundante `Todas as conexões · N` e o seu espaço na faixa de controles. O filtro Conexão e contador operacional no resumo continuam presentes.
- **#40 — Windows:** pywebview recebe explicitamente o ICO nativo da marca PT2VHF via `webview.start(icon=...)`; PyInstaller empacota o ICO sob `branding` com `--add-data` nos dois scripts de build. Testes e verificação do asset no EXE.
- **Retenção:** opção independente de Waypoints, padrão Nunca; waypoints expirados deixam de ser mostrados sem apagar registros antecipadamente.
- **Qualidade:** novos testes de waypoints serializados como Protobuf, IDs, proveniência por conexão, timestamps, expiração, filtros de interface e build com ícone.

**Validação pendente:** testar fisicamente o ícone do taskbar/Alt+Tab, recepção de waypoints e comportamento do menu no WebView2, e demais issues do backlog que permanecem abertas. Esta release não marca como concluídas todas as 32+ issues.

## v0.6.3 — 14/10/2026 — Atualizador verificado e manutenção do banco

- **#34/#2/#15 (código):** atualização externa só é marcada como instalada após a nova instância iniciar, permanecer viva e responder `/health` com a versão esperada; a falha agora é persistida, pode ser exibida no popup e exige diagnóstico. Modo Portable guarda cópia anterior e pode fazer rollback quando o processo novo encerrou. **Não declarar resolução completa sem ensaio com Windows 11 físico.**
- **#33 (parcial):** tela de saúde SQLite, contagem de tabelas, páginas, WAL/SHM, retenções e disco; `quick_check` e `foreign_key_check` sob demanda; backup online verificado com `sqlite3.backup()` em pasta local, sem modificar retenções.
- **#35 (parcial):** nome amigável de nó editável localmente, guardado no SQLite, separado do Node ID e preservado na sincronização futura de NodeDB.
- **#30 (parcial):** LEDs TX/RX derivados de novos eventos observados no backend, sem confundir MQTT com RX do rádio ou TX aceito com RF comprovado.
- **#37 (correção):** popup somente após checar novidades da atualização, sem reabrir durante F5 na mesma sessão.
- **Testes offline:** diagnóstico e snapshot SQLite, preservação de alias, separação de eventos TX/RX, ordem do aviso do atualizador e rotas do aplicativo.

**Validação pendente:** atualização automática no Setup e Portable físicos; LED RX/TX e foco dos diálogos no WebView2; nenhuma garantia de paridade total com o Traffic Analyzer nem de conclusão das demais issues.

## v0.6.2 — 14/10/2026 — Conexões, primeira inicialização e cabeçalho

- **#37 — Primeira configuração:** quando `/api/state` retorna lista `sources` vazia, o aplicativo abre um diálogo central informando que é necessário cadastrar uma conexão Meshtastic. Os botões **Ir para conexões** e **Agora não** permitem respectivamente abrir `Configurações → Conexões` com foco no nome da nova conexão ou continuar sem cadastro. O aviso só aparece uma vez por carregamento, nunca apenas porque conexões cadastradas estão desconectadas; resposta inválida/falha de consulta não aciona o aviso.
- **#36 — Terminologia:** seção antes chamada Fontes passa a **Conexões**; campos, ajuda, filtros, CSV/relatório, indicadores e notificações exibem nomenclatura coerente, mantendo APIs, nomes de tabelas e IDs internos `source_id` compatíveis.
- **#21 — Cabeçalho:** marca aumentada (logo 58 px; título 22 px), versão com a mesma tipografia do título e subtítulos maiores; remoção do estado “N fonte(s) conectada(s)” da linha superior, preservando a contagem na faixa de indicadores. Menu reordenado: Mapa, Mensagens, Nós, Tráfego, Estatísticas, Automações, Configurações, Ajuda.
- **Navegação profunda:** URLs específicas `/configuracoes/conexoes`, `/configuracoes/dispositivo`, `/configuracoes/retencoes`, `/configuracoes/mapa`, `/configuracoes/sistema` e `/configuracoes/geral` permitem F5/favoritos. A API HTTP local serve corretamente essas rotas.
- **Teste adicional:** nova suíte de regressão verifica estado inicial sem conexões, fonte cadastrada porém desativada, rotas HTTP locais e contrato da interface; CI Windows valida Python, sintaxe JS, empacotamento e publicação.

**Limites de validação:** testes automatizados não equivalem à validação do fluxo de foco/teclado no WebView2 real; instalação Setup/Portable, conexão com rádio físico, atualização interna e itens antigos do backlog continuam sujeitos a ensaios no Windows 11. A v0.6.2 não declara resolvido todo o backlog.

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