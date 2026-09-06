#!/usr/bin/env bash
set -euo pipefail
OWNER="${GITHUB_OWNER:-pabloramoa-dev}"
REPO="${GITHUB_REPO:-previsao-rj}"
FULL="$OWNER/$REPO"
command -v gh >/dev/null || { echo 'gh CLI não encontrado'; exit 2; }
gh auth status
if gh repo view "$FULL" >/dev/null 2>&1; then
  echo "$FULL já existe"
else
  gh repo create "$FULL" --public --source=. --remote=origin --push
fi
# Variables não sensíveis
gh variable set META_GRAPH_VERSION --repo "$FULL" --body 'v26.0'
gh variable set AUTOMATION_ENABLED --repo "$FULL" --body 'false'
# Secrets são lidos do ambiente/prompt do operador; nunca gravados em arquivo.
for name in IG_USER_ID IG_ACCESS_TOKEN META_APP_SECRET IG_VERIFY_TOKEN; do
  val="${!name:-}"
  if [[ -n "$val" ]]; then
    printf '%s' "$val" | gh secret set "$name" --repo "$FULL"
  else
    echo "Secret $name não definido; pulando."
  fi
done
echo "Bootstrap GitHub concluído para $FULL"
