# PT2VHF Mesh Analyzer — v0.6.32

**Projeto independente de MeshMonitor, por Alex, PT2VHF.** Aplicativo para **Windows 10 versão 1809+ (x64)** e **Windows 11 (x64)**, com SQLite próprio, integração nativa Meshtastic (USB, BLE, TCP e MQTT) e análises locais.

## Downloads — Windows 10 / Windows 11 (64 bits)

**Versão mais recente (publicada após aprovação do pipeline): [v0.6.32](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/tag/v0.6.32)**

| Download | Nome do arquivo | Link |
|---|---|---|
| **Setup Windows 10/11** | `PT2VHF-Mesh-Analyzer-v0.6.32-Setup-Win10-Win11-x64.exe` | [Baixar instalador](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.32/PT2VHF-Mesh-Analyzer-v0.6.32-Setup-Win10-Win11-x64.exe) |
| **Portable Windows 10/11** | `PT2VHF-Mesh-Analyzer-v0.6.32-Portable-Win10-Win11-x64.exe` | [Baixar Portable](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.32/PT2VHF-Mesh-Analyzer-v0.6.32-Portable-Win10-Win11-x64.exe) |
| **Portable ZIP** | `PT2VHF-Mesh-Analyzer-v0.6.32-Portable-Win10-Win11-x64.zip` | [Baixar ZIP](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.32/PT2VHF-Mesh-Analyzer-v0.6.32-Portable-Win10-Win11-x64.zip) |
| **SHA256** | `SHA256SUMS.txt` | [Conferir hashes](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.32/SHA256SUMS.txt) |

**Links automáticos (última versão):**
[Setup Windows 10/11](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-Setup-Win10-Win11-x64.exe) ·
[Portable Windows 10/11](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-Portable-Win10-Win11-x64.exe) ·
[Hashes](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/SHA256SUMS.txt).

**Requisitos:** Windows 10 **1809/Build 17763 ou superior** ou Windows 11, **64 bits**; **Microsoft Edge WebView2 Runtime** instalado (o Setup não faz download automático desse runtime); recursos locais Bluetooth/serial dependem do driver e das permissões do sistema. O instalador é por usuário, sem elevação obrigatória. Os pacotes de atualização com nomes antigos `Win11-x64` permanecem na v0.6.32 exclusivamente para que versões anteriores consigam atualizar; apontam para o mesmo executável compatível Windows 10/11. O Windows pode apresentar SmartScreen, pois o executável ainda não tem assinatura digital.

### Novidades da v0.6.32 — Testes completos do atualizador Windows

- **Reinicialização (#103):** teste de ponta a ponta com PyInstaller real simulando launcher encerrando normalmente com código 0 antes de uma nova instância iniciar o servidor de saúde. Requer nonce correto, versão e `ui_ready` antes de declarar sucesso.
- **Autenticidade do processo:** a validação /health agora exige nonce não vazio e correspondente; não aceita uma aplicação antiga ou uma resposta sem identificação.
- **Diagnóstico verdadeiro:** quando a versão instalada já está em execução, mas a tentativa anterior não confirmou o reinício, a interface informa **“versão instalada; reinício automático não confirmado”** — nunca “falha na instalação” sem evidência. Preserva o relatório da tentativa anterior para investigação.
- **Regressões:** testes de relatórios de atualização com versões iguais/antigas, cancelamento de aviso, verificação da identidade do serviço e PowerShell/PyInstaller real no pipeline Windows.
- **Compatibilidade:** Setup e Portable Windows 10 (1809+) / 11 x64; sem apagar banco SQLite. Teste de atualização no computador real continua sendo obrigatório para encerrar #103.

### Novidades da v0.6.31 — Atualização automática e WebView2

- **Correção crítica de reinicialização (#103):** a ponte nativa de exportação PDF deixa de expor o objeto inteiro `webview.Window` como atributo público do `js_api`. Isso evita que o pywebview inspecione recursivamente objetos WinForms/WebView2, reproduzido nos logs da v0.6.30 (`maximum recursion depth exceeded` e `E_NOINTERFACE`).
- **Confirmação mais robusta:** o atualizador consulta `/health` autenticado por versão/nonce e `ui_ready` antes de interpretar o fim do processo inicial. Código 0 sozinho nunca significa sucesso nem falha da instalação.
- **Regressão automatizada:** a introspecção real do pywebview deve expor apenas `save_pdf`, sem percorrer a janela nativa; diálogo de salvamento PDF permanece testado.
- **Compatibilidade:** Windows 10 1809+ / Windows 11 x64, instalador e Portable; dados SQLite e preferências são preservados.
- **Validação de campo pendente:** confirmar atualização Setup/Portable na estação que apresentou a falha, sem popup após o aplicativo reabrir.

### Novidades da v0.6.30 — Mensagens e legenda compacta

- **Mapa (#119):** legenda recolhida por padrão em botão compacto no canto inferior esquerdo, expansível e acessível; ícones de nós, significado dos enlaces amarelos e diagnóstico técnico em painel secundário. Indicadores continuam sendo atualizados sem manter a legenda aberta.
- **Mensagens (#120):** o caractere `@` continua acionando sugestões, mas a seleção insere apenas o nome longo do nó com espaços, sem prefixo `@` nem underscores; fallback para nome curto/Node ID e verificação dos limites de bytes UTF-8.
- **Mensagens (#121):** campo “Pesquisar nó...” acima dos contatos, filtro incremental por nome longo/curto/amigável, aliases e Node ID, ignorando acentos/maiúsculas. Inclui nós offline e sem conversa anterior; canais continuam acessíveis, busca local sem tráfego RF e botão limpar.
- **Regressão (#118 e #57):** mantidos o indicador verde de versão atualizada e os estados/checks das mensagens; testes JavaScript e suite Windows devem validar.
- **Escopo:** outras issues permanecem abertas para teste de equipamento, implantação e trabalho adicional. A publicação não significa resolução integral de todas as issues históricas.

### Novidades da v0.6.29

- Atualizador Portable: reinício direto com ambiente isolado do runtime PyInstaller anterior; preserva pasta de dados e porta personalizadas.
- Confirmação pela versão, identificação da tentativa e interface pronta; diagnóstico distingue HTTP indisponível de interface ainda não pronta. Avisos de falha mostram data e versão atualmente executada.
- Pipeline testa o EXE Portable real, com nome versionado, caminho com espaços, ambiente _MEI inválido, perfil persistido e confirmação de prontidão pela API. Este teste usa modo headless e não substitui aceite visual no computador afetado.
- Para obter o novo atualizador, instale esta versão manualmente: uma tentativa iniciada por versão antiga ainda usa o atualizador antigo. O próximo ciclo automático precisa de validação em campo (#103).

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

## Instalação Windows 10/11 — código-fonte (disponível neste ZIP)

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

## Limitações conhecidas

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