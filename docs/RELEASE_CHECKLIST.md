# Gate de lançamento

Atualizado em 15/09/2026. Até aqui este arquivo ainda descrevia o estado de
07/09 — dizia que não havia credencial da Meta e que as fases 2 e 4 estavam
abertas, quando o primeiro Reel real já tinha ido ao ar em 13/09. Checklist que
mente é pior que checklist que não existe.

## Fase 0 — Isolamento
- [x] repositório `pabloramoa-dev/previsao-rj` criado
- [x] guard de isolamento cobrindo src, config, workflows, scripts e testes
- [x] nenhum segredo versionado

## Fase 1 — Dados
- [x] `config/locais_rj.yaml` com as 10 zonas do §4.2
- [x] `config/fontes.yaml` com timeout, retries, TTL e fallback por fonte
- [x] coletor multi-modelo (ECMWF + GFS + ICON)
- [x] provedor independente do Open-Meteo (MET Norway), para a concordância
      entre modelos não ser toda da mesma casa
- [x] schema de snapshot do §12.2 com source, fetched_at, valid_for, model_run e fallback_used
- [x] score de confiança 0-100 do §5.2 com os cortes de 50 e 35
- [x] resolver geográfico e banco de aliases do §4.4
- [x] snapshot válido para Rio, Niterói e Baixada — critério de saída da fase
- [x] coleta ao vivo rodando no Actions e versionada em `data/snapshots/` 2x/dia
- [~] INMET e CEMADEN: **encerrados como não aplicáveis** (12/09). INMET exige
      CAPTCHA no painel e devolve HTTP 204 nas leituras; CEMADEN não resolve o
      host. Consequência assumida: `observation_match` vale zero e o teto do
      score é 80.

## Fase 2 — Personagens
- [x] Bira do Tempo, Bia da Orla e Nuvem RJ desenhados no motor já portado
- [x] estados, ações e cenários
- [x] ficha de cinco expressões por apresentador, renderizada e conferida
- [x] sem clipping em 9:16, legível na grade
- [ ] revisão final de adereços e cenários

## Fase 3 — Render
- [x] render 1080x1920
- [x] QA por ffprobe
- [x] os 5 formatos de lançamento do §16.1 escritos e validados por dado
- [ ] revisão audiovisual formato a formato, com a duração editorial de 25–38 s
      (o Reel base hoje sai perto de 17 s)

## Fase 4 — Editorial
- [x] gerador de candidatos
- [x] pontuação de 5 critérios com os dois veto gates
- [x] controle de repetição e fadiga (§8.3)
- [x] fila com dedupe_key e expires_at (§13.3), versionada em `data/editorial_queue.json`
- [x] a fila é o estado do publicador: `ready → publishing → published`
- [x] **uma pauta decide tudo** — `scripts/escolher_pauta.py` escolhe o item e o
      mesmo item vira formato do render, personagem, legenda e dedupe_key da
      publicação (15/09). Antes os três decidiam separado e o histórico
      registrava pauta que não foi ao ar.

## Fase 5 — Instagram
- [x] publicador com verificação do username de destino e bloqueio de duplicata
- [x] secrets exclusivos do RJ configurados (`IG_USER_ID`, `IG_ACCESS_TOKEN`)
- [x] healthcheck do username `previsaorj` aprovado (12/09)
- [x] Reel manual dry-run aprovado
- [x] Reel manual real publicado e revisado (13/09, `media_id 18087503246659884`)
- [x] renovação automática do token de 60 dias (`token_refresh.yml`)
- [ ] **primeira execução do `token_refresh` confirmada** — o workflow nunca
      rodou; validar por disparo manual antes de depender dele em novembro
- [ ] automação diária habilitada: definir a variable `AUTOMATION_ENABLED=true`

## Fase 6 — Atendimento (comentário, DM e voz)
- [x] código, testes e blueprint do Render
- [ ] escopos `instagram_business_manage_messages` e
      `instagram_business_manage_comments` no app da Meta
- [ ] token regerado **depois** de adicionar os escopos
- [ ] serviço `previsaorj-atendimento` implantado no Render
- [ ] variáveis do painel: `IG_VERIFY_TOKEN`, `IG_ACCESS_TOKEN`,
      `META_APP_SECRET`, `GROQ_API_KEY`
- [ ] webhook da Meta apontando para `/webhook`, campos `comments` e `messages`
- [ ] variable `ATENDIMENTO_URL` no repositório — sem ela o workflow de ping
      sai em 0 s dizendo "nada a fazer", verde e inútil
- [ ] os sete itens de aceite de `docs/ATENDIMENTO.md`

## Fase 7 — Lançamento
- [ ] duas semanas de operação diária observadas
- [ ] cadência e horário confirmados com dado de alcance

## Fase 8 — Otimização
- [ ] watch/share/save reais coletados
- [ ] testes A/B do plano

**Rollback:** `AUTOMATION_ENABLED` diferente de `true` desliga o Reel diário sem
editar arquivo. O `workflow_dispatch` continua disponível com publicação
desligada por padrão.
