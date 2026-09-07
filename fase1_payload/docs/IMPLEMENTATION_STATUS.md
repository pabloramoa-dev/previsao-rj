# Estado da implementação — 07/09/2026

Referência: Plano Mestre v1.1, capítulo 16 (fases) e 17 (critérios de aceite).

## Fases

| Fase | Estado | Observação |
|---|---|---|
| 0 — Isolamento | **concluída** | repo próprio, guard de isolamento cobrindo src, config, workflows, scripts e testes |
| 1 — Dados | **concluída nesta entrega** | 10 zonas, coletor multi-modelo, schema §12.2, score de confiança §5.2, resolver de aliases §4.4 |
| 2 — Personagens | **a refazer** | ver "Decisão de 07/09" abaixo |
| 3 — Render | parcial | um formato só, narração fixa de 5 frases; faltam os outros 4 formatos de lançamento (§16.1) |
| 4 — Editorial | esboço | `scoring.py` devolve valor fixo em 3 dos 5 critérios; sem candidatos, sem fadiga, sem fila |
| 5 — Instagram | **bloqueada** | código pronto; falta app da Meta, `IG_USER_ID` e token — só o proprietário pode gerar |
| 6 — Stories + DM | não iniciada | o resolver geográfico da Fase 1 já é a base |
| 7 — Lançamento | não iniciada | |
| 8 — Otimização | não iniciada | |

## Concluído na Fase 1 (07/09/2026)

- `config/locais_rj.yaml`: as 10 zonas meteorológicas do §4.2, 46 pontos com
  coordenada e alias, 3 estádios, 11 praias, 2 terminais de barca e o banco de
  ambiguidades ("Centro", "Barra", "Caxias", "Campo Grande", "Freguesia",
  "Maracanã"). Substitui o antigo `config/locations.yml`, que tinha 7 pontos
  soltos e foi removido para não haver duas fontes de verdade.
- `config/fontes.yaml`: as 12 fontes do §5.1 registradas com timeout, retries,
  TTL de cache, TTL de frescor e fallback. Alerta Rio e COR entram na lista de
  `forbidden_weather_sources`.
- `src/previsao_rj/config.py`: carregamento com validação — id duplicado, zona
  ou município inexistente, coordenada fora do recorte metropolitano e alias
  repetido entre locais falham na leitura, não em produção.
- Coletor Open-Meteo multi-modelo (ECMWF IFS, GFS, ICON) e multi-ponto, com
  promoção automática de secundário quando o ECMWF cai.
- `collectors/base.py`: timeout, retries limitados, cache com TTL, cache vencido
  como degradação marcada e `SourceResult` com a procedência que o snapshot exige.
- `collectors/observations.py`: INMET e CEMADEN escritos e **desligados**, com o
  QC de faixa e timestamp UTC do §5.3 já implementado.
- `quality/confidence.py`: os cinco critérios do §5.2 com os pesos 30/20/15/20/15
  e os cortes de 50 (linguagem categórica) e 35 (Reel de alerta).
- `normalizers/snapshot.py`: schema §12.2 completo, mantendo intactos os campos
  que o render e a legenda já consomem.
- `geo/resolver.py`: resolver de bairro com acento, abreviação, erro de digitação
  e pergunta de desambiguação — base da Fase 6.
- `.github/workflows/coletar_dados.yml`: coleta manual, sem secret e sem
  publicação, com resumo legível no Actions e snapshot como artifact.
- 66 testes (eram 8).

## Decisão de 07/09 — personagens

O §2.3 e o §6.1 do plano proíbem reusar Ranzinza, Dona Maria e Juarez e mandam
criar **Bira do Tempo**, **Bia da Orla** e **Nuvem RJ**. A entrega de 06/09 tinha
portado Ranzinza e Dona Maria. O proprietário decidiu em 07/09 seguir o plano:
personagens próprios do RJ, reaproveitando **integralmente** a engenharia já
portada (respiração, boca por amplitude, câmera, cartões, área segura, karaokê,
Kokoro). O que muda é o desenho e a voz, não o motor.

Consequência: `src/previsao_rj/render/characters/visual.py` e `docs/PERSONAGENS.md`
serão reescritos na Fase 2. Ranzinza e Dona Maria permanecem funcionando até que
Bira e Bia passem na aprovação visual, para não ficar sem nenhum render no ar.

## Dependências externas ainda não aplicadas

Nenhuma credencial foi criada, inventada ou reutilizada. Falta, e só o
proprietário pode fazer:

1. app da Meta exclusivo do Previsão RJ;
2. `IG_USER_ID` e token da conta `@previsaorj`;
3. gravar os Secrets e as Variables listados em `docs/SECRETS.md`.

## Gate de produção

A automação permanece DESATIVADA até: secrets do RJ → `token_health` verde →
dry-run → Reel manual real aprovado → revisão → só então `schedule`.
