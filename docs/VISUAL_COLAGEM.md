# Visual "colagem de papel" do Reel

Desde 16/09/2026 o Reel do @previsaorj sai no estilo colagem de papel (Vox).
Mudou só a direção de arte e a finalização: as batidas, a voz, o lip sync, os
cartões de dado, a trava do dia e a publicação continuam os mesmos.

## O que aparece no vídeo

- **Folha e foto colada:** folha azul-noite com vincos; o cenário do Rio
  (céu, morros, mar, guarda-corpo) vira uma foto colada com moldura rasgada,
  fita adesiva e retícula amarela/verde-água atrás.
- **Adesivos:** Bira/Bia e a Nuvem RJ com borda branca. Braços e mãos ficam
  fora da borda, senão sobra um "braço fantasma" branco nos gestos.
- **Selo e marca:** o selo do topo (assunto do dia) é recorte amarelo com
  rótulo verde-água; a marca @previsaorj é uma tira de papel creme. O selo
  continua no primeiro e no último quadro (grade do perfil e loop).
- **Cartões de dado:** viram papel rasgado com fita e entram "colados", em
  degraus de 12 fps. Faixa colorida (umidade, UV, alerta) mantém a cor.
- **Carimbo:** a batida de alerta ganha o carimbo ATENÇÃO.
- **Legenda:** karaokê no mesmo lugar, com banda de borda rasgada e texto sem
  contorno.
- **CTA:** cartão em colagem com a chamada, o @ e a instrução.
- **Som:** voz masterizada por ganho FIXO medido + limitador (alvo −16,5
  LUFS). Nada de loudnorm de passe único no caminho do sinal.
- **Entrega:** grão de papel aplicado por ffmpeg depois do Manim, H.264
  Main / Level 4.0 a 30 fps com faststart, e um `REEL_preview_720p.mp4` no
  artifact para conferir.

## Onde está

- `src/previsao_rj/render/characters/vox_papel.py` — a camada de papel.
- `scene.py` — ramo `VOX` (fundo, adesivos, cartões, selo, legenda).
- `pipeline.py` — grão, master e entrega quando `estilo_vox()`.

## Voltar ao visual anterior

Crie a variable de repositório `PREVISAO_RJ_ESTILO` com o valor `classico`
(Settings → Secrets and variables → Actions → Variables). O `reel_manha.yml`
e o `publicar_manual.yml` leem essa variable; sem ela, vale `vox`.
Localmente: `PREVISAO_RJ_ESTILO=classico python -m src.previsao_rj.render.characters.pipeline ...`.

## Armadilhas

- O grão do papel não entra como imagem no Manim: deixa o render muito mais lento.
- A borda de adesivo usa só as formas preenchidas. Texto (o "RJ" da camisa) com
  traço grosso vira espinho branco fora do corpo.
- Manim não recorta vetor: o cenário é desenhado já do tamanho da moldura
  (`cena_rio`), com as alturas do guarda-corpo e do mar iguais às do fundo clássico.
