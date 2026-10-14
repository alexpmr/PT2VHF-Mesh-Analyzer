# Changelog — PT2VHF Mesh Analyzer

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