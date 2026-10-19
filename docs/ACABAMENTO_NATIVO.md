# Acabamento nativo interativo — somente CPU

Este recurso é ligado ao renderizador PRINCIPAL de cada canal. **Não recria o personagem**
nem sintetiza voz com eSpeak. O MP4 com personagem, movimentos, cenários,
Rhubarb ou outro lip sync e vozes oficiais é produzido primeiro e preservado.
Se a pauta/episódio declarar `interatividade`, o acabamento insere um cartão
com pergunta e alternativas, e um segundo cartão para revelar a resposta opcional.
Quando não existe essa chave, o MP4 é entregue **sem alteração**.

## Como ativar em um roteiro do canal

Copie o bloco `interatividade` de `examples/nativo_interativo.json` para o
objeto principal do episódio ou pauta, antes da renderização original.
A própria produção principal chamará `tools.native_video_finisher` depois
de gerar o vídeo, antes da entrega/validação. O render de demonstração CPU
independente em `tools/cpu_studio.py` continua opcional, mas NÃO é utilizado
na renderização principal.

- Nina: JSON do episódio em `episodios/`; `motor/produzir.py`.
- Pablo Guru: JSON editorial `output/episode.json`, gerado por `daily.prepare`.
- Mengão: pauta `pauta` consumida por `src.flamengo.gerar`.
- Sul Fluminense: chave `interatividade` no JSON de dados de manhã ou noite.
- Previsão RJ: chave `interatividade` no snapshot fornecido ao renderizador.
- Sábio: chave `interatividade` no item da fila editorial.

A pergunta e as alternativas são **texto visual no fecho**. Para o personagem
falar a pergunta, também inclua essa fala no roteiro original, usando sua
própria voz. Não se gera nenhum trecho com voz mecânica.

`modo`: pergunta, quiz, misterio ou mito_verdade. `pergunta` obrigatório
(8–135 caracteres), `opcoes` 2–4 quando quiz, `resposta` opcional,
`segundos` de 2 a 4. A resposta, quando configurada, aparece por mais
1,6 segundo. Preserva as legendas dos trechos falados porque os cartões são
acrescentados ao final, nunca colocados em cima da personagem.

## B-roll verdadeiro, de arquivo local autorizado

Defina dentro de `interatividade`:
```json
{"pergunta":"O que você observou nessa cena?",
 "broll_video":"assets/apoio/autorizado.mp4",
 "credito":"origem e licença do clipe local"}
```
O clipe local será reproduzido **em movimento** no espaço do cartão final.
Também é permitido `broll_imagem` no lugar de `broll_video`.
Não aceite clips sem direitos de uso; não existe pesquisa/download automático
ou requisição a Pexels/OpenAI. O caminho precisa permanecer dentro do repo.
Para não encobrir alternativas, B-roll e lista de opções não podem coexistir
no mesmo cartão.

## Segurança, custo e QA

- CPU com FFmpeg, Pillow e fontes DejaVu; nenhuma GPU ou API paga.
- `NATIVE_ENGAGEMENT_ENABLED=false` volta ao original sem alterar a voz.
- Não altera os workflows de agendamento/publicação.
- Se o vídeo ultrapassaria 180 segundos, não adiciona a cartela.
- Arquiva `*.interatividade.json` com duração, formato, origem do apoio,
  hash e verificação. Se for renderizado novamente, a fonte original deve ser
  reprocessada: evita duplicar as cartelas.
- CI usa `python -m unittest discover -s tools -p test_native_finisher.py -v`
  com um MP4 de teste sintetizado e verifica a preservação do áudio e vídeo.

### Limites

É uma camada de PARTICIPAÇÃO no final do vídeo real. Não substitui o
HyperFrames, não anima novos gestos do rig e não decide sozinho qual quiz
combina com a história. Isso seria perigoso para matérias factuais; a pauta
editorial deve selecionar a pergunta e a resposta. Não ativa automaticamente
um quiz em toda previsão nem muda os horários ou a publicação.
