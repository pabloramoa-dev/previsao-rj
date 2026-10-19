# Estudio CPU gratuito — piloto isolado

Este recurso NAO altera os motores oficiais, as credenciais, as filas nem a publicacao.
Ele prepara **um novo formato experimental** (quiz, historia com pistas, mito/verdade,
explicacao ilustrada) usando somente Python + Pillow + FFmpeg + espeak-ng. Nao usa
GPU, chave de IA, APIs pagas, servidor Render ou videos generativos.

## Execucao

Valide o roteiro sem renderizar:

    python tools/cpu_studio.py --spec examples/cpu_piloto.json --check-only

Gere o MP4 no GitHub Actions: menu Actions -> "Estudio CPU gratuito - piloto"
-> Run workflow na branch feat/estudio-cpu-gratuito-20261019.
O workflow cria um artefato temporario (1 dia), sem publicar nada.
O render do piloto usa **espeak-ng como narracao provisoria**, apenas para verificar
o fluxo. Essa voz nao substitui as vozes existentes do canal.

Para renderizar no Ubuntu local:

    sudo apt-get install ffmpeg fonts-dejavu-core espeak-ng
    python -m pip install pillow
    python tools/cpu_studio.py --spec examples/cpu_piloto.json --output output/piloto.mp4 --tts espeak

Sem voz provisoria: troque para --tts none. O video entao tera trilha de silencio,
NAO esta pronto para postagem publica.

## Formato de um roteiro

JSON: name, style (nina, guru, mengao, tempo, sabio), footer e scenes.
Cada cena: title, text, seconds (2..18), voice_text (opcional),
image (opcional) e voice_file (opcional).

- image deve apontar para um arquivo PNG/JPG local relativo ao JSON, como
  ../assets/minha_arte.png. As imagens devem ser autorizadas para reutilizacao.
- voice_file deve apontar para uma narracao MP3/WAV local feita pelo motor
  de voz oficial do personagem. Isso tem prioridade sobre a voz espeak.
- Se houver imagem, o compositor reserva area de arte e reduz o bloco textual.
- Os estilos oferecem identidade de cor; isto NAO redesenha ou anima o rig
  original do personagem. Um retrato aprovado pode ser enviado no campo image.
- A largura e altura sao 1080x1920; video H.264 e audio AAC.
- O QA basico verifica resolucao, codec e existencia de faixa de audio.
  Nao equivale a revisao humana de ritmo, roteiro, sincronismo e enquadramento.

## Custo e seguranca

Nao requer GPU nem conta em provedor externo. Runners padrao em repositorios
publicos costumam ter minutos gratuitos; em repositorios privados os minutos
contam para a franquia GitHub Actions. Confirme limites e configuracoes de
gastos da conta. Renderize sob demanda; sem publicacao nem cron por padrao.
Videos devem ficar nos artefatos temporarios, nunca commitados no Git.

## Limites desta primeira integracao

- Nao gera imagens novas por IA, nao seleciona automaticamente clipes B-roll
  e nao modifica o render dos episodios regulares.
- Para usar fotos/videos do Pexels ou Openverse, baixe apenas itens cuja
  licenca permita uso e registre a origem, sem depender de APIs pagas.
- Recursos futuros: reutilizar diretamente sprites/vozes existentes, sincronizar
  elementos com marcacoes de fala, inserir trechos reais e rodar validacao
  de legibilidade. Esses itens ainda precisam de testes individuais.
