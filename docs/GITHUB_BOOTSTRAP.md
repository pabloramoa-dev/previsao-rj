# Bootstrap do GitHub

Destino: `pabloramoa-dev/previsao-rj`.

Configuração recomendada:
- visibilidade **public** no piloto, porque o MP4 do GitHub Release precisa ser baixável pela Meta e Actions de repo público evitam custo de espera;
- branch padrão `main`;
- secrets exclusivos do RJ;
- variable `META_GRAPH_VERSION=v26.0`;
- nenhuma schedule ativa no primeiro commit.

Primeira sequência de Actions:
1. `CI — Previsão RJ`.
2. `Health — Meta / @previsaorj`.
3. `Reel manual — Previsão RJ`, `fonte=live`, `publicar=false`.
4. revisar artifact.
5. repetir com `fonte=live`, `publicar=true`.
6. somente após validação humana, habilitar o cron de `reel_manha.yml`.

## Dupla trava
Mesmo depois de o `schedule` ser habilitado, o job exige `AUTOMATION_ENABLED=true`. A variável nasce como `false` no script de bootstrap.
