# PT2VHF Mesh Analyzer — v0.6.9

**Projeto independente de MeshMonitor, por Alex, PT2VHF.** Aplicativo Windows 11 x64 com banco próprio SQLite, fontes Meshtastic e análises locais. A arquitetura também permite evolução para Linux/macOS.

## Downloads — Windows 11 x64

**Versão mais recente (publicada após aprovação do pipeline): [v0.6.9](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/tag/v0.6.9)**

| Download | Arquivo disponível | Link direto |
|---|---|---|
| **Instalador (recomendado)** | `PT2VHF-Mesh-Analyzer-v0.6.9-Setup-Win11-x64.exe` | **[Baixar instalador EXE](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.9/PT2VHF-Mesh-Analyzer-v0.6.9-Setup-Win11-x64.exe)** |
| **Versão portátil** | `PT2VHF-Mesh-Analyzer-v0.6.9-Portable-Win11-x64.zip` | **[Baixar Portable ZIP](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.9/PT2VHF-Mesh-Analyzer-v0.6.9-Portable-Win11-x64.zip)** |
| **Verificação SHA256** | `SHA256SUMS.txt` | [Baixar hashes](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.9/SHA256SUMS.txt) |

**Atalhos para a última versão (atualizados automaticamente pelo GitHub):**
[Setup mais recente](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-Setup-Win11-x64.exe) ·
[Portable mais recente](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-Portable-Win11-x64.zip) ·
[SHA256 mais recente](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/SHA256SUMS.txt) ·
[Todas as releases](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases)

**Requisitos:** Windows 11 64 bits. O Setup instala o programa; o Portable pode ser extraído e executado sem instalação. Para conferir a integridade, compare o SHA256 do arquivo baixado com o valor em `SHA256SUMS.txt` da mesma versão. O Windows pode apresentar o SmartScreen para programas sem assinatura digital.

### Novidades da v0.6.9

- **Atualização #34 (correção no código):** o atualizador confirma que o processo da nova versão permanece vivo e responde com a versão pretendida e `ui_ready=true` em `/health` antes de escrever um aviso de sucesso; falhas ficam registradas em `update.log` e `update_complete.json`. No Portable, pode restaurar o executável anterior se o novo processo já terminou. **Ainda exige teste real Setup → Setup e Portable → Portable em Windows 11, portanto não há garantia de correção em campo.**
- **Banco SQLite #33 (parcial):** Configurações → Sistema mostra contagens, arquivos WAL/SHM, espaço, páginas, retenções e último backup. `quick_check`/integridade referencial por ação explícita, e backup consistente via API nativa `sqlite3.backup` sem alterar retenção ou apagar histórico. Prévia de limpeza, restauração e maintenance avançada continuam pendentes.
- **Nomes amigáveis #35 (parcial):** botão **Renomear** no detalhe do nó armazena apelido local por Node ID no SQLite. O nome é priorizado em identificações que usam `idName`, sem substituir a identidade rádio nem dados de NodeInfo. Auditoria de todos os cartões e tabelas ainda pendente.
- **LEDs de tráfego #30 (parcial):** TX vermelho ao aceitar envio via interface; RX verde em novo pacote de rádio USB/BLE/TCP (sem incluir MQTT). Contadores de evento por conexão, baseline sem pulsos durante carregamento de histórico e intervalo de polling local de 650 ms; requer medição física de precisão e desempenho. TX aceito **não** comprova RF irradiado.
- **Primeiro acesso #37 (correção):** guarda de sessão impede repetição no F5, com apresentação sequencial após avaliação das novidades da release. Conferir em WebView2 no Windows real.
- **Testes novos:** backup WAL, integridade SQLite, nomes locais preservados por NodeDB, sequência RX/TX e ordem lógica de sucesso do atualizador. Pipeline Windows verifica Python, JavaScript, PyInstaller e Inno Setup.

**Escopo: esta é uma release de estabilização e evolução parcial do backlog; NÃO marca como encerradas todas as 30 issues, especialmente #31, #29, #6, #3, #1 e #10.**

### Novidades da v0.6.2

- **Primeira execução:** sem nenhuma conexão cadastrada, aparece “Configure sua primeira conexão”. **Ir para conexões** abre o formulário em Configurações → Conexões; **Agora não** permite explorar. Não aparece apenas porque um rádio cadastrado está offline/desativado.
- **Conexões:** aba, campos, filtros e mensagens da interface usam o novo nome, mantendo a compatibilidade do banco e APIs internas `sources`.
- **Identidade visual:** logotipo e bloco PT2VHF maiores, número da versão tão destacado quanto o título e retirada da contagem de conexões da primeira linha (a contagem permanece nos KPIs).
- **Menu:** Mapa | Mensagens | Nós | Tráfego | Estatísticas | Automações | Configurações | Ajuda.
- **Endereços dedicados:** cada subaba de Configurações tem URL própria, começando por `/configuracoes/conexoes` na interface local; o caminho pode ser usado em favoritos e preservado após atualizar a página.
- **Validação:** suíte Python e sintaxe JS pelo pipeline, com publicação automática dos executáveis Win11 x64. A execução e compatibilidade física de rádio/atualizador ainda precisam de teste em Windows 11.

### Identidade visual — v0.6.1

- Logotipo do **PT2VHF Mesh Analyzer**: antena e ondas de rádio sobre a serra, conectadas por três nós de uma rede mesh. Verde de marca (`#59e97e`), azul-esverdeado da interface escura e amarelo reservado às evidências/realces RF.
- A mesma arte aparece no **cabeçalho do aplicativo**, favicon da interface web local, **ícone real do EXE (Setup e Portable)**, **ícone do instalador**, **atalhos da Área de Trabalho/Menu Iniciar** e **janela/Barra de tarefas do Windows** quando empacotada.
- O processo WebView2 e os atalhos Windows compartilham o AppUserModelID `PT2VHF.MeshAnalyzer`. O ICO multirresolução é gerado por `python branding/build_icons.py` da imagem matriz versionada e verificada por SHA256.
- Se um atalho antigo fixado na barra de tarefas ainda mostrar o ícone anterior, desfixe-o e fixe novamente a aplicação atualizada; o cache do Explorer também pode exigir renovação.
- **Esta release não resolve integralmente os itens de UI/rádio/atualizador ainda abertos no backlog.** Nenhuma configuração de rádio ou banco SQLite é alterada pela marca.

### Novidades da v0.6.0

- **Atualização direta dentro do Mesh Analyzer (Windows 11):** a partir da v0.6.0, clique no indicador de nova versão, veja changelog, confirme e acompanhe download e SHA256. O aplicativo fecha fontes/SQLite e um processo externo instala e reinicia, apresentando as novidades uma vez. **A atualização real com Setup e Portable ainda requer teste de bancada.** Para vir da v0.4.0 é necessário baixar esta versão uma vez.
- **Configurações → Mapa:** filtros de janela e número de observações, mapa-base, brilho, cores e espessuras de RF/MQTT, mostrar linhas/nós, mapa de calor de pacotes observados, nomes, relevo, Auto Zoom em novos traceroutes, temas sonoros e animação com velocidade/duração. A barra do Mapa deixou de mostrar controles históricos inoperantes e seleção de velocidade/mapa-base.
- **Estatísticas:** apenas 10 subabas; *Acessos* removida. Visão Geral redesenhada em 8 cartões com resumo automático em faixa amarela. Outras subabas ampliadas, mantendo precisão das observações e sem inventar TX/CRC ou RF direto.
- **Integridade:** base de dados preservada no perfil do usuário. Em caso de falha, o atualizador grava `update.log` e permite instalação manual.

**Pendente:** paridade total com todos os painéis e métricas do Traffic Analyzer v1.62.1; validação do atualizador, WebView2 e dispositivos físicos em Windows 11.

### Recursos acumulados até a v0.6.0

- **Estatísticas (10 subabas)**: Visão Geral, Rede, RF, Ranking, Routing, Tráfego, Consultas, Chat, Energia, Pontos de atenção. Dados do SQLite próprio, filtros por período, fonte e nó, evolução horária, tabelas e médias RF quando medidas.
- **Relatório técnico PDF nativo e offline**: capítulos com inventário, fontes, tráfego, RX/RSSI/SNR, telemetria LocalStats quando disponível, relações observadas, diagnóstico de possíveis interferências/colisões, hipóteses e ações técnicas. Não necessita Home Assistant nem MeshMonitor.
- **Dados RF auditáveis**: `num_packets_rx_bad` de LocalStats indica RX inválido, **não** contador CRC específico. Outro LoRa na faixa, piso de ruído e colisões não são comprovados sem instrumentação adicional; o relatório marca explicitamente o que não pode medir.
- **Nós**: 11 colunas iniciais, busca, ordenação, ocultação de colunas, idade da última observação/posição e referência de distância automática no rádio local conectado. Hops sem evidência não são exibidos como zero.
- **Tráfego**: filtro por fonte/tipo, detalhes dos pacotes, pausa da tabela e CSV visível.
- **Mensagens**: autocomplete incremental de nós ao digitar `@`, inserindo nome/identificador como texto comum interoperável; **não é um DM nativo nem garante alerta remoto**.
- **Mapa**: base OSM, topográfico, satélite, claro e escuro; radar meteorológico, hillshade e relevo com corte (DEM), slider e opacidades. Pulsos animados em nós observados, sem desenhar uma rota RF não comprovada.
- **Preservação**: migração incremental do SQLite sem remover posições e tráfego históricos. Setup e Portable do GitHub são buildados por CI Windows.

**Não confundir “11 subabas existentes” com paridade integral de indicadores do legado:** vários painéis avançados exibem indisponibilidade quando não há evidência suficiente, como rankings RF diretos, taxa de CRC de hardware, espectro, confirmação de entrega e sessões web autenticadas.

### O que muda na v0.6.0

- **Interface desktop WebView2** abre no Windows 11 sem navegador externo por padrão.
- **Configurações → Sistema**: escolher abertura de navegador adicional e frequência de verificações (15 min padrão); acesso Web LAN continua desabilitado enquanto não houver autenticação.
- **Indicador de versão no topo**, com verificação automática e clique para nova consulta ou visualização da release disponível.
- **Configurações → Dispositivo**: seleção de rádio conectado Serial/USB, BLE ou Wi-Fi/TCP/IP, leitura dos grupos do cache Meshtastic, alteração de parâmetros escalares não sensíveis e botão único para enviar alterações de vários grupos. Não há confirmação universal de gravação persistente.
- **Instalação**: WebView encerra backend e conexões quando a janela fecha; Inno Setup solicita encerramento de aplicações em uso. Validação do atualizador automático completo ainda pendente.

**Requisito:** Windows 11 x64 com Microsoft Edge WebView2 Runtime; sem runtime a interface não abre automaticamente em navegador. A v0.6.0 não implementa LAN autenticada, alteração de canais/PSKs ou atualização instalável automática.

### Novidades da v0.6.0

- **Correção dos enlaces**: identificadores oficiais de pacotes Meshtastic, interpretação de traceroutes/NeighborInfo recebidos, evidência por fonte e reprocessamento de histórico salvo. Contadores distinguem relações gravadas, visíveis e sem posição. Rotas observadas **não são automaticamente enlaces RF diretos**.
- **Mapa → Fonte**: Todas as fontes (padrão) ou filtro específico USB/Serial, BLE, Wi-Fi/TCP ou MQTT. A seleção não modifica o rádio de transmissão.
- **Aba Nós**: distância geodésica usando automaticamente o **rádio local conectado** com localização conhecida; nenhuma seleção manual de nó de referência. Havendo vários rádios ativos e nenhuma fonte selecionada, exibe indisponibilidade.
- **Menu principal**: segunda linha abaixo do título, sem perder o indicador de versão.
- **Migração de dados**: SQLite evolui de forma não destrutiva, preservando histórico e evidência de fontes.

**Diagnóstico:** estar sem linha no mapa pode significar não ter rota decodificada, não ter posições dos dois nós ou ter aplicado filtros. O aplicativo explicita essas situações. Nem todo pacote LoRa permite determinar os saltos RF percorridos.

## O que esta versão entrega

- Interface no estilo do **PT2VHF Traffic Analyzer**, com abas **Mapa, Nós, Tráfego, Mensagens, Estatísticas, Automações, Configurações e Ajuda**. O cabeçalho, a barra compacta e a pesquisa incremental são inspirados na v1.62.1.
- **Configurações → LoRa**: leitura das configurações de um rádio conectado e edição conservadora de parâmetros LoRa com revisão/confirmação. Visualização de outras seções com segredos ocultos. Backup JSON sem segredos; restauração e edição geral ainda não implementadas.
- **Atualização**: consulta à última release no GitHub a cada 15 minutos por padrão, configurável entre 5 e 1440 minutos no navegador; instalação/download permanecem manuais.
- **Configurações → Fontes**: cadastro ilimitado de fontes independentes **USB/Serial (COM), Wi-Fi/TCP/IP (porta 4403), Bluetooth LE e MQTT**, com nome, tipo, dados de conexão, habilitar/desabilitar, alterar e excluir. Fontes rádio permitem RX e TX; MQTT é **somente RX** nesta versão.
- **Banco de dados próprio SQLite**. Pacotes, nós, posições, mensagens e rotas são registrados localmente por fonte, sem chamada à API do MeshMonitor.
- **Configurações → Retenções**: prazo separado para **nós, pacotes/tráfego, mensagens, posições, traceroutes, enlaces e logs**. Padrão de todas: **Nunca apagar**. Limpeza periódica (a cada hora) ou imediata mediante confirmação.
- **Mensagens privadas** e mensagens para canais Meshtastic com seleção de fonte TX; a aceitação pelo rádio **não é prova de entrega nem confirmação de leitura**.
- Mapa com múltiplos provedores, radar/hillshade/corte de altitude e nós de posição conhecida, busca por nome curto, longo, Node ID e aliases historicamente registrados. **Rotas observadas não são automaticamente classificadas como enlace RF direto.**
- Releitura de fontes persistentes e tentativa de reconexão; indicadores por fonte e contagem RX na sessão.
- Interface web escutando **apenas em 127.0.0.1** por segurança; escrita protegida por token CSRF, sem credenciais na resposta de API; banco no perfil do usuário.

## Instalação Windows 11 — código-fonte (disponível neste ZIP)

1. Instale **Python 3.12** (64 bits), incluindo `py` no sistema.
2. Extraia este pacote em uma pasta de sua preferência.
3. Dê dois cliques em **`Iniciar_Windows_11.bat`**. Na primeira execução ele cria `.venv` e instala as bibliotecas necessárias (requer internet). Depois abre a interface no navegador.
4. Abra **Configurações → Fontes**, cadastre o dispositivo por COM, IP, BLE ou MQTT e habilite a conexão.
5. Se o navegador não abrir automaticamente, visite **http://127.0.0.1:8789** enquanto a aplicação estiver rodando.

Para iniciar no terminal após instalar:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m mesh_analyzer
```

### EXE portátil e instalador

Este pacote inclui os projetos de build para **gerar EXE Windows 11 e Setup (Inno Setup)**. Em um Windows com Python:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

O GitHub Actions de `.github/workflows/windows.yml` compila o EXE, o ZIP portátil, o Setup e hashes SHA256 em **Windows Server 2022** e publica os artefatos ao incorporar uma nova versão na branch `main`. As releases incluem tanto os arquivos versionados quanto os nomes estáveis usados pelos atalhos da última versão.

**Atenção:** um ZIP de código-fonte não é um EXE compilado. O teste de CI não equivale a validação em rádio físico.

## Onde ficam os dados

- Windows: `%LOCALAPPDATA%\PT2VHF-Mesh-Analyzer\mesh-analyzer.sqlite3`.
- Linux/macOS (para desenvolvimento): `$XDG_DATA_HOME/PT2VHF-Mesh-Analyzer` ou `~/.local/share/PT2VHF-Mesh-Analyzer`.
- Variável opcional de teste: `PT2VHF_MESH_DATA`.
- Nunca coloque o SQLite, arquivo `.env` ou credenciais no repositório. Senhas MQTT são gravadas localmente no SQLite; **não há criptografia de credenciais em repouso na v0.6.0**. Evite computadores compartilhados e restrinja as permissões ao usuário do sistema.

## Limites honestos da v0.6.0

- O **visual e as abas** foram recriados a partir do padrão Traffic Analyzer; a v0.6.0 **não é uma cópia funcional completa** da v1.62.1. Funcionalidades de dashboard avançado ainda não implementadas em paridade, bots PING/CLIMA, integrações geográficas/APRS, rankings RF diretos comprovados, consulta ativa NodeInfo e cobertura especializada permanecem pendentes.
- **Hardware físico ainda não foi testado.** USB e TCP utilizam interfaces oficiais Meshtastic Python. BLE requer identificador apropriado e suporte da plataforma/firmware; conectar diversos BLE simultâneos pode depender do hardware e do SO. MQTT armazena envelopes Meshtastic; payloads criptografados sem chaves conhecidas não são decodificados, e MQTT **não transmite** RF.
- O radio Meshtastic deve usar firmware compatível e **a mesma porta não deve ser ocupada por outro cliente**. Fontes múltiplas podem escutar rádios distintos; transmissões acontecem somente na fonte escolhida.
- Para ser confiável, um enlace direto RF necessita evidência por hop, não apenas um registro de traceroute. Na v0.6.0, o mapa diferencia rotas observadas de RF confirmado.
- A interface usa Leaflet e mapas-base online; **recepção e banco independem da internet**, mas a cartografia requer acesso à internet e pode ficar vazia offline.
- A interface HTTP da v0.6.0 é apenas localhost. Acesso remoto exigirá autenticação/TLS antes de permitir publicação na rede.
- O gerenciamento LoRa confirma apenas que o comando foi aceito pela API local, não o readback persistente do rádio. Campos de segurança e PSK não são editáveis nesta tela.
- O tratamento de ACK/retransmissões e estados detalhados de entrega será ampliado. Estado inicial `accepted_by_radio` **não significa entregue nem lido**.

## Verificação offline

```shell
python -m unittest discover -s tests -v
```

## Projeto anterior

Traffic Analyzer v1.x permanece separado: https://github.com/alexpmr/traffic-analyzer. Nenhum arquivo de instalação, configuração ou banco do Traffic Analyzer é sobrescrito pelo Mesh Analyzer.