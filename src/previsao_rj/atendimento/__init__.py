"""Atendimento por comentario, DM e mensagem de voz — Plano Mestre, Fase 6.

Este pacote responde uma pessoa por vez, em tempo real. Ele nao publica Reel,
nao escreve no snapshot editorial e nao compartilha estado com a esteira de
producao: a unica coisa que reaproveita do resto do repositorio e o cadastro
geografico (config/locais_rj.yaml) e o resolver da secao 4.4, que ja foi
escrito na Fase 1 justamente para servir de base aqui.

Por que um coletor proprio (dados.py) e nao o collectors/ da Fase 1: aquele
coletor e multi-modelo, tem retry, QC e score de confianca, e leva dezenas de
segundos — correto para o post das 6h, errado para responder uma DM enquanto a
pessoa olha a tela. Aqui a coleta e uma chamada em lote, com cache de 20
minutos, servindo todo mundo que escrever nesse intervalo.
"""
