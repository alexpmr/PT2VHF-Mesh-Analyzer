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