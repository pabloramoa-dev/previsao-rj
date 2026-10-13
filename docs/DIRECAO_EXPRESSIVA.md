# Estilo expressivo — Previsão RJ

Inspirado na direção aprovada da Nina e na evolução do Previsão Sul Fluminense, mas adaptado à identidade visual de Bira e Bia.

## Motor principal: HyperFrames

- Direção de cada fala calculada pela timeline real da voz.
- Gestos do braço esquerdo, sem competir com o direito que aponta para o telão.
- Aproximações de câmera de até 6%, somente no avatar; cartões e legendas não se deslocam.
- Zoom retorna ao normal antes do fim do vídeo.
- Plano de direção incluído no pacote.json.
- Relatório .quality.json por vídeo, com verificações estruturais.

## Motor Manim de reserva

- Mão esquerda com o mesmo planejamento por fala. O braço segue essa mão.
- Preserva voz, boca, desenhos, ação do braço direito e cenários existentes.

## Custo e reversão

- PREVISAO_RJ_DIRECAO=1 (padrão) ativa os novos movimentos.
- PREVISAO_RJ_DIRECAO=0 desativa o estilo sem editar o código.
- Não exige APIs pagas adicionais.

## Testes

- CI com testes de direção, integridade das previsões e QA.
- Matriz HyperFrames de Bira e Bia.
- Render Manim de reserva sem publicação automática.
- Conferência visual final recomendada após cada revisão de estilo.

## Garantias de preservação

A integração não modifica os horários, as fontes meteorológicas, os limiares de alertas, os dados de bairros, o atendimento por DM ou o sistema de publicação. O relatório técnico não comprova precisão meteorológica nem substitui inspeção dos frames.
