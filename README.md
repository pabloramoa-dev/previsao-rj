# Previsão RJ — @previsaorj

Pipeline **isolado** para geração e publicação de Reels meteorológicos do @previsaorj.

## Regra de isolamento

Este repositório **não importa, não escreve e não depende em runtime** de `previsao-sul-fluminense`.
O projeto anterior serve apenas como referência de engenharia: vídeo 9:16, safe areas, artefatos,
QA, idempotência e publicação via API. Personagens, dados, secrets e estado são exclusivos do RJ.

## Estado inicial seguro

- `schedule` permanece **desativado**.
- `publicar_manual.yml` usa `publicar=false` por padrão.
- `reel_manha.yml` é manual até o primeiro Reel real ser validado no @previsaorj.
- nenhum secret é versionado.
- a versão da Graph API vem de `META_GRAPH_VERSION`.

## Fluxo

`Open-Meteo -> snapshot -> editorial -> roteiro -> render 1080x1920 -> ffprobe/QA -> artifact -> publicação manual -> Meta container -> FINISHED -> media_publish`

## Teste local determinístico

```bash
python -m src.previsao_rj.render.test_reel --fixture tests/fixtures/snapshot_rj.json --out output/REEL_TESTE_01.mp4
python scripts/qa_video.py output/REEL_TESTE_01.mp4
pytest -q
```

## Secrets de produção

Veja `docs/SECRETS.md`. Os valores pertencem **somente** ao @previsaorj.
