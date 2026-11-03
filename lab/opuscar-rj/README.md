# Lemo Opuscar / Previsão RJ — telejornal experimental

Piloto sem publicação para o Bira do Tempo, usando a linguagem visual de News Package e Data Storytelling de https://github.com/lemomo-ai/lemo-opuscar.

O compositor é uma adaptação original leve em Pillow/FFmpeg. Não instala nem executa o motor WebGL completo do Opuscar: respeita os limites CPU do Actions, preserva o vídeo existente do HyperFrames, a voz Kokoro pm_alex, o lip sync, as legendas, a duração integral do roteiro e os dados de previsão do RJ.

Saídas: output/REEL_OPUSCAR_RJ.mp4 (vídeo completo), output/REEL_OPUSCAR_RJ_preview_720p.mp4 (prévia), output/CAPA_OPUSCAR_RJ.jpg (capa), output/REEL_OPUSCAR_RJ.json (relatório).

A abertura usa temperaturas e chance de chuva de localidades reais extraídas do output/snapshot.json ao vivo, com barras animadas. A data aparece na tela. Não se inventam números.

## Segurança
O workflow lemo-telejornal-rj-piloto.yml usa contents: read, não recebe credenciais da Meta e não possui passo de publicação. O compositor rejeita fixtures e dados inconsistentes, verifica áudio, resolução, FPS, duração e decodificação. Avaliar o artifact antes de usar no pipeline diário.

## Teste local

1. python -m pip install pillow
2. python -m unittest discover -s lab/opuscar-rj -p test_*.py -v
3. python lab/opuscar-rj/montar.py --original output/REEL_BASE_RJ.mp4 --snapshot output/snapshot.json --saida output/REEL_OPUSCAR_RJ.mp4

É necessário renderizar o vídeo base com o HyperFrames usando dados ao vivo.

Créditos da referência visual: https://github.com/lemomo-ai/lemo-opuscar.
