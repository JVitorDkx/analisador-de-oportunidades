# Analisador de Oportunidades

Agente de inteligência para análise explicável de oportunidades de comércio digital, e-commerce, produtos, ofertas, tendências e campanhas.

O projeto separa rigidamente:

- `OBS-*`: fatos observados e rastreáveis;
- `CALC-*`: indicadores produzidos por código determinístico;
- `INF-*`: interpretações da IA;
- `REC-*`: recomendações e próximos experimentos.

## Motor v0.1

O Motor Determinístico v0.1 (`SCORE-0.1.0`) transforma entradas estruturadas e indicadores rastreáveis em um score oficial reproduzível, sem usar IA para cálculos.

O score opera na escala de 0 a 100 e combina quatro dimensões:

| Dimensão | Peso |
| --- | ---: |
| Demanda observável | 30% |
| Economia da oferta | 30% |
| Atratividade competitiva | 20% |
| Adequação operacional | 20% |

Características atuais:

- cálculos internos com precisão decimal;
- duas casas decimais apenas na apresentação;
- ranking baseado no valor bruto não arredondado;
- empates com a mesma posição oficial;
- ausência de uma dimensão resulta em `official_score: null`;
- pesos ausentes não são redistribuídos;
- indicadores `CALC-*` mantêm método, versão e referências `OBS-*`;
- margem de contribuição não positiva reprova a oportunidade;
- custo mínimo de teste acima do orçamento reprova a oportunidade;
- cobertura, idade das evidências e quantidade de fontes controlam a suficiência dos dados.

As fórmulas econômicas autorizadas calculam margem de contribuição, margem percentual, CPA de equilíbrio e compatibilidade entre custo mínimo de teste e orçamento. As notas normalizadas de demanda, economia e concorrência devem chegar como indicadores determinísticos `CALC-*` versionados; o motor não inventa fórmulas para produzi-las.

As regras versionadas ficam em `config/score-v0.1.json`. O código do motor está em `src/scoring/` e os contratos de entrada, saída e indicadores estão em `references/`.

## Executar localmente

Requisito: Python 3.11 ou superior. O núcleo atual utiliza somente a biblioteca padrão do Python.

No PowerShell, entre no repositório e desative a geração de bytecode durante os testes:

```powershell
cd C:\Users\clemi\Documents\Codex\analisador-de-oportunidades
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m unittest discover -s tests -p "test_*.py" -v
```

Validar o fixture principal de entrada:

```powershell
python -m src.validation.validate_input tests/fixtures/pre-test-basic.json
```

Validar o relatório de saída contra a entrada original:

```powershell
python -m src.validation.validate_output data/results/pre-test-basic-result.md tests/fixtures/pre-test-basic.json
```

Carregar programaticamente o motor autorizado:

```python
from src.scoring.engine import ScoreEngine

engine = ScoreEngine.from_file("config/score-v0.1.json")
```

## Pipeline end-to-end

O runner `src/pipeline.py` executa, em ordem:

1. validação da entrada pré-score;
2. resolução das referências explícitas de `scoring_context`;
3. execução do Motor Determinístico v0.1;
4. inclusão dos novos indicadores `CALC-*` em uma cópia da entrada;
5. nova validação da entrada enriquecida;
6. validação opcional da saída analítica final.

Executar o pipeline e imprimir o envelope JSON no terminal:

```powershell
python -m src.pipeline caminho/entrada.json
```

Validar também um relatório final JSON ou Markdown:

```powershell
python -m src.pipeline caminho/entrada.json --final-output caminho/resultado.md
```

Salvar o envelope técnico do pipeline:

```powershell
python -m src.pipeline caminho/entrada.json --output caminho/pipeline-result.json
```

Cada oportunidade processada deve declarar `scoring_context` conforme `references/scoring-context-schema.json`. O contexto referencia registros `OBS-*` existentes para economia, custo mínimo, orçamento, fit operacional e logística. Cada item de `independent_source_ids` deve corresponder ao `source_url` de pelo menos uma evidência observada; identificadores sem respaldo não aumentam a contagem de fontes. As idades são calculadas a partir de `generated_at` e das datas das evidências; quando um `CALC-*` de dimensão usa mais de uma evidência, aplica-se conservadoramente a maior idade entre elas.

## Segurança e limitações

O projeto não estima faturamento sem modelo autorizado, não trata sinais públicos como prova de vendas, não promete lucro e não executa campanhas ou alterações de orçamento. Dados ausentes permanecem ausentes: nenhuma regra pode preencher lacunas ou fabricar evidências silenciosamente.
