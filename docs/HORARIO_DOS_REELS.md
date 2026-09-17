# Horário dos Reels diários do @previsaorj

Decisão de 17/09/2026. Dois Reels por dia, cada um preparado com antecedência
e publicado na hora marcada.

| Turno | Apresentador | Fala de | Gatilho externo | Preparo | Publica | Prazo |
|---|---|---|---|---|---|---|
| Manhã (`reel_manha.yml`) | Bira do Tempo | **hoje** | 05:15 | 05:20 | **06:00** | 10:00 |
| Noite (`reel_noite.yml`) | Bia da Orla | **amanhã** (antecipação) | 17:15 | 17:20 | **18:00** | 21:00 |

Horários de Brasília. Os marcos ficam no `env:` de cada workflow (`ALVO`,
`PREPARO_MIN`, `PRAZO`); mudar o horário é mudar essas três linhas e o horário
da tarefa no cron-job.org.

## O que o job faz

1. **trava** — se o turno já publicou hoje, ou se o disparo automático chegou
   depois do `PRAZO`, termina em segundos.
2. **espera o preparo** (`ALVO - PREPARO_MIN`) — quem disparou cedo aguarda.
3. **prepara** — coleta a previsão atual, escolhe a pauta do turno, renderiza,
   monta a legenda, roda o QA e guarda o vídeo como artifact.
4. **espera o `ALVO`** — o vídeo já está pronto.
5. **publica** — confere a conta, hospeda o MP4 num Release temporário,
   publica e grava a fila.

Disparo manual (botão *Run workflow*) não espera: prepara e publica na hora.

## O que cada turno pode publicar

- Manhã: `rio_antes_de_sair`, `chove_onde`, `vai_dar_praia`, `vai_ao_jogo` —
  só pautas sobre o dia de hoje (`editorial/turnos.py`, `FORMATOS_MANHA`).
- Noite: `amanha_no_rio` — a previsão do dia seguinte.
- `fim_de_semana` continua sendo avaliado, mas nenhum turno o publica.

## Por que gatilho externo

O `schedule` do GitHub atrasa horas ou descarta a execução (16/09: crons das
04:30–05:30 rodaram às 09:45; 17/09: não rodaram). Os crons que ficaram nos
workflows são **reserva**, de madrugada (00:47–02:47) e no início da tarde
(12:47–14:47): mesmo com horas de atraso ainda chegam antes do preparo, e o
job espera. Todos os disparos caem no mesmo grupo de concorrência; o segundo
só começa depois do primeiro e encontra a trava fechada.

## Configurar o cron-job.org (feito pelo proprietário)

Token: GitHub → Settings → Developer settings → Fine-grained tokens.
Repositório **só** `previsao-rj`; permissão **Contents: Read and write**.

Duas tarefas, fuso `America/Sao_Paulo`, todo dia:

| Tarefa | Horário | Corpo |
|---|---|---|
| Previsão RJ — manhã | 05:15 | `{"event_type":"reel_manha"}` |
| Previsão RJ — noite | 17:15 | `{"event_type":"reel_noite"}` |

- URL: `https://api.github.com/repos/pabloramoa-dev/previsao-rj/dispatches`
- Método: `POST`
- Cabeçalhos: `Accept: application/vnd.github+json`,
  `Authorization: Bearer <token>`, `Content-Type: application/json`,
  `X-GitHub-Api-Version: 2022-11-28`
- Resposta esperada: **204**. 401/403 = token errado ou sem permissão;
  404 = token sem acesso a este repositório.
