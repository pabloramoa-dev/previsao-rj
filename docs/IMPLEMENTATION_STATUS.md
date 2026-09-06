# Estado da implementação — 06/09/2026

## Concluído neste pacote
- estrutura isolada `previsao-rj`;
- configuração geográfica inicial Rio / Niterói / Baixada;
- coletor Open-Meteo;
- snapshot normalizado;
- score editorial determinístico;
- roteiro base;
- personagem piloto próprio do RJ;
- render vertical 1080x1920;
- legenda e marca @previsaorj;
- QA por ffprobe;
- guard de isolamento;
- publicação Meta com verificação do username de destino;
- workflow manual com `publicar=false` por padrão;
- bloqueio de publicação com fixture;
- cron de manhã comentado/desativado;
- configuração Meta documentada para Instagram Login, host `graph.instagram.com` e Graph API v26.0.

## Dependências externas ainda não aplicadas
O conector GitHub disponível nesta sessão não oferece a ação de **criar um novo repositório** nem gerenciar **Actions Secrets**. Também não há conexão autenticada com Meta/Instagram para criar App, gerar token ou gravar os secrets. Por isso, o código está pronto para bootstrap, mas nenhuma credencial foi inventada ou reutilizada.

## Gate de produção
A automação permanece DESATIVADA até: repo GitHub criado -> secrets do RJ -> token health -> dry-run live -> Reel manual real -> revisão -> cron.

## Continuação da implantação
Repositório público `pabloramoa-dev/previsao-rj` criado pelo usuário e acessível ao conector. Código enviado à branch main nesta continuação. Secrets e conexão Meta continuam pendentes. Nenhuma publicação ou agenda foi ativada. O workflow da manhã ainda é apenas um guard, não um pipeline de produção completo.
