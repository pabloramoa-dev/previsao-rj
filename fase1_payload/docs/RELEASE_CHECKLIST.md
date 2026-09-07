# Gate de lançamento

## Fase 0 — Isolamento
- [x] repositório `pabloramoa-dev/previsao-rj` criado
- [x] guard de isolamento cobrindo src, config, workflows, scripts e testes
- [x] nenhum segredo versionado

## Fase 1 — Dados
- [x] `config/locais_rj.yaml` com as 10 zonas do §4.2
- [x] `config/fontes.yaml` com timeout, retries, TTL e fallback por fonte
- [x] coletor multi-modelo (ECMWF + GFS + ICON)
- [x] schema de snapshot do §12.2 com source, fetched_at, valid_for, model_run e fallback_used
- [x] score de confiança 0-100 do §5.2 com os cortes de 50 e 35
- [x] resolver geográfico e banco de aliases do §4.4
- [x] snapshot válido para Rio, Niterói e Baixada — critério de saída da fase
- [ ] INMET e CEMADEN ligados e validados contra fixture
- [ ] primeira coleta ao vivo rodada no Actions e revisada

## Fase 2 — Personagens
- [ ] Bira do Tempo, Bia da Orla e Nuvem RJ desenhados no motor já portado
- [ ] estados, ações e cenários
- [ ] snapshots visuais de referência por personagem e expressão
- [ ] sem clipping em 9:16, legível na grade

## Fase 3 — Render
- [x] render 1080x1920
- [x] QA por ffprobe
- [ ] os 5 formatos de lançamento do §16.1

## Fase 4 — Editorial
- [ ] gerador de candidatos
- [ ] pontuação de 5 critérios com os dois veto gates
- [ ] controle de repetição e fadiga (§8.3)
- [ ] fila com dedupe_key e expires_at (§13.3)

## Fase 5 — Instagram
- [x] publicador com verificação do username de destino e bloqueio de duplicata
- [ ] secrets exclusivos do RJ configurados
- [ ] healthcheck do username `previsaorj` aprovado
- [ ] Reel manual dry-run aprovado
- [ ] Reel manual real publicado e revisado
- [ ] automação habilitada

**Rollback:** comentar/remover `schedule`; `workflow_dispatch` continua
disponível com publicação desligada por padrão.
