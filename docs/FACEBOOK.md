# Publicação na Página do Facebook — Previsão RJ

O mesmo MP4 do Reel do Instagram vai para a Página **Previsão RJ** como Reel (e,
se ligado, como Story). Nada é renderizado de novo.

## Como funciona

```
reel (job do Instagram)          facebook (job separado)
  render -> MP4 -> Release  ───►   baixa o artifact (legenda) e usa a MESMA URL do MP4
  publica no Instagram             start -> upload por file_url -> finish (video_reels)
  grava fila editorial             confirma na Meta, grava data/facebook_publicacoes.json
```

- **Independência:** o job `facebook` roda com `always()`. Se o Instagram falhar,
  o Facebook publica mesmo assim (o MP4 já está no Release). Se o Facebook
  falhar, o Instagram não é repetido nem desfeito.
- **Duplicidade:** chave `repo|facebook|page_id|tipo|dedupe_key`. Item
  `published` nunca é reenviado; `unknown` é conferido na Meta antes de qualquer
  nova tentativa.
- **Reenvio só do Facebook:** workflow *Facebook — reenviar só o Facebook*
  (`facebook_reenviar.yml`), com a URL do MP4 e a `dedupe_key` do resumo da
  execução original. O Release dura 7 dias.
- **Erros:** OAuth 190 / permissão / ID errado = para na hora (não insiste);
  limite de requisições, 5xx e rede = 4 tentativas com espera 10s, 30s, 90s.
  Tokens são mascarados em logs e no estado.
- **Trava de destino:** o token precisa ser da própria Página (`/me` = `FACEBOOK_PAGE_ID`)
  e o nome/usuário da Página precisa bater com `FACEBOOK_EXPECTED_PAGE`.
- **Limites da Meta:** Reel de 3 a 90 s; Story até 60 s (acima disso é
  registrado como `skipped`, sem erro); 30 Reels por API a cada 24 h por Página.

## Chaves

| Onde | Nome | Valor |
|---|---|---|
| Variable | `FACEBOOK_PUBLISH_ENABLED` | `true` liga. **Sem ela, nada vai ao Facebook.** Rollback de um clique. |
| Variable | `FACEBOOK_REELS_ENABLED` | padrão `true` |
| Variable | `FACEBOOK_STORIES_ENABLED` | padrão `false` |
| Variable | `FACEBOOK_EXPECTED_PAGE` | padrão `Previsão RJ` |
| Variable | `FACEBOOK_GRAPH_VERSION` | padrão `v25.0` |
| Secret | `FACEBOOK_PAGE_ID` | ID da Página Previsão RJ |
| Secret | `FACEBOOK_PAGE_ACCESS_TOKEN` | token **de Página** de longa duração |

Os secrets do Instagram (`IG_USER_ID`, `IG_ACCESS_TOKEN`) **não mudam**.

## O que o Pablo precisa fazer (uma vez por canal)

1. **Criar a Página** "Previsão RJ" (categoria Site de notícias e mídia) e
   vincular o @previsaorj em Configurações da Página › Contas vinculadas ›
   Instagram (pede o login do Instagram).
2. **App da Meta "Previsao RJ bot":** adicionar o caso de uso *Gerenciar tudo na
   sua Página* com `pages_show_list`, `pages_read_engagement` e
   `pages_manage_posts`. O app precisa estar no modo **Ativo**: posts feitos por
   app em desenvolvimento não ficam visíveis ao público. Para Páginas que o
   próprio administrador do app gerencia, o acesso padrão basta (sem App Review
   nem verificação de empresa).
3. **Token de Página que não expira:** no Explorador da Graph API, gerar o token
   de usuário com as três permissões, trocar por token de longa duração e pegar
   o `access_token` da Página em `/me/accounts`. Esse token de Página não
   expira enquanto a senha e as permissões não mudarem.
4. Colar `FACEBOOK_PAGE_ID` e `FACEBOOK_PAGE_ACCESS_TOKEN` em Settings › Secrets
   do repositório e criar a variable `FACEBOOK_PUBLISH_ENABLED=true` só depois do
   primeiro teste.
5. **Não** ligar o compartilhamento automático Instagram → Facebook no Meta
   Business Suite/Instagram: com ele ligado, cada Reel apareceria duas vezes na
   Página.
