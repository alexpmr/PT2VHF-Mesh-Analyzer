# PT2VHF Mesh Analyzer — v0.6.54

**Projeto independente de MeshMonitor, por Alex, PT2VHF.** Aplicativo para **Windows 10 versão 1809+ / Windows 11 (x64)**, **Linux (x64)** e **macOS (Apple Silicon e Intel)**, com SQLite próprio, integração nativa Meshtastic (USB, BLE, TCP e MQTT) e análises locais.

## Downloads

**Versão mais recente (publicada após aprovação do pipeline): [v0.6.54](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/tag/v0.6.54)**

### Windows 10 / Windows 11 (64 bits)

| Download | Nome do arquivo | Link |
|---|---|---|
| **Setup Windows 10/11** | `PT2VHF-Mesh-Analyzer-v0.6.54-Setup-Win10-Win11-x64.exe` | [Baixar instalador](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.54/PT2VHF-Mesh-Analyzer-v0.6.54-Setup-Win10-Win11-x64.exe) |
| **Portable Windows 10/11** | `PT2VHF-Mesh-Analyzer-v0.6.54-Portable-Win10-Win11-x64.exe` | [Baixar Portable](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.54/PT2VHF-Mesh-Analyzer-v0.6.54-Portable-Win10-Win11-x64.exe) |
| **Portable ZIP** | `PT2VHF-Mesh-Analyzer-v0.6.54-Portable-Win10-Win11-x64.zip` | [Baixar ZIP](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.54/PT2VHF-Mesh-Analyzer-v0.6.54-Portable-Win10-Win11-x64.zip) |

### macOS

| Download | Nome do arquivo | Link |
|---|---|---|
| **macOS Apple Silicon (M1/M2/M3/M4)** | `PT2VHF-Mesh-Analyzer-v0.6.54-macOS-arm64.dmg` | [Baixar DMG](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.54/PT2VHF-Mesh-Analyzer-v0.6.54-macOS-arm64.dmg) |
| **macOS Intel** | `PT2VHF-Mesh-Analyzer-v0.6.54-macOS-x64.dmg` | [Baixar DMG](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.54/PT2VHF-Mesh-Analyzer-v0.6.54-macOS-x64.dmg) |

### Linux

| Download | Nome do arquivo | Link |
|---|---|---|
| **Ubuntu / Linux Mint (.deb)** | `PT2VHF-Mesh-Analyzer-v0.6.54-amd64.deb` | [Baixar .deb](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.54/PT2VHF-Mesh-Analyzer-v0.6.54-amd64.deb) |
| **Linux x64 (outras distribuições)** | `PT2VHF-Mesh-Analyzer-v0.6.54-Linux-x64.tar.gz` | [Baixar TAR.GZ](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.54/PT2VHF-Mesh-Analyzer-v0.6.54-Linux-x64.tar.gz) |

### Container (servidor, NAS e Raspberry Pi)

Imagem `ghcr.io/alexpmr/pt2vhf-mesh-analyzer` para **amd64** e **arm64** (Raspberry Pi 4/5), atualizada a cada release:

```bash
docker run -d --name pt2vhf-mesh-analyzer --restart unless-stopped \
  -p 127.0.0.1:8789:8789 -v mesh-data:/data \
  ghcr.io/alexpmr/pt2vhf-mesh-analyzer:latest
```

Abra `http://localhost:8789` no próprio servidor. Rádio USB em servidor Linux: acrescente `--device /dev/ttyUSB0 --group-add dialout`. Exemplo completo em [`container/docker-compose.yml`](container/docker-compose.yml). Wi-Fi/TCP e MQTT funcionam sem restrição; Bluetooth e acesso por outros computadores da rede ainda não são suportados no container (acesso remoto por túnel SSH: `ssh -L 8789:127.0.0.1:8789 usuario@servidor`). Para atualizar: `docker pull ghcr.io/alexpmr/pt2vhf-mesh-analyzer:latest` e recrie o container; o volume `/data` preserva banco e configurações.

| Verificação | Arquivo | Link |
|---|---|---|
| **SHA256 (todas as plataformas)** | `SHA256SUMS.txt` | [Conferir hashes](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/download/v0.6.54/SHA256SUMS.txt) |

**Links automáticos (última versão):**
[Setup Windows 10/11](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-Setup-Win10-Win11-x64.exe) ·
[Portable Windows 10/11](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-Portable-Win10-Win11-x64.exe) ·
[macOS Apple Silicon](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-macOS-arm64.dmg) ·
[macOS Intel](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-macOS-x64.dmg) ·
[Ubuntu/Mint .deb](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-amd64.deb) ·
[Linux x64](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/PT2VHF-Mesh-Analyzer-Linux-x64.tar.gz) ·
[Hashes](https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest/download/SHA256SUMS.txt).

**Requisitos Windows:** Windows 10 **1809/Build 17763 ou superior** ou Windows 11, **64 bits**; **Microsoft Edge WebView2 Runtime** instalado (o Setup não faz download automático desse runtime); recursos locais Bluetooth/serial dependem do driver e das permissões do sistema. O instalador é por usuário, sem elevação obrigatória. Os pacotes de atualização com nomes antigos `Win11-x64` permanecem na v0.6.54 exclusivamente para que versões anteriores consigam atualizar; apontam para o mesmo executável compatível Windows 10/11. O Windows pode apresentar SmartScreen, pois o executável ainda não tem assinatura digital.

**Requisitos macOS:** macOS 13 Ventura ou superior. Abra o DMG e arraste **PT2VHF Mesh Analyzer** para **Aplicativos**. O app não é assinado/notarizado pela Apple: na primeira abertura, clique com o botão direito → **Abrir** (ou em Ajustes do Sistema → Privacidade e Segurança → **Abrir Mesmo Assim**). O macOS pede permissão de Bluetooth na primeira conexão BLE.

**Requisitos Linux:** distribuição 64 bits com glibc 2.35+ (Ubuntu 22.04, Linux Mint 21, Debian 12, Fedora 36 ou mais novos) e um navegador. **Ubuntu / Linux Mint:** dê dois cliques no `.deb` ou use `sudo apt install ./PT2VHF-Mesh-Analyzer-v0.6.54-amd64.deb`; o atalho aparece no menu e o comando `pt2vhf-mesh-analyzer` fica disponível. Remover o pacote preserva seus dados. **Outras distribuições:** extraia o `.tar.gz` e execute `./PT2VHF-Mesh-Analyzer` (a interface abre no navegador padrão) ou `./instalar.sh` para criar o atalho no menu de aplicativos. Para rádio USB, o usuário deve pertencer ao grupo `dialout`.

**Atualização:** no Windows, a atualização é feita pelo próprio aplicativo. No macOS e no Linux, o aplicativo avisa quando houver versão nova e o botão abre a página da release para baixar o pacote (no `.deb`, instale o novo por cima). No container, atualize a imagem.

### Novidades da v0.6.54

- **Cores por tipo de conexão:** a barra do rádio no topo muda de cor conforme a conexão: **verde** para USB, **azul** para Bluetooth, **laranja** para Wi-Fi e **violeta** para MQTT. As cores aparecem também nos pontos do menu do rádio, nos temas escuro e claro.

### Novidades da v0.6.53

- **Bluetooth no Windows (#191):** o app passa a conectar como o Chrome (cliente web oficial): primeiro abre a sessão Bluetooth com o rádio e **espera a ligação ficar ativa**, e só então lê os serviços. Antes, a leitura era pedida antes de existir ligação. Com alguns adaptadores, como o Realtek Bluetooth 4.2 USB, o Windows recusava em milissegundos, enquanto o cliente web conectava no mesmo PC.

### Novidades da v0.6.52

- **Bluetooth (#191):** quando o Windows recusa a conexão em milissegundos, sem chegar a falar com o rádio, a mensagem diz isso. O log registra a duração de cada tentativa e do pareamento.
- **Correções:**
  - "Últimas leituras" da coleta MeshCore, em Automações, dava erro ao abrir.
  - O diagnóstico (.zip) mostra as versões das bibliotecas também no app instalado.

### Novidades da v0.6.51

- **Diagnóstico para suporte (#198):** nova aba **Configurações → Diagnóstico**, com o botão **Baixar diagnóstico (.zip)**. O arquivo é gerado na hora, fica só no computador e serve para mandar ao suporte.
  - **Vai no arquivo:** versões, conexões e seus estados; Bluetooth (modelo do adaptador, rádios vistos com sinal, pareamento no sistema, últimas tentativas); portas USB; eventos dos últimos 7 dias e log da execução; configurações; números do banco.
  - **Não vai:** texto de mensagens, posições dos nós, senhas, PIN, chaves de canal e credenciais MQTT.
  - **Registro detalhado:** a opção liga, por 10 minutos, o log detalhado de Bluetooth e conexão (bleak e meshtastic). Use assim: liga a opção, repete a tentativa que falha e baixa o diagnóstico.
  - **Atalho:** quando um rádio Bluetooth falha no "Adicionar automaticamente", o resultado ganha o botão **Baixar diagnóstico para o suporte (.zip)**.

### Novidades da v0.6.50

- **Bluetooth (#191):** o app volta a **parear antes de conectar** os rádios Bluetooth que ainda não estão pareados.
  - No teste de campo, parear primeiro funcionava (v0.6.46); com a ordem invertida (v0.6.47–0.6.49), o Windows passou a recusar o pareamento depois de uma tentativa de conexão frustrada.
  - A conexão continua com o prazo maior e a segunda tentativa da v0.6.47.
  - Pareamentos nunca são removidos nem desfeitos.
- **Nome do rádio:** o resultado do "Adicionar automaticamente" mostra o nome anunciado pelo rádio junto do endereço, por exemplo **Meshtastic_8cdd** (10:20:BA:6A:8C:DD).
- **Adaptador Bluetooth:** a tela mostra o **modelo** do adaptador, lido do Gerenciador de Dispositivos (ex.: "Intel(R) Wireless Bluetooth(R)"), além do nome Bluetooth do computador.

### Novidades da v0.6.49

- **Uma conexão de cada vez (#189/#194):** com uma conexão escolhida em **Mostrar dados de**, tudo passa a ser só dela, mesmo com outras conectadas.
  - A barra superior mostra apenas essa conexão ("Platorm · MQTT"), sem o rádio USB entre parênteses. O rádio que transmite aparece ao passar o mouse e no menu.
  - Os contadores do topo (nós, pacotes, mensagens, relações) e as luzes TX/RX seguem a conexão escolhida.
  - O botão **✕** ao lado volta para todas as conexões.
- **Bluetooth (#191):**
  - O resultado do **Informar PIN…** aparece na própria linha do "Adicionar automaticamente": pareando, conectando, adicionado ou o motivo da falha, com **Tentar outro PIN…**.
  - Quando o Bluetooth falha, a tela mostra o adaptador Bluetooth do computador (nome, suporte a BLE e a conexão com dispositivos BLE).
  - Se o Windows não conseguir abrir conexão com nenhum rádio, nem para parear, a tela explica que a causa costuma ser o adaptador ou o driver, e sugere testar no **client.meshtastic.org**.
  - O app não remove mais pareamentos que já existiam no Windows.

### Novidades da v0.6.48

- **Barra superior (#194):** com uma conexão escolhida em **Mostrar dados de**, a barra superior passa a mostrar essa conexão, por exemplo "Platorm · MQTT (TX: PT2VHF-4 - Móvel)", com cor própria. O botão **✕ Todas as conexões**, ao lado, volta à visão completa. Na v0.6.47 o selo ficava fora da área visível do cabeçalho.
- **PIN no "Adicionar automaticamente" (#191):** rádios Bluetooth sem resposta ganham o botão **Informar PIN…**, que pareia com o código, verifica e cadastra o rádio. Rádios Meshtastic no modo Bluetooth padrão pedem PIN mesmo sem você ter definido um: ele aparece na tela do rádio (123456 nos rádios sem tela), e o celular só pede na primeira vez.

### Novidades da v0.6.47

- **Bluetooth (#191):** rádios Meshtastic que conectavam no celular falhavam no Windows com `TimeoutError` ou "Could not get GATT services: Unreachable".
  - A conexão agora procura o rádio uma vez, dá mais tempo para abrir a conexão e ler os serviços (20 s em vez de 10 s) e tenta uma segunda vez, lendo os serviços direto do rádio.
  - Antes de aceitar, confirma que consegue ler os dados do rádio.
  - O app conecta primeiro **sem parear**, como o celular. Só mexe no pareamento se precisar: pareia sem PIN o rádio que exige, pede o PIN quando o rádio pede, e remove um pareamento do Windows que esteja atrapalhando. Um pareamento criado pelo app que não resolveu é desfeito.
  - As buscas Bluetooth do app esperam enquanto uma conexão está em andamento.
  - O erro agora diz em que etapa falhou, em português (procurar o rádio, abrir a conexão ou ler os dados), e o que foi tentado com o pareamento.
- **Mostrar dados de uma conexão (#189):** o menu do rádio no topo ganhou a seção **Mostrar dados de**, com **Todas as conexões**, o rádio ativo e as conexões **MQTT**.
  - Escolhendo uma conexão, mapa, nós, mensagens, tráfego e estatísticas passam a mostrar só os dados dela.
  - Um selo "Vendo …" ao lado do rádio indica o filtro; clique nele para voltar a todas.
  - Escolher MQTT só muda a visualização: o rádio ativo continua transmitindo.

### Novidades da v0.6.46

- **MeshCore (etapa 2, #190):** ferramentas próprias para quem usa rádio MeshCore Companion.
  - **Estatísticas → MeshCore:** dados do rádio (frequência, BW, SF, potência), ocupação da lista de contatos com aviso perto do limite, **colisões de prefixo** entre repetidores (dois repetidores com o mesmo começo de chave confundem os caminhos), **mudanças de caminho** dos contatos, contatos sem anúncio há mais de 30 dias (com remoção em lote), canais do rádio (inclusive canais públicos por #hashtag), anunciar agora (vizinhos ou toda a malha), adicionar contatos automaticamente, link do próprio contato e contadores do rádio.
  - **Painel do nó MeshCore:** telemetria; nos repetidores e room servers também status (bateria, ruído, airtime, RX/TX, duplicados), vizinhos, traceroute de ida e volta com SNR de cada trecho, login com senha e comandos de CLI; e ainda redescobrir caminho, zerar caminho e remover contato. Vizinhos e traceroutes entram na topologia do mapa.
  - **Mapa → Ver → MESHCORE:** filtro por protocolo (só Meshtastic / só MeshCore), anel violeta nos nós MeshCore e caminhos dos contatos pelos repetidores.
  - **Planejamento:** presets MeshCore (SF × BW, inclusive 62,5 kHz); com rádio MeshCore conectado, a frequência, o SF/BW e a potência vêm do próprio rádio.
- **Automações (#188):** blocos separados para **Meshtastic** e **MeshCore**. No bloco MeshCore, escolha contatos para pedir **telemetria ou status periodicamente** (a partir de 15 min), com senha opcional guardada só no computador, limite de pedidos por hora e recuo automático quando o nó não responde. As mensagens automáticas valem para os dois protocolos.

### Novidades da v0.6.45

- **MeshCore (etapa 1, #185):** o app passa a receber dados de rádios **MeshCore** com firmware **Companion**, além do Meshtastic, por USB, Bluetooth ou Wi-Fi. Em Configurações → Conexões, escolha **Protocolo do rádio → MeshCore** (Wi-Fi usa a porta 5000; Bluetooth aceita o PIN do rádio). Os contatos e anúncios do MeshCore viram nós no mapa e na lista (repetidores, room servers e sensores com seus ícones), as mensagens diretas e de canal aparecem na aba Mensagens e podem ser respondidas, e cada pacote ouvido entra no Tráfego com SNR, RSSI e número de saltos. Ao plugar um rádio MeshCore na USB, ele é reconhecido e adicionado como os rádios Meshtastic; no Bluetooth, rádios "MeshCore-…" também são detectados. Meshtastic e MeshCore não conversam entre si pelo rádio: o app mostra as duas redes lado a lado.
  - Ainda não disponível para MeshCore nesta etapa: consultas remotas e ping de presença, traceroute, favoritos no rádio, apagar nós do rádio e configuração do rádio.

### Novidades da v0.6.44

- **Análise de enlace:** quando o terreno bloqueia a linha de visada, "Fresnel livre" passa a mostrar "0% (sem visada)" com a altura do terreno acima da linha, em vez de uma porcentagem negativa (tela e PDF).

### Novidades da v0.6.43

- **Bluetooth sem PIN entra sozinho (#164):** rádios Bluetooth sem PIN definido são pareados, verificados e incluídos nas conexões automaticamente, sem clique (com aviso e **Desfazer**), como já acontece na USB. Se outro rádio estiver ativo, o novo fica disponível em espera. O campo de PIN só aparece quando o rádio realmente pede um código. "Adicionar e conectar", "Adicionar automaticamente" e a busca da primeira abertura também pareiam sem PIN antes de conectar. A opção fica em Configurações → Conexões → "Adicionar e conectar sem perguntar" → Bluetooth (ligada por padrão).

### Novidades da v0.6.42

- **Elevações do terreno funcionando (#179/#180):** a análise de enlace e o melhor ponto falhavam com "Não foi possível consultar as elevações do terreno (Open-Meteo)". As elevações agora vêm dos tiles de terreno Terrarium (AWS Open Data, base SRTM), sem chave e sem limite diário, com mais detalhe (~30–40 m em vez de ~90 m). Os tiles ficam guardados no computador: áreas já analisadas funcionam sem internet. O Open-Meteo continua como alternativa, e a mensagem de erro passa a mostrar o motivo real (sem conexão, limite de uso, certificado…).
- **Melhor ponto com busca mais densa:** cerca de 2.500 amostras por área (antes 900), refinadas em volta de cada topo.

### Novidades da v0.6.41

- **Análise de enlace entre 2 pontos (#179):** no mapa, **Ver → Planejamento → Analisar enlace entre 2 pontos**. Clique em dois pontos quaisquer (ou em nós, ou digite as coordenadas) e veja:
  - distância, azimutes e altitude do terreno nas pontas;
  - perfil de altimetria com a curvatura da Terra, a linha de visada e a 1ª zona de Fresnel;
  - perda em espaço livre, perda por obstrução, sinal estimado no receptor e margem sobre a sensibilidade do preset LoRa;
  - veredito **Viável / Marginal / Inviável** com o motivo, o pior obstáculo marcado no mapa e a altura de antena que libera a zona de Fresnel.

  Altura das antenas, frequência, potência, ganhos, perdas de cabo e preset são editáveis; frequência, potência e preset vêm do rádio conectado. Os pontos podem ser arrastados. Quando uma das pontas é o seu rádio, mostra também o SNR/RSSI já recebidos do outro nó. Exporta em PDF. O botão do popup de um enlace do mapa abre a mesma análise.
- **Melhor ponto para instalar nó (#180):** **Ver → Planejamento → Melhor ponto para instalar nó**. Desenhe a área clicando no mapa (Ctrl+Z desfaz; feche no primeiro vértice, com duplo clique ou em Concluir). A ferramenta encontra os topos de morros diferentes dentro da área e os numera **do mais alto para o mais baixo**, no mapa e na tabela ao lado (altitude, desnível, distância, direção e coordenadas). Vértices editáveis, ponto de referência opcional (nó ou ponto do mapa), enlace de cada ponto até a referência ou um nó, surveys salvos, **CSV** e **PDF do survey** com mapa de relevo, tabela e perfis de enlace.

As elevações vêm do Open-Meteo e ficam guardadas no app: pontos já analisados funcionam sem internet.

### Novidades da v0.6.40

- **Alertas da malha (#165):** sino na barra superior com contador. Avisa quando um favorito fica calado por horas, bateria baixa em repetidores e favoritos, canal congestionado, mensagem privada recebida e menção ao seu rádio. Cada situação gera um único alerta até ser resolvida. Envio opcional por **Telegram** e **e-mail (SMTP)**, com botões de teste. Configurações → Alertas.
- **Backup e restauração (#166):** um único `.zip` com banco, conexões, favoritos, preferências, automações e histórico. A restauração guarda uma cópia de segurança do banco atual e reinicia o app. Serve para levar tudo para outro computador, servidor ou container. Configurações → Sistema.
- **Mapa de cobertura (#167):** camada com a qualidade (SNR) das recepções diretas por RF, por área. Menu Ver → Análise da malha.
- **Linha do tempo do nó (#168):** no detalhe do nó, gráficos de presença, bateria, tensão, SNR, utilização do canal e airtime em 24 h, 7 dias ou 30 dias.
- **Saúde dos repetidores (#169):** nova aba em Estatísticas com disponibilidade, bateria, canal, participação em rotas e presença de cada ROUTER/REPEATER.
- **Topologia e gargalos (#170):** rotas de traceroute desenhadas no mapa e a aba Topologia mostra os nós por onde mais passam as rotas.
- **Perfil de terreno (#171):** no popup de um enlace, **Perfil do terreno** mostra o relevo entre os dois nós, a curvatura da Terra e a 1ª zona de Fresnel, com um veredito sobre a visada.
- **Mensagens agendadas (#172) e respostas automáticas (#173):** em Automações, agende mensagens (uma vez, todo dia no horário ou a cada N minutos) e crie respostas a comandos como `PING` com variáveis (`{nome}`, `{snr}`, `{saltos}`, `{hora}`, `{clima}`…). Limite de envios por hora e pausa por remetente.
- **Vários canais (#174):** canais secundários do rádio aparecem como conversas e no seletor de canal; o botão **Canais…** mostra e edita nome, ativação e chave dos canais 1 a 7.
- **Busca nas mensagens (#175):** campo **Buscar no histórico…** na aba Mensagens, sem diferenciar acentos e maiúsculas, com o trecho da conversa em volta de cada resultado.
- **English / Español (#176):** idioma da interface em Configurações → Sistema → Aparência. Menus, botões, configurações e diálogos são traduzidos; algumas mensagens de estado continuam em português.
- **Relatório PDF avançado (#177):** novas seções de repetidores, rotas e gargalos, cobertura, presença e alertas/mensagens (sem o texto das mensagens).
- **PIN Bluetooth no app (#164):** quando um rádio BLE pede pareamento, o aviso traz o campo **PIN do rádio** e o botão **Parear com PIN** (Windows e Linux; no macOS o próprio sistema pede o PIN).

### Novidades da v0.6.39

- **Primeira abertura conecta sozinha (#162):** ao abrir sem nenhuma conexão, o app procura o rádio **antes** de mostrar "Configure sua primeira conexão": testa ao mesmo tempo todas as portas **USB/serial** e o primeiro rádio Meshtastic que responder é adicionado e **conectado na hora, sem clique** (com Desfazer). Sem rádio na USB, procura no Wi-Fi e no Bluetooth próximo. O aviso só aparece se nada for encontrado, agora com o resultado da busca e **Procurar novamente**. Durante a busca aparece "Procurando rádios Meshtastic…" com Cancelar.

### Novidades da v0.6.38

- **Rádio USB entra sozinho (#155):** ao plugar um rádio Meshtastic novo na USB, ele é verificado, cadastrado e conectado **sem clique**, com aviso e botão **Desfazer**. A USB tem prioridade sobre Wi-Fi e Bluetooth: se outro rádio estiver ativo, o USB assume (com retorno automático se falhar); rádios já cadastrados replugados também retomam a prioridade. Wi-Fi e Bluetooth continuam com o aviso de clique. Tudo configurável em Configurações → Conexões.
- **Verificação Bluetooth não trava mais (#156):** "Adicionar e conectar" responde na hora e acompanha a verificação com **Cancelar**, prazo máximo (30 s USB/Wi-Fi, 45 s Bluetooth), mensagem clara ao estourar e **Tentar de novo**. Rádios Bluetooth são verificados **um de cada vez** ("Na fila 2 de 4"), com orientação sobre o PIN de pareamento. "Adicionar automaticamente" também ganhou Cancelar.
- **Favoritos sincronizados (#157):** uma lista única de favoritos no aplicativo, mesclada nos dois sentidos ao conectar cada rádio (e a cada 15 s): favoritos do rádio entram no app, os do app vão para o rádio, e no conflito vale a alteração mais recente. Funciona sem rádio conectado; nós que o rádio ainda não conhece ficam pendentes e são aplicados quando ele ouvir o nó. Opção por conexão e **Sincronizar favoritos agora** no menu do rádio.
- **Mensagens no estilo WhatsApp (#158):** no canal, o remetente aparece **em cima do balão**, colorido, com nome curto e Node ID à direita; mensagens seguidas do mesmo remetente ficam agrupadas; respostas aparecem como bloco de citação; horário no canto inferior direito.
- **Ping de presença (#159):** a automação passa a chamar nós ouvidos por RF e **calados há mais de 2 h** (até 72 h), começando pelos calados há mais tempo. Sem resposta, tenta de novo em 30 min, 1 h, 2 h… até 24 h; pausa com canal congestionado e usa no máximo metade das consultas por hora. A aba Nós ganhou a coluna **Presença** ("respondeu há 10 min" / "sem resposta (3)") e nós sem resposta ficam esmaecidos no mapa. A opção "Vizinhos", que não tinha efeito, foi retirada.
- **Ubuntu / Linux Mint (#153):** novo pacote `.deb`.
- **Container (#160):** imagem oficial para servidor e Raspberry Pi.

### Novidades da v0.6.37

- **Rádio detectado ao plugar (#149):** com o app aberto, ao conectar um rádio na USB (ou quando um rádio aparece no Wi-Fi ou bem perto pelo Bluetooth), surge o aviso **“Rádio Meshtastic detectado”** com **Adicionar e conectar** · **Agora não** · **Nunca para este dispositivo**. Um clique confirma que é um rádio Meshtastic, cadastra a conexão com o nome do rádio e conexão automática marcada, e conecta. Os avisos podem ser desligados por tipo em Configurações → Conexões.
- **Adicionar automaticamente (#151):** botão novo ao lado de **Adicionar conexão manualmente**. Procura em USB, Wi-Fi e Bluetooth próximo e cadastra sozinho todos os rádios Meshtastic que ainda não estão configurados, com um resumo no final (adicionados, já configurados, sem resposta). Rodar de novo não duplica conexões.
- **Seletor do rádio ativo (#152):** clique no indicador de conexão da barra superior para escolher qual rádio fica ativo. A lista mostra só a conexão ativa e as que estão habilitadas e com o dispositivo presente agora. Se a troca falhar, o rádio anterior volta automaticamente; o escolhido passa a ser o preferido ao abrir o app.
- **Detectar automaticamente (#150):** novo nome do antigo botão “Configuração Automática”.

### Novidades da v0.6.36

- **Linux e macOS:** novos pacotes Linux x64 (`.tar.gz`) e macOS Apple Silicon/Intel (`.dmg`), gerados e testados no mesmo pipeline do Windows.
- **Downloads:** o ZIP de código-fonte deixou de ser publicado entre os arquivos da release.
- **Mensagens (#144):** o horário relativo passa a usar o horário de recepção no computador quando o relógio do rádio está apenas defasado (causa do “há 3 minutos” fixo); o horário do rádio fica visível no detalhe do horário. Horário à frente do relógio do PC mostra data/hora completas, sem idade inventada.
- **Mensagens (#145):** a conversa não volta mais sozinha para o final enquanto você lê o histórico; novas mensagens mostram o botão **↓ Novas mensagens**. Quem está no final continua acompanhando automaticamente.
- **Barra superior (#146):** o botão mostra apenas **Atualizado** (verde) ou **Nova Versão** (laranja), sem o número da versão; as versões instalada e disponível continuam no detalhe do botão e no diálogo de atualização.

### Recursos mantidos da v0.6.35

Quando houver versão nova, além do indicador no menu superior, abre um aviso perguntando se deseja atualizar agora; **Depois** adia a mesma versão por 24 horas e nada é instalado sem confirmação.

### Recursos mantidos da v0.6.34

Quebras de linha e datas nas mensagens; nome da conexão ativa na barra superior; primeira conexão de rádio disponível com demais em espera; favoritos locais com confirmação do rádio separada; fila recolhida no mapa; aviso ao sair das automações sem salvar; filtros de enlaces e ranking com posições históricas. Veja [CHANGELOG.md](CHANGELOG.md) para escopo e limites.

### Recursos mantidos da v0.6.33 — Contato, Automações e Mensagens

- **Automações (#80):** novos padrões: ligado, avaliação a cada 1 minuto, 24 consultas/hora, mínimo 60 segundos entre TX, nós das últimas 24 horas; preserva configurações anteriores. Botão Salvar automação amarelo em todos os temas.
- **Sobre (#134):** página nova /sobre com cartão “DÚVIDAS, DIFICULDADES OU SUGESTÕES? / Fale comigo”, WhatsApp 61 98402-3634 e e-mail alexpmr@gmail.com clicáveis, com o menu Ajuda e /ajuda preservados.
- **Mensagens (#129):** seletor de emojis e contador de bytes UTF-8 com bloqueio acima de 220 bytes.
- **Mensagens (#130):** clicar no balão oferece Responder e mostra uma prévia; esta versão usa fallback de citação textual, sem alegar suporte de reply nativo do firmware.
- **Mensagens (#131):** clique com botão direito sobre mensagem TX com falha permite reenviar manualmente; exige confirmação de possível duplicação e gera nova tentativa.
- **Mensagens (#132):** Canal primário sempre fixado no primeiro lugar e favoritos conhecidos do rádio em área fixa da barra lateral; resto da lista continua rolável e pesquisável.
- **Nós (#136):** coluna de estrela (★/☆/◇) e opção de menu para Favoritar/Desfavoritar usando os comandos oficiais do rádio (`setFavorite`/`removeFavorite`); não atribui confirmação antes de o NodeDB informar o novo estado. A estrela respeita a origem do rádio conectado. Requer aceite com equipamento físico.
- **NodeDB (#79, parcial):** flags booleanas explícitas de favorito importadas do rádio por fonte e persistidas em SQLite. **A alteração bidirecional dos favoritos no rádio e a atualização contínua sem reconexão ainda precisam de implementação/validação com hardware real**.
- **Escopo:** esta release NÃO encerra todo o backlog de dezenas de issues históricas. Testes em hardware Meshtastic real e UI final no Windows 10/11 continuam necessários.

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

Somente a release estável mais recente permanece disponível, com instaladores para Windows, macOS e Linux. O código-fonte não é publicado como arquivo de download da release. Após publicar e verificar os arquivos da nova versão, o pipeline remove as releases antigas e seus downloads. Tags e histórico do código são preservados; não há reescrita do Git.

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