# Atendimento por comentário, DM e voz — Fase 6

O que entra em produção aqui: uma pessoa comenta ou manda DM (escrita ou
falada) pedindo o tempo do bairro dela, e recebe a previsão de hoje e amanhã em
segundos, sem ninguém digitar nada.

Serviço: `previsaorj-atendimento` (Render, plano free).
Código: `src/previsao_rj/atendimento/`.
Blueprint: `render.yaml`.

## Por que dentro deste repositório, e não em um serviço à parte

O webhook lê `config/locais_rj.yaml` e importa `previsao_rj.geo.resolver` — o
mesmo cadastro e o mesmo resolver que a esteira de Reels usa. Duas listas de
bairro sairiam do compasso na primeira semana, e o erro apareceria do pior jeito
possível: a pessoa de Icaraí recebendo o tempo de Campo Grande sem ninguém
perceber. Uma fonte de verdade só.

## O que o robô faz

| Entrada | Resposta |
|---|---|
| Comentário no Reel com um bairro | Private Reply com a previsão + confirmação curta no comentário |
| DM com bairro, praia, estádio ou município | Previsão de hoje e amanhã + linha de decisão do dia |
| DM em áudio | Transcreve e segue o mesmo caminho do texto |
| DM com `BAIRRO + CHUVA/SOL/VENTO/NUBLADO` | Registra no radar e devolve o resumo da zona |
| `RADAR` ou `RADAR + ZONA` | O que os seguidores relataram nas últimas 3h |
| `AJUDA` | Explica os comandos |

Regras de conteúdo herdadas do plano: a resposta traz **dois dias** (o Reel já
conta um; repetir seria redundante com o vídeo que a pessoa acabou de ver) e
termina em **decisão**, não em número. Em bairro de praia entra a leitura de
praia com UV; em local de `spatial_fit: baixo` (Alto da Boa Vista, Guaratiba,
Itacoatiara) entra o aviso de microclima, porque ali o modelo de ~9 km não
enxerga o que a pessoa está vendo pela janela.

Ambiguidade nunca é chutada: "Centro" e "Barra" perguntam o município antes de
responder — é o banco de ambiguidades do §4.4, já pronto desde a Fase 1.

## Trava de seguidor

Quem não segue recebe a primeira resposta por cortesia, com um convite no fecho.
Da segunda vez em diante, recebe só o convite. Se a API não responder se a
pessoa segue, ela é tratada como seguidora: ninguém fica sem previsão por erro
nosso.

## Radar colaborativo

Vive em memória do processo, de propósito: o relato só vale por poucas horas, e
um reinício custa, no pior caso, o resumo de uma janela. O ID do Instagram nunca
é guardado — o que entra é um hash com sal (`RADAR_HASH_SALT`), que serve para
não contar a mesma pessoa duas vezes e não serve para saber quem ela é.

Para tornar persistente depois: criar um Postgres, definir `DATABASE_URL` e
acrescentar `psycopg[binary]>=3.2,<4` em `requirements/atendimento.txt`. O
código já grava no banco quando a variável existe; nada mais muda.

Pergunta não vira relato: `condicao_simples` recusa qualquer mensagem com "?".
Sem isso, o radar passaria a medir curiosidade em vez de tempo.

## Mensagem de voz

Transcrição na Groq (`whisper-large-v3-turbo`), cerca de um segundo por áudio. O
áudio não é guardado em lugar nenhum: existe na memória do processo durante a
chamada e some. Áudio acima de 8 MB é descartado sem transcrever.

Rodar Whisper dentro do próprio serviço foi descartado: 512 MB de RAM e CPU
fracionada derrubariam também as respostas de texto, que funcionam bem. Sem
`GROQ_API_KEY` o robô não quebra — ele pede o bairro por escrito.

## Implantação

### 1. App da Meta — escopos

O app **Previsao RJ bot** precisa de dois escopos além dos três já pedidos:

- `instagram_business_basic` *(já)*
- `instagram_business_content_publish` *(já)*
- `instagram_business_manage_insights` *(já)*
- **`instagram_business_manage_messages`** — sem ele não há DM nem Private Reply
- **`instagram_business_manage_comments`** — sem ele não há resposta no comentário

Depois de adicionar os escopos, **gere o token de novo**: token antigo continua
valendo com as permissões antigas, e a falha aparece só na hora de responder.

### 2. Render

Deploy pelo `render.yaml` (Blueprint). Variáveis a preencher no painel:

| Variável | De onde vem |
|---|---|
| `IG_ACCESS_TOKEN` | token da conta, com os cinco escopos |
| `IG_VERIFY_TOKEN` | você inventa; a mesma string vai no painel da Meta |
| `META_APP_SECRET` | **Chave secreta do app do Instagram** — Casos de uso > Personalizar > API do Instagram > Configuração da API com login do Instagram (NÃO a de Configurações > Básico) |
| `GROQ_API_KEY` | console.groq.com > API Keys |
| `RADAR_HASH_SALT` | o Render gera sozinho |

`PYTHONPATH=src`, `EXPECTED_IG_USERNAME` e `META_GRAPH_VERSION` já vêm do
blueprint.

> **Atenção à chave secreta.** Na rota "API do Instagram com login do
> Instagram", a Meta assina os webhooks com a chave secreta **do app do
> Instagram**. Com a chave de Configurações > Básico, todo `POST /webhook`
> volta `403 assinatura invalida` nos logs do Render e nenhuma DM é respondida
> — foi o que aconteceu na implantação de 15/09/2026.

### 3. Webhook na Meta

- Callback URL: `https://<servico>.onrender.com/webhook`
- Verify token: o mesmo `IG_VERIFY_TOKEN`
- Campos: `comments` e `messages`
- O app precisa estar **publicado** (Publicar, no menu do app) para a Meta
  entregar webhooks. A publicação exige a URL da política de privacidade:
  `https://pabloramoa-dev.github.io/previsao-rj/` (arquivo `docs/index.html`).

O serviço também se inscreve sozinho em `comments,messages` no primeiro `/ping`
e no primeiro webhook — a inscrição manual é cinto e suspensório.

### 4. Manter acordado

O plano free suspende o serviço após 15 minutos sem tráfego e a volta leva perto
de um minuto — tempo suficiente para a Meta considerar o webhook fora do ar. O
workflow **Manter atendimento acordado** faz ping de 10 em 10 minutos; defina a
variable `ATENDIMENTO_URL` (Settings > Variables) com a URL do serviço.

## Verificação

`GET /ping` — saúde, idade do cache, estado do radar, se a voz está ligada.
`GET /diagnostico` — contadores por etapa. Nenhum dos dois devolve texto de
mensagem, ID de usuário ou credencial.

Aceite antes de considerar a fase concluída:

1. `/ping` responde 200 com `"eventos_assinados": "ok"`.
2. DM com "Copacabana" volta com hoje, amanhã e a linha de praia.
3. DM com "Centro" pergunta o município em vez de responder.
4. Áudio dizendo "como está o tempo na Tijuca" volta com a previsão da Tijuca.
5. Comentário em um Reel gera DM e resposta pública curta.
6. Repetir o mesmo comentário não gera segunda resposta.
7. Conta que não segue recebe cortesia uma vez e convite na segunda.

## Testes

```bash
PYTHONPATH=src python -m pytest tests/test_atendimento.py tests/test_atendimento_webhook.py -q
```

39 testes, nenhum toca a rede: a previsão é injetada e as chamadas à Meta são
substituídas. O que se verifica é o que pode responder errado para um seguidor —
bairro trocado, relato fantasma no radar, cortesia gasta duas vezes, áudio que
passa batido e reenvio da Meta virando resposta dobrada.

## Limites conhecidos

- Private Reply só vale uma vez por comentário e dentro de 7 dias, regra da Meta.
- A janela de mensagem padrão da Meta é de 24h após a última mensagem da pessoa.
- O radar zera em cada deploy enquanto não houver banco.
- O serviço free tem 512 MB: nada de Manim, Kokoro ou numpy em
  `requirements/atendimento.txt`. Quem renderiza Reel é o Actions.
