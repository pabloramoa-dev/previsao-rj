# Stories — design vetorial v2

Renderer: `resvg-py==0.5.0`, binding de https://github.com/linebender/resvg (https://github.com/sparkfish/resvg-py).
Ícones: https://github.com/basmilius/meteocons, pacote `@meteocons/svg-static` 0.1.0, estilo fill. Os 12 SVGs selecionados estão versionados; licença MIT incluída.
Fonte: Manrope, https://github.com/google/fonts/tree/main/ofl/manrope e https://github.com/sharanda/manrope. Instâncias estáticas de pesos 400 e 800 extraídas da fonte variável; licença OFL incluída.

O render funciona sem baixar fontes ou ícones. Saída 1080×1920; layout em SVG, com PNG produzido por resvg. Temperatura máxima, mínima, probabilidade diária, rajadas, UV e próximos horários disponíveis vêm do snapshot. Valores ausentes ficam como travessão. O ícone segue o código WMO, não apenas a probabilidade de chuva.

`--preview` permite revisar uma coleta histórica com marca explícita de estudo visual. Sem essa opção, permanece o bloqueio de coleta vencida. Este comando não publica e não responde por DM. Os cards não anunciam atendimento automático ainda não conectado.
