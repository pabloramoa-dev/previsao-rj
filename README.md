# Previsão RJ — @previsaorj

Pipeline **isolado** para geração e publicação de Reels meteorológicos do
@previsaorj. Construído a partir do Plano Mestre v1.1.

## Regra de isolamento

Este repositório não importa, não escreve e não depende em tempo de execução do
projeto anterior. Aquele projeto serve apenas como referência de engenharia:
vídeo 9:16, áreas seguras, artistas, QA, idempotência e publicação via API.
Personagens, dados, segredos e estados são exclusivos do RJ. `scripts/isolation_guard.py`
verifica isso em cada execução de CI.

## Estado inicial seguro

- Agendamentos de publicação permanecem desligados. O histórico de dados coleta às 06h e 18h, sem publicar.
- `publicar_manual.yml` usa `publicar=false` por padrão.
- `reel_manha.yml` é manual até o primeiro Reel real ser validado no @previsaorj.
- `coletar_dados.yml` não usa nenhum secret e não publica nada.
- Nenhum segredo é versionado.
- A versão da Graph API vem de `META_GRAPH_VERSION`.

Balanço atualizado: [STATUS_IMPLANTACAO_2026-09-07.md](docs/STATUS_IMPLANTACAO_2026-09-07.md).

Elenco atual: Bira do Tempo, Bia da Orla e Nuvem RJ. O workflow **Teste visual e vozes** produz demonstrações, ficha de expressões, Reel-base com coleta real e Stories, sem publicação.

## Fluxo

```
Open-Meteo (ECMWF + GFS + ICON)
  -> normalização em snapshot com procedência e confiança
  -> motor editorial (pontuação + gates de confiança e frescor)
  -> roteiro
  -> render 1080x1920
  -> ffprobe/QA
  -> artifact
  -> publicação manual
  -> container Meta -> FINISHED -> media_publish
```

## Camada de dados

Detalhes em `docs/DADOS.md`. Coleta manual, sem instalar nada, pelo Actions:
**Coletar dados — Previsão RJ**. O resumo da execução traz a tabela por zona, a
janela de chuva, a confiança critério a critério e o estado de cada fonte.

Localmente:

```bash
pip install -r requirements/test.txt
python -m scripts.collect_live output/snapshot.json --tier 1
python -m pytest -q
```

## Teste local determinístico do vídeo

```bash
python -m src.previsao_rj.render.test_reel --fixture tests/fixtures/snapshot_rj.json --out output/REEL_TESTE_01.mp4
python scripts/qa_video.py output/REEL_TESTE_01.mp4
```

## Segredos de produção

Veja `docs/SECRETS.md`. Os valores pertencem **somente** ao @previsaorj.
