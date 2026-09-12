# Balanço após análise do documento e do GitHub

Atualização: 07/09/2026. Projeto exclusivo `pabloramoa-dev/previsao-rj`.

O documento recebido foi comparado com os 75 arquivos então existentes na main, os workflows e o snapshot histórico. O novo trabalho implementa as prioridades do balanço; não representa lançamento no Instagram.

## Implementado nesta rodada

- Fallback por campo entre ICON, ECMWF e GFS, alinhado pela data, com modelo/origem/idade registrados. UV ausente no principal é completado sem inventar zero.
- Contraste regional de temperatura, chuva e rajadas; roteiro uniforme quando não existe contraste térmico. Ausência de observação validada continua valendo zero no critério correspondente.
- Snapshot 2.1 preserva até sete dias e a série horária por local, com origem por campo. Cache identificado pelos parâmetros completos; idade do cache não desaparece ao gerar novo snapshot.
- Coletor marítimo consultado ao vivo e ativado para ondas modeladas. Grade efetiva e data acompanham os valores. Balneabilidade e avisos oficiais continuam sendo dependências separadas.
- Seleção de candidatos, score explicável, veto por confiança/frescor, repetição em sete dias, alternância de apresentadores, deduplicação e expiração da fila local. Histórico agendado passa a gerar a avaliação editorial, sem publicar.
- Cinco roteiros com validação: Rio antes de sair, Chove onde, Vai dar praia, Fim de semana e Vai ao jogo. Jogo exige evento verificado e cobertura horária de chegada/evento/saída; praia exige boletim por local, origem e validade. Isso não significa que os cinco formatos já tenham aprovação audiovisual.
- Bira do Tempo, Bia da Orla e Nuvem RJ desenhados em código, com cenários urbano/orla. Bira e Bia usam presets sem o envelhecimento vocal do elenco legado. O motor de narração, lipsync, gestos, legendas e câmera permanece reutilizado.
- Gerador de Stories 1080×1920 por local. Rascunhos de atendimento geográfico, pergunta para nomes ambíguos e recusa a usar coleta vencida.
- Núcleo de recepção de webhook com HMAC, filtro de conta, recusa de ecos e deduplicação SQLite. É uma biblioteca local: ainda não existe endpoint público nem envio de mensagens.

## Evidências

- 91 testes locais passaram; compilação e verificação de isolamento passaram.
- CI dos commits `720d439` e `74d0d74` passou no GitHub.
- Render de demonstração de Bira/Bia no workflow `34077858519` passou, incluindo QA de resolução, codec, áudio e duração. Frames conferidos visualmente.
- Coleta expandida: oito localidades, ICON/ECMWF/GFS e mar retornaram dados utilizáveis, sete datas e 24 horários por local/dia. A confiança da coleta foi 67,8/100; não foi artificialmente elevada por observações ausentes.
- Os roteiros de base, contraste e fim de semana foram preparados com coleta real. Praia/evento também têm testes com fixtures explicitamente fictícias, que não são pauta de produção.

## Pendências reais

1. Aprovação humana dos desenhos e da sonoridade dos presets. Os arquivos são protótipos de revisão. Foram adicionadas cinco expressões e o piscar determinístico. Faltam revisão final dos adereços/cenários e revisão audiovisual dos cinco formatos, inclusive durações específicas.
2. INMET/CEMADEN: integrar observações efetivas com estação, timestamp e QC. O catálogo INMET respondeu, mas as consultas de leituras feitas nesta rodada retornaram HTTP 204. Não ligamos um coletor sem leituras verificáveis. A confirmação observacional continua indisponível.
3. INEA/DHN: falta coletor confiável de boletins e avisos, vínculo por praia e regras completas do índice de praia. Ondas do Open-Meteo não substituem esses dados. O índice ponderado do plano ainda não está implementado.
4. Meta RJ: configurar credenciais próprias, permissões e destino; publicar e validar o primeiro Reel controlado. Nenhuma credencial da outra operação foi usada.
5. Atendimento: hospedar endpoint, validar eventos reais da conta RJ, configurar private reply/respostas públicas e política de retenção. Os módulos atuais só produzem rascunhos locais.
6. Editorial/lançamento: ligar a fila ao estado persistente do publicador após a validação Meta, definir cadência aprovada e observar duas semanas de operação. O histórico editorial deve receber apenas publicações realmente confirmadas.
7. Métricas: coletar watch/share/save reais e executar os testes A/B do plano; ainda não há baseline que sustente uma otimização.

## Como reproduzir sem publicar

```bash
python -m pytest -q
python scripts/isolation_guard.py
python -m scripts.collect_live output/snapshot.json --tier 1
python -m scripts.editorial_scan output/snapshot.json
python -m src.previsao_rj.render.stories output/snapshot.json output/stories
python -m src.previsao_rj.render.characters.pipeline --demo --personagem bira --out output/bira.mp4
python -m src.previsao_rj.render.characters.pipeline --snapshot output/snapshot.json --personagem bira --format rio_antes_de_sair --out output/reel_base.mp4
```

Instalar `requirements/test.txt` e, para os vídeos, `requirements/characters.txt` e as dependências de sistema do workflow `personagens_teste.yml`. Os agendamentos de publicação permanecem desativados, como exigido pelo plano até o primeiro Reel real aprovado. Apenas a coleta de dados permanece agendada.

Referências primárias consultadas: [Open-Meteo Marine](https://open-meteo.com/en/docs/marine-weather-api), [INMET — estações automáticas](https://portal.inmet.gov.br/servicos/esta%C3%A7%C3%B5es-autom%C3%A1ticas), [INMET — acesso aos dados](https://portal.inmet.gov.br/noticias/saiba-como-acessar-os-dados-meteorol%C3%B3gicos-dispon%C3%ADveis-no-site-do-inmet).

## Fechamento da validação — 07/09/2026

- [Workflow 34130854660](https://github.com/pabloramoa-dev/previsao-rj/actions/runs/34130854660) concluído com sucesso nos dois jobs. Os 91 testes passaram no runner.
- Ficha de cinco expressões por apresentador renderizada e conferida. Corrigido um grupo vazio do Bira que fazia os limites geométricos incluírem indevidamente a origem da cena.
- Demonstrações: Bira 16,52 s; Bia aproximadamente 16,43 s. Reel-base com coleta real: 16,77 s, 1080×1920, H.264/AAC. Este Reel curto é um teste funcional; a duração editorial de 25–38 s ainda precisa ser ajustada antes do lançamento.
- Oito Stories gerados. Coleta usada no último teste: oito localidades, confiança 63/100. Os arquivos são registros dessa coleta, não uma previsão permanentemente atualizada.
- Workflow manual alinhado com Bira/Bia. O modo fixture usa demonstração e continua impedido de publicar.
- A conexão GitHub disponível não permite consultar/configurar secrets ou variables por suas rotas de API. Portanto, esta rodada não confirmou as credenciais Meta do RJ e não publicou no Instagram. Nenhum cron de publicação foi ativado.

## Atualização 12/09/2026 — credenciais, fila e provedor independente

Esta seção não reescreve o balanço acima; registra o que mudou depois dele.

**Pendência 4 — encerrada.** App próprio da Meta criado e exclusivo da conta (`Previsao RJ bot`), rota "API do Instagram com login do Instagram", três permissões e nada além: `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_insights`. Conta aceita como Testador do Instagram. Secrets `IG_USER_ID` e `IG_ACCESS_TOKEN` gravados e validados de ponta a ponta pelo workflow de saúde, sem publicar. Falta apenas a publicação do primeiro Reel controlado, que é decisão humana. Acrescentado `token_refresh.yml`, que renova o token de 60 dias e regrava o secret com um PAT restrito a este repositório.

**Pendência 6 — encerrada.** A fila do motor editorial virou o estado persistente do publicador, versionada em `data/editorial_queue.json`. Ela morava em `output/`, que o `.gitignore` descarta: nenhuma execução via o que a anterior tinha feito, e por isso os vetos de duplicata e de gancho repetido nunca chegavam a disparar — o histórico vinha de um arquivo que nenhum código escrevia. O ciclo agora é `ready → publishing → published`, com `release` quando é certo que nada foi ao ar e `unknown` quando a mídia pode existir. Item em `unknown` nunca é retentado sozinho: espera conferência humana.

**Pendências 2 e 3 — encerradas como não aplicáveis, sem implementação.**

O INMET fechou o acesso programático às leituras: além do HTTP 204 já registrado no balanço, o painel oficial passou a exigir reCAPTCHA no `POST /estacao/front/`. Não se contorna CAPTCHA, e um coletor apoiado nisso quebraria na primeira mudança da página. O CEMADEN não resolveu sequer o host a partir do ambiente de execução. O INEA publica balneabilidade em boletim, não em API, e a DHN publica avisos em texto — raspagem de documento, com a fragilidade que isso implica.

A decisão foi guiada pelo pipeline irmão, que opera há meses: ele não usa nenhuma dessas fontes e não sente falta. A regra adotada é usar apenas fonte com acesso estável e comprovado.

Consequências assumidas, e são reais: o critério "observação compatível" (§5.2, peso 20) continua valendo zero e o teto do score de confiança permanece 80, como o código já registra em `notes`; e o formato `vai_dar_praia` segue vetado por `balneabilidade_oficial_indisponivel`, porque o plano proíbe estimativa própria de balneabilidade. O veto está funcionando, não falhando.

**Novo: provedor independente.** ICON, ECMWF e GFS vinham todos pelo Open-Meteo — mesma casa, mesmo pipeline, mesmo endpoint. A "concordância entre modelos", critério de maior peso do score, nunca foi entre provedores, e uma queda do Open-Meteo levava os três juntos. Foi acrescentada a **MET Norway** (`locationforecast/2.0/compact`), o mesmo endpoint já em produção no pipeline irmão, exigindo `User-Agent` identificado.

Ela contribui para a concordância de temperatura e serve de rede de proteção: sem nenhum modelo do Open-Meteo utilizável, o snapshot ainda sai, marcado como fallback. O que a met.no não fornece nesta latitude — rajada, probabilidade de chuva e índice UV — fica **ausente** do snapshot, nunca zerado: zero seria uma afirmação, e a ausência deixa o normalizador cair no provedor que tem o dado.
