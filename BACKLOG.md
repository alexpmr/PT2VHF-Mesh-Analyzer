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

## Solicitações de backlog ainda não encerradas

As melhorias abaixo são **itens de backlog**, não funcionalidades já entregues. O detalhamento e os testes de aceite estão nas respectivas issues:

1. [**#1 — Idiomas na barra superior**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/1): PT-BR (padrão), EN, ES, FR, DE e IT; tradução completa de interface, notificações e atualizador, persistência e troca sem reinício.
2. [**#2 — Atualização interna (parcial)**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/2): verificação de GitHub Releases **a cada 15 minutos por padrão**, período configurável em Configurações, consulta manual, changelog, download verificado por SHA256 e instalação autorizada sem perder o banco.
3. [**#3 — Acesso Web pela LAN**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/3): **desligado por padrão**, acesso local via aplicativo; habilitação explícita com autenticação, senha, proteção das APIs/mensagens, endereço IP/porta e opção de desligar sem afetar localhost.
4. [**#4 — Mensagens com visual de mensageiro**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/4): conversas/canais, balões RX/TX, horários, dias, não lidas, notificações, campo inferior, status de envio/ACK sem alegar leitura remota.
5. [**#5 — Menções de nós usando `@`**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/5): filtro incremental a cada caractere por nome curto/longo, personalizado, aliases e Node ID; inserir referência legível; teclado/mouse; suporte a vários `@`; mensagem transmitida como texto interoperável (não equivale a DM nem notificação nativa universal).
6. [**#6 — Configuração completa do rádio com backup/restore (parcial)**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/6): ler todos os campos **suportados pelo firmware/hardware** (LoRa, canais, dispositivo, posição, energia, BLE, rede, módulos, segurança), editar em uma única interface e **Aplicar tudo** com comparação, validação, envio sequencial, acompanhamento de ACK/readback e reinício quando necessário. Backup versionado, exportação de segredos protegida e restauração seletiva com validação de compatibilidade e backup prévio. **O envio não é uma transação RF atômica**.

7. **Downloads na página principal do GitHub**: implementado no README e no pipeline da v0.1.1; confirmar funcionamento real após release.

## Novas solicitações de interface — 14/10/2026 (pendentes)

Referência visual/funcional: **[PT2VHF Traffic Analyzer](https://github.com/alexpmr/traffic-analyzer)**. Reaproveitar experiência de navegação e regras analíticas, **não** a API/servidor do MeshMonitor. Os exemplos visuais foram enviados na conversa do projeto.

- [**#8 — Aba Nós, tabela analítica**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/8): replicar cabeçalho compacto, total de nós, referência de distância, busca, limpar, Colunas e Atualizar; mostrar Nome longo, Nome curto, Role, Hardware, Saltos, Bateria, Tensão, Distância, SNR, Última interação, Última posição. Campos opcionais quando existentes; ordenação/filtros persistentes, última interação distinta da posição e nós antigos jamais forçados a online por NodeDB importado.
- [**#9 — Aba Tráfego, histórico avançado**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/9): tabela conforme referência, busca, filtros de período/origem/destino/canal/tipo/fonte, ordenação, colunas personalizáveis, detalhes de pacote, distinção RF vs MQTT, dados de SNR/RSSI/hops/ACK quando realmente presentes, respeito à privacidade e desempenho com grande histórico.
- [**#10 — Estatísticas: paridade funcional integral com o Traffic Analyzer v1.62.1 NO PT2VHF Mesh Analyzer**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/10): migrar todas as **11 subabas**, cards de KPIs, resumo automático, filtros globais de período/nó/fonte, gráficos, tabelas, rankings RF interativos, pontos de atenção, auditoria, **Relatório/PDF e CSV**, URLs individuais, drill-down e cálculos auditáveis baseados exclusivamente no SQLite próprio e nas fontes Meshtastic. O Traffic Analyzer é somente a referência; não modificar nem depender do MM.
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
  - Vinculada à [**#10 — Estatísticas completas**](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/issues/10). O relatório é uma funcionalidade **pendente**, não uma nova release.

**Situação:** issues de Nós, Tráfego, Estatísticas e Mapa registradas; pendentes de implementação na aplicação.

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