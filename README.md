# PT2VHF Mesh Analyzer — v0.6.21

**Projeto independente de MeshMonitor, por Alex, PT2VHF.** Aplicativo Windows 11 x64 com banco próprio SQLite, fontes Meshtastic e análises locais. A arquitetura também permite evolução para Linux/macOS.

## Downloads — Windows 11 x64

**Versão mais recente (publicada após aprovação do pipeline): [v0.6.21](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/tag/v0.6.21)**

| Download | Arquivo disponível | Link direto |
|---|---|---|
| **Instalador (recomendado)** | `PT2VHF-Mesh-Analyzer-v0.6.21-Setup-Win11-x64.exe` | **[Baixar instalador EXE](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.21/PT2VHF-Mesh-Analyzer-v0.6.21-Setup-Win11-x64.exe)** |
| **Versão portátil** | `PT2VHF-Mesh-Analyzer-v0.6.21-Portable-Win11-x64.exe` | **[Baixar Portable EXE](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.21/PT2VHF-Mesh-Analyzer-v0.6.21-Portable-Win11-x64.exe)** |
| **Verificação SHA256** | `SHA256SUMS.txt` | [Baixar hashes](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.21/SHA256SUMS.txt) |

**Atalhos para a última versão (atualizados automaticamente pelo GitHub):**
[Setup mais recente](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-Setup-Win11-x64.exe) ·
[Portable mais recente](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-Portable-Win11-x64.exe) ·
[SHA256 mais recente](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/SHA256SUMS.txt) ·
[Todas as releases](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases)

**Requisitos:** Windows 11 64 bits. O Setup instala o programa; o Portable EXE pode ser executado diretamente, sem instalação. O ZIP permanece disponível por compatibilidade. Para conferir a integridade, compare o SHA256 do arquivo baixado com o valor em `SHA256SUMS.txt` da mesma versão. O Windows pode apresentar o SmartScreen para programas sem assinatura digital.

### Novidades da v0.6.21

- Reinício com ambiente PyInstaller independente e espera pelo bootloader anterior; Setup mantém diretório atual e grava log próprio.
- Trechos RF identificados usam amarelo contínuo por padrão, com tipo/evidência no popup. Remove sobreposição de fluxo lógico duplicado, sem promover traceroutes ao ranking RF direto.
- Testes de JavaScript real e ciclo Windows de substituição/reinício de EXE onefile de teste. Hardware e WebView2 reais ainda requerem validação.
- **Instale manualmente esta versão.** O atualizador antigo continua sendo usado na passagem da v0.6.20 para a v0.6.21; o runner corrigido será usado a partir desta instalação.

## Política de downloads

Somente a release estável mais recente permanece disponível. Após publicar e verificar os arquivos da nova versão, o pipeline remove as releases antigas e seus downloads. Tags e histórico do código são preservados; não há reescrita do Git.

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