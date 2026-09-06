# Secrets exclusivos do @previsaorj

Criar no GitHub **apenas depois** de existir `pabloramoa-dev/previsao-rj`:

| Nome | Uso |
|---|---|
| `IG_USER_ID` | ID da conta profissional @previsaorj |
| `IG_ACCESS_TOKEN` | token de publicação da conta RJ |
| `META_APP_SECRET` | validação de webhook (fase DM) |
| `IG_VERIFY_TOKEN` | handshake de webhook (fase DM) |
| `PUBLIC_MEDIA_BASE_URL` | URL pública do MP4 quando houver storage dedicado |

Variables (não secret):
- `META_GRAPH_VERSION` — versão da Graph API validada em teste.
- `EXPECTED_IG_USERNAME=previsaorj` — trava contra publicação na conta errada.

**Nunca reutilizar** tokens, IDs, app secret, webhook ou estado do Previsão Sul Fluminense.

- `AUTOMATION_ENABLED=false` — segunda trava; só mudar para `true` depois do Reel manual real aprovado.
