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

O runner end-to-end ainda será implementado em uma etapa posterior. Até lá, o motor é consumido como biblioteca Python e os validadores possuem interfaces de linha de comando próprias.

## Segurança e limitações

O projeto não estima faturamento sem modelo autorizado, não trata sinais públicos como prova de vendas, não promete lucro e não executa campanhas ou alterações de orçamento. Dados ausentes permanecem ausentes: nenhuma regra pode preencher lacunas ou fabricar evidências silenciosamente.
