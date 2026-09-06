# Ranzinza e Dona Maria no Previsão RJ

Adaptação solicitada pelo proprietário do projeto. Referência lida, sem qualquer
alteração: `pabloramoa-dev/previsao-sul-fluminense`, commit
`90e2ab5e040695821437f711fed25d2875161557`.

## Identidade visual preservada

| Elemento | Ranzinza | Dona Maria |
|---|---|---|
| Cabeça | Circular, grande, pele clara, tufos grisalhos, três fios no topo | Circular, grande, cabelo grisalho e coque |
| Expressões disponíveis | Bravo, desconfiado e resmungando | Simpática e conspirando |
| Rosto | Sobrancelhas grossas, rugas laterais, nariz arredondado, bigode grisalho | Sobrancelhas arqueadas, cílios, bochechas rosadas e sorriso |
| Óculos | Meia-lua na ponta do nariz | Redondos com correntinha dourada |
| Roupa | Xadrez vermelho, suspensórios verdes, calça cinza e chinelos | Blusa azul, avental amarelo floral com bolso, saia roxa e chinelos |
| Acessórios | Bengala de madeira, copo, cachecol e guarda-chuva condicionais | Brincos dourados, avental e varal no cenário |
| Cenário | Varanda e céu animado | Quintal e varal ao entardecer |

As funções geométricas, paleta, espessuras e proporções foram copiadas por
adaptação local, não redesenhadas de memória. A marca foi trocada para
`@previsaorj`. Braços agora acompanham a mão no gesto de apontar.

## Vozes idênticas na configuração

| Parâmetro | Ranzinza | Dona Maria |
|---|---|---|
| Motor/modelo | Kokoro ONNX v1.0 | Kokoro ONNX v1.0 |
| Voz | `pm_alex` | `pf_dora` |
| Idioma | `pt-br` | `pt-br` |
| Velocidade | 0,95 | 0,95 |
| Pitch | 0,88 | 0,94 |
| Pausa entre falas | 0,30 s | 0,30 s |

Ambas: PCM mono 44.100 Hz; compensação `atempo=1/pitch`; vibrato 5,5 Hz,
profundidade 0,09; high-pass 90 Hz; compressor -18 dB, ratio 3, attack 8 ms,
release 180 ms; volume 1,15. Não há substituição silenciosa por eSpeak:
ele é apenas o fonetizador do Kokoro. Se o modelo falhar, o render falha.

## Recursos transportados

- Respiração contínua e boca por amplitude a 22 amostras/s, suavização RMS,
  distinção por zero-crossing e visemas X/B/C/D/E/F, acompanhando a boca original.
- Sol girando, nuvens deslizando, chuva, poças, relâmpagos, névoa e ondas de calor.
- Copo/beber, cachecol, tremor de frio, bafo, apontar, abanar, suor, guarda-chuva
  e gotas. Uso condicionado aos dados/ações da cena, não tudo simultaneamente.
- Varal com roupas oscilando e céu de entardecer da Dona Maria.
- Legenda karaokê, cartões, número em destaque, entrada com escala,
  câmera com aproximação e deriva, selo geográfico e saída do personagem no resumo.
- Render 1080×1920, 30 fps, H.264/AAC. Vídeo não é acelerado para encaixar a voz.

As expressões alternativas existem nos construtores; a cena padrão usa bravo
para ele e simpática para ela. Nem todo efeito aparece no teste curto.
O karaokê estima tempos por palavra; não é alinhamento fonético palavra a palavra.

## Arquivos e validação

`src/previsao_rj/render/characters/` contém visual, movimento, boca, síntese,
cena e orquestração. Nenhum import ou download de código do Sul Fluminense
ocorre em runtime. Nenhuma credencial, banco ou workflow de produção foi copiado.

`personagens_teste.yml` gera dois MP4s demonstrativos e imagens no Actions,
sem secrets, sem permissão de escrita e sem etapa de publicação. Rodar localmente:

```bash
pip install -r requirements/characters.txt
python -m src.previsao_rj.render.characters.pipeline --demo --personagem ranzinza --out output/ranzinza.mp4
python -m src.previsao_rj.render.characters.pipeline --demo --personagem maria --out output/maria.mp4
```

Necessário instalar FFmpeg, espeak-ng, Cairo/Pango e fontes Poppins, como descrito
no workflow de teste. A aprovação visual e auditiva depende dos MP4s concluídos;
ter os mesmos presets não comprova, por si só, o resultado final.
