# Análise exploratória do dataset Album of the Year

Projeto em Python para explorar o arquivo `aoty.csv`, que reúne notas de usuários,
álbuns, artistas, gêneros, datas de lançamento e quantidade de avaliações.
O script produz tabelas CSV, gráficos PNG e um relatório em Markdown.

## Resultados iniciais

O arquivo anexado contém **5.000 álbuns** e oito colunas. Nesta versão do dataset,
as colunas originais não têm valores vazios nem IDs ou links duplicados. As notas
variam de **75 a 95**, com média **80,25** e mediana **80**. A quantidade de
avaliações é assimétrica: mediana **482** e média aproximada de **1.255**.

Há mais álbuns dos anos 2010 do que de qualquer outra década. A correlação de
Spearman entre nota e número de avaliações é de aproximadamente **0,337**: uma
associação positiva moderada, que não deve ser interpretada como causalidade.
O conjunto também é uma seleção de álbuns e usuários da fonte, não uma amostra
aleatória de toda a música publicada.

## Grupos de descoberta por gênero e nota

O script também associa cada álbum a todos os gêneros listados nele e a uma faixa
de nota (`<80`, `80-<85`, `85-<90` ou `90+`). Isso permite explorar candidatos
para alguém que já sabe quais gêneros prefere; dentro de cada grupo, os álbuns são
ordenados por nota e, em caso de empate, por número de avaliações. Álbuns com mais
de um gênero aparecem em mais de um grupo.

São gerados `grupos_genero_nota.csv` (resumo dos grupos),
`albuns_por_genero_faixa_nota.csv` (álbuns e atributos de cada grupo) e dois
gráficos adicionais: um mapa de calor da proporção de faixas de nota por gênero
e boxplots para comparar a distribuição de notas nos gêneros mais frequentes.

Esses grupos são filtros de catálogo baseados em conteúdo e notas agregadas, não
clusters aprendidos a partir do comportamento dos ouvintes. Eles podem ajudar a
montar listas candidatas, mas não demonstram que uma pessoa específica gostará dos
álbuns. Para validar ou personalizar recomendações, ainda são necessários dados
de interações individuais.

## Estrutura

- `data/aoty.csv` — cópia local do dataset anexado.
- `src/aoty_eda.py` — validação, transformação, estatísticas e geração dos resultados.
- `tests/` — testes automatizados para leitura, validação e geração.
- `reports/` — relatório, tabelas e gráficos criados ao executar o projeto.

## Como executar

Requer Python 3.10 ou superior. Instale as duas dependências diretamente, cada uma
em seu próprio comando:

```powershell
python -m pip install pandas
python -m pip install matplotlib
python src\aoty_eda.py
```

Para usar outro CSV ou definir a pasta de saída:

```powershell
python src\aoty_eda.py --csv caminho\para\aoty.csv --output-dir reports
```

Os formatos de data são interpretados durante a leitura. Notas, datas ou contagens
inválidas em campos preenchidos geram um erro explícito, em vez de serem descartadas
silenciosamente.

## Testes

```powershell
python -m unittest discover -s tests -v
```
