# Meta / Instagram — sequência de ativação

1. Confirmar `@previsaorj` como conta profissional compatível com a rota escolhida da Instagram API.
2. Criar/usar um aplicativo Meta **exclusivo** do Previsão RJ.
3. Conceder somente as permissões necessárias para leitura da própria conta e publicação.
4. Obter `IG_USER_ID` e token de teste da conta RJ.
5. Executar primeiro `token_health.yml` e confirmar que o `username` retornado é exatamente `previsaorj`.
6. Executar `publicar_manual.yml` com `publicar=false`.
7. Depois de revisar artifact/capa/legenda, executar manualmente com `publicar=true`.
8. Confirmar `media_id`, capa, legenda, áudio, resolução e conta correta.
9. Só então habilitar `schedule` em `reel_manha.yml`.

A automação nunca deve ser ligada antes da etapa 8.

## Configuração escolhida (06/09/2026)

- Login: **Instagram API with Instagram Login / Business Login for Instagram**.
- Host: `https://graph.instagram.com`.
- Graph API inicial: `v26.0`, mantida em `META_GRAPH_VERSION`.
- Permissões mínimas para publicação: `instagram_business_basic` e `instagram_business_content_publish`.
- Comentários/DM entram depois com permissões próprias; não pedir escopos extras no piloto.
