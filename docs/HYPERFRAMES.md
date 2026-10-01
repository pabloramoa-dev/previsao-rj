# HyperFrames em producao

O compositor 0.8.96 recebe a renderizacao original como camada de video e conserva
personagens, cenarios, legendas, voz, trilha, CTA e duracao. Acrescenta particulas
laterais, moldura com brilho nas trocas e progresso. O Pablo ganha movimento
suave de camera; nos cards meteorologicos o enquadramento permanece fixo.

Instalacao: `npm ci --prefix video`, depois
`cd video && npx --no-install hyperframes browser ensure`.
FFmpeg e FFprobe devem estar no PATH. Os workflows de producao instalam tudo pela
acao local setup-hyperframes. Nao existem downloads npm durante a renderizacao.

Entrega somente apos lint, render, validacao H.264/AAC, resolucao original,
30 fps, duracao com tolerancia de 150 ms e decodificacao completa.
Um arquivo .render.json registra versao, hash da fonte e duracao.
O arquivo original so e substituido depois de o candidato passar nas verificacoes.

`python -m unittest discover -s tests -p test_hyperframes_finishing.py -v`
verifica entradas, framing meteorologico e recusa de arquivos invalidos.
`python -m video.smoke` renderiza tres paletas em 1080x1920 e verifica correlacao
do audio superior a 0.98. O workflow de validacao nao publica nas redes.

Horarios, tokens, destinos e permissoes de publicacao existentes permanecem
configurados como antes. O pipeline legado de Volta Redonda continua com o cron
desativado. Documentos estaticos, carrosseis e servicos de DM nao precisam de
compositor de video.

## Modelo de boletim do Rio

O Previsao RJ segue o visual de telejornal aprovado: HUD em azul-marinho,
vermelho e amarelo; ticker com dados do proprio roteiro; lower third de Bira/Bia;
legendas destacadas em grupos de quatro palavras; glitch, whip e flash nos cortes;
grao, vinheta, trilha discreta e whooshes. A camada Manim fornece os personagens,
lip sync, cenarios do Rio e paineis meteorologicos. Marca e legendas duplicadas
sao desligadas apenas durante a geracao da camada destinada ao HyperFrames.
O conteudo editorial e as vozes originais do RJ continuam sendo usados.
