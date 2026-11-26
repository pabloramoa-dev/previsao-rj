# Secrets exclusivos do @previsaorj

Criar no GitHub **apenas depois** de existir `pabloramoa-dev/previsao-rj`:

| Nome | Uso |
|---|---|
| `IG_USER_ID` | ID da conta profissional @previsaorj |
| `IG_ACCESS_TOKEN` | token de publicação da conta RJ |
| `META_APP_SECRET` | validação de webhook (fase DM) — usar a **chave secreta do app do Instagram** (API com login do Instagram), não a de Configurações > Básico |
| `IG_VERIFY_TOKEN` | handshake de webhook (fase DM) |
| `PUBLIC_MEDIA_BASE_URL` | URL pública do MP4 quando houver storage dedicado |

Variables (não secret):
- `META_GRAPH_VERSION` — versão da Graph API validada em teste.
- `EXPECTED_IG_USERNAME=previsaorj` — trava contra publicação na conta errada.

**Nunca reutilizar** tokens, IDs, app secret, webhook ou estado do Previsão Sul Fluminense.

- `AUTOMATION_ENABLED=false` — segunda trava; só mudar para `true` depois do Reel manual real aprovado.

## Facebook (Página Previsão RJ) — ver docs/FACEBOOK.md

- Secrets: `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_ACCESS_TOKEN` (token de Página, separado do token do Instagram).
- Variables: `FACEBOOK_PUBLISH_ENABLED` (desligado por padrão), `FACEBOOK_REELS_ENABLED`, `FACEBOOK_STORIES_ENABLED`, `FACEBOOK_EXPECTED_PAGE`, `FACEBOOK_GRAPH_VERSION`.
