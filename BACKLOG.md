# Backlog — PT2VHF Mesh Analyzer

Esta é uma linha nova: não confundir com o projeto PT2VHF Traffic Analyzer v1.x.

## v0.1.0 (implementado no código)

- Núcleo Python próprio e banco SQLite independente; fontes USB/Serial, TCP/IP, BLE, MQTT RX com reconexão prevista.
- Abas e visual alinhados ao Traffic Analyzer, incluindo Configurações → Fontes e Retenções.
- Nós e mensagens persistentes com filtros e busca, canais e DM via rádio selecionado, mapa com posição histórica.
- Retenção configurável individual para sete categorias, default Nunca.
- Build Windows preparada para compilação por GitHub Actions/Windows; validação real pendente.

## Próximos passos (não implementados ou ainda não validados)

1. **Validar rádio físico no Windows 11:** USB/Serial, TCP/IP e BLE; conferir recepção, envio privado, ACK/NAK, múltiplas fontes e reconexões.
2. **Build EXE/Setup na CI:** executar workflow Windows com tag v0.1.0; testes em Win11 físico, SmartScreen, Defender e uninstall preservando banco.
3. **Mensagens:** aprimorar chat privado, confirmação de ACK/NAK, reenvio, mensagens pendentes e notificações.
4. **Análise RF/roteamento:** parsing completo de traceroutes SNR por hop, ranking RF sem enlaces falsos e trilhas de nós móveis com validade temporal da posição.
5. **Compatibilidade de protocolos:** mapear formatos protobuf/versionamento e validar MQTT public/private, TLS e BLE nas diferentes plataformas.
6. **Portar funcionalidades do Traffic Analyzer:** consulta NodeInfo/telemetria, automações PING/CLIMA, alarmes, estatísticas avançadas, exportação PDF, dashboards e camadas meteorológicas.
7. **Segurança:** proteção das credenciais MQTT em repouso via Windows DPAPI/Keyring; autenticação para acesso de rede; política de cookies/sessão e TLS.
8. **Distribuição multiplataforma:** pacotes Linux (service + AppImage/deb) e macOS (.app), testes e assinatura.
9. **Banco e backup:** migração de histórico do MeshMonitor e Traffic Analyzer atual, backup/restore com integridade, controle de tamanho.
10. **Fontes e coexistência:** descoberta BLE automática, gerenciamento de nomes de fontes, diagnóstico RSSI/SNR, reconexão com backoff, filas e limite de consumo RF.

O projeto anterior permanece inalterado e não deve ser desinstalado automaticamente.