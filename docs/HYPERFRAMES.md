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

## Estúdio completo (padrão desde 01/10/2026)

O Reel diário deixou de passar pelo Manim: a imagem inteira agora é HTML + GSAP
renderizado pelo HyperFrames (`hyperframes/`), no mesmo molde do motor aprovado
em 30/09/2026. Continuam iguais o roteiro e a pauta (`editorial/`), o corte de
duração, as vozes Kokoro (Bira `pm_alex` 1.04 às 6h, Bia `pf_dora` 1.02 às 18h),
o lip sync por amplitude, as cinco previsões obrigatórias, o QA, o preview 720p,
a miniatura e o manifesto.

- `hyperframes/gerar_hf.py` — narração, tempos, lip sync, trilha e `pacote.json`;
  aceita os mesmos argumentos do pipeline Manim (`--snapshot/--demo`,
  `--personagem`, `--format`, `--topico`, `--out`).
- `hyperframes/compor.py` — Bira e Bia redesenhados em SVG animado (respiração,
  piscada, sobrancelhas, braço apontando para o telão nas cenas de dado), telão
  com Corcovado, Pão de Açúcar com bondinho, orla e calçadão pelo tempo do dia;
  cenas abertura → número (count-up + headline-slam + carimbo do lugar) →
  quadro split-flap das cinco regiões → alerta → frase → CTA; transições glitch,
  whip-pan e flash; HUD, ticker, lower third, legenda karaokê, grão e vinheta.
- `hyperframes/compositions/instagram-follow.html` — card "Seguir" do @previsaorj.

Reversão sem editar arquivo: variável `PREVISAO_RJ_MOTOR=manim` em
Settings > Variables volta ao pipeline Manim + camada de boletim descrita acima.
Validação sem publicar: workflow "Validar estúdio HyperFrames — Previsão RJ"
(render de Bira e Bia no artifact).
