# Camada de dados — Fase 1

Referência: Plano Mestre v1.1, capítulos 4, 5, 12.2 e 12.3.

## O que existe

| Arquivo | Papel |
|---|---|
| `config/locais_rj.yaml` | As 10 zonas meteorológicas do §4.2, 46 pontos com coordenada, aliases, estádios, praias e o banco de ambiguidades |
| `config/fontes.yaml` | Registro de fontes com timeout, retries, TTL de cache, TTL de frescor e política de fallback |
| `src/previsao_rj/config.py` | Carrega e **valida** a configuração; falha cedo em id duplicado, zona inexistente, coordenada fora do recorte ou alias repetido |
| `collectors/base.py` | HTTP com timeout, retries limitados, cache e `SourceResult` (procedência) |
| `collectors/open_meteo.py` | ECMWF IFS + GFS + ICON, todos os pontos em uma requisição por modelo |
| `collectors/observations.py` | INMET e CEMADEN, **desligados**, com o QC do §5.3 já escrito |
| `quality/confidence.py` | Score 0-100 do §5.2 com os cortes de 50 e 35 |
| `normalizers/snapshot.py` | Schema único do §12.2 |
| `geo/resolver.py` | Resolver de bairro e alias do §4.4, base do atendimento por DM |

## Como rodar

Pelo GitHub, sem instalar nada: Actions → **Coletar dados — Previsão RJ** →
Run workflow. O resumo da execução mostra a tabela de temperaturas, a janela de
chuva, a confiança critério a critério e o estado de cada fonte. O
`snapshot.json` sai como artifact.

Localmente:

```bash
pip install -r requirements/test.txt
python -m scripts.collect_live output/snapshot.json --tier 1
python -m pytest -q
```

## Amostra: o que é coletado

`sample_tier` em `locais_rj.yaml` decide quem entra:

- **tier 1** — âncoras do Reel-base, sempre coletadas. Hoje: Barra da Tijuca,
  Campo Grande, Centro, Copacabana, Duque de Caxias, Icaraí, Nova Iguaçu e
  Tijuca. Cobrem Rio, Niterói e Baixada, que é o critério de saída da Fase 1.
- **tier 2** — entram quando há contraste, pauta de zona ou formato específico.
- **tier 3** — só por DM, bairro pedido ou evento.

## Confiança: como o número é montado

| Critério | Peso | O que mede hoje |
|---|---|---|
| Concordância de modelos | 0-30 | desvio-padrão entre ECMWF, GFS e ICON na máxima e na chuva |
| Atualidade da rodada | 0-20 | idade do dado contra o `freshness_ttl_minutes` da fonte |
| Consistência temporal | 0-15 | variação contra o snapshot anterior, quando houver |
| Observação compatível | 0-20 | **sempre 0 enquanto INMET/CEMADEN estiverem desligados** |
| Adequação espacial | 0-15 | `spatial_fit` médio dos pontos usados |

Com observação desligada o teto real é **80**, não 100 — e isso é o
comportamento correto: não há observação confirmando nada. O snapshot registra
o motivo em `confidence.notes`, em vez de fingir pontuação cheia.

Os dois gates saem prontos em `confidence.gates`:

- `allow_categorical_language` — falso abaixo de 50: o roteiro tem que falar em
  probabilidade, não em certeza.
- `allow_alert_reel` — falso abaixo de 35: Reel de alerta bloqueado; no máximo
  Story explicando a incerteza.

## Decisões que valem a pena registrar

**Rodada do modelo.** O endpoint de previsão do Open-Meteo não devolve o horário
da rodada. Em vez de inventar um valor, `model_run` guarda o início da série
horária servida, que é o que dá para verificar, e a atualidade real é medida por
`fetched_at` mais a idade do cache. Se um dia o Open-Meteo expuser a rodada,
troca-se só `_model_run()`.

**Dia de referência.** O snapshot pega o dia do próprio dado servido, não do
relógio da máquina. Assim uma fixture, um teste e um render sempre falam do
mesmo dia — o §14.2 exige que a legenda não contradiga o dia de referência.

**Falha de fonte.** Nunca vira zero silencioso. Uma fonte que cai entra no
snapshot como `failed` ou `degraded`, com o erro em `detail`; se houver cache
vencido, ele é usado e marcado com `fallback_used: true`.

**Fallback de modelo.** Sem ECMWF, o primeiro secundário utilizável é promovido
a principal e o snapshot marca `fallback_used`. Sem nenhum modelo, `build()`
levanta erro em vez de publicar um snapshot vazio.

**Praia é o bairro.** No resolver, "Icaraí" e "Barra da Tijuca" apontam para o
bairro, não para uma entidade "praia" separada — praia não é um lugar diferente
do bairro para quem pergunta.

## O que ainda não existe nesta camada

- INMET e CEMADEN ligados: falta validar o formato real de resposta contra uma
  fixture e mapear estação por zona.
- Open-Meteo Marine, INEA e Marinha/DHN: entram junto com o formato
  "Vai dar praia?" (§10.1).
- Eventos, futebol e mobilidade: os blocos existem no schema, vazios.
- `collect-data.yml` em schedule: proibido até a Fase 7.
