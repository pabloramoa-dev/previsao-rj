# Por que a primeira tentativa falhou

Só o `README.md` e o `.gitignore` chegaram no repositório — os dois arquivos
soltos da raiz. Nenhuma das seis pastas foi. Isso acontece quando os arquivos
são arrastados **de dentro do zip** (o Windows mostra o zip como se fosse uma
pasta, mas o navegador não consegue ler as subpastas de lá).

# O jeito certo

1. **Extraia o zip de verdade** — botão direito → "Extrair tudo". Você fica com
   uma pasta `previsao-rj-fase1` no disco.
2. Abra a pasta extraída. Selecione tudo dentro dela (Ctrl+A): as pastas
   `.github`, `config`, `docs`, `scripts`, `src`, `tests` e os arquivos
   `README.md`, `.gitignore` e este `LEIA_ANTES.md`.
3. Arraste a seleção para a área de upload do GitHub.
4. Confira: a lista de arquivos que aparece na página tem que mostrar caminhos
   com barra, tipo `config/locais_rj.yaml` e `src/previsao_rj/config.py`.
   Se aparecerem só nomes soltos, os caminhos se perderam — pare e me avise.
5. Mensagem de commit:
   `Fase 1: 10 zonas, coletor multi-modelo, schema 12.2, score de confianca e resolver`

# Um arquivo precisa ser apagado

`config/locations.yml` foi substituído pelo `config/locais_rj.yaml`. Abra ele no
GitHub, três pontinhos → **Delete file** → commit. Deixar os dois cria duas
fontes de verdade para os locais, o que o plano proíbe no §12.3.

# Depois

- **Actions → CI — Previsão RJ**: 68 testes + guard de isolamento.
- **Actions → Coletar dados — Previsão RJ → Run workflow** (tier 1): primeira
  coleta ao vivo. Não usa secret e não publica nada.
