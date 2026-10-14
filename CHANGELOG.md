# Changelog — PT2VHF Mesh Analyzer

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