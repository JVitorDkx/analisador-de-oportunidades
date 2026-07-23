# Analisador de Oportunidades

Ferramenta para análise explicável de oportunidades de comércio digital, e-commerce, produtos, ofertas, tendências e campanhas.

O projeto combina validação de dados, cálculos determinísticos e contratos auditáveis para produzir rankings reproduzíveis. A inteligência artificial pode interpretar os resultados, mas não calcula nem altera o score oficial.

## Visão geral

O fluxo separa cada tipo de informação pelo seu papel:

- `OBS-*`: fatos observados, datados e vinculados à fonte;
- `CALC-*`: indicadores produzidos por código determinístico;
- `INF-*`: interpretações fundamentadas nas evidências;
- `REC-*`: recomendações e próximos experimentos.

Essa separação evita que dados ausentes sejam inventados, que interpretações sejam apresentadas como fatos ou que um modelo de IA altere silenciosamente os cálculos.

## Estado atual

A versão funcional `1.1.0` inclui:

- validação estrutural e semântica das entradas;
- Motor Determinístico v0.1 (`SCORE-0.1.0`);
- cálculo de indicadores econômicos autorizados;
- filtros eliminatórios de margem e orçamento;
- ranking com empates na mesma posição;
- pipeline completo de validação, scoring e enriquecimento;
- camada determinística de interpretação `INF-*` e recomendação `REC-*`;
- interface de linha de comando para execução completa;
- pacote paralelo `OFFER-INTELLIGENCE-0.1.0` para indicadores de anúncios e ofertas;
- runner isolado para inteligência de ofertas com fixtures contratuais;
- cliente TypeScript tipado gerado do contrato OpenAPI 3.1;
- CI com validações independentes para Python e TypeScript;
- validação opcional do relatório analítico final;
- contratos JSON versionados;
- suíte automatizada de testes.

## Fluxos da Fase 2

A Fase 2 adiciona três fluxos sem acoplar novas regras ao score oficial:

1. observações normalizadas de mercado → `OfferIntelligenceEngine` isolado →
   envelope versionado de indicadores `CALC-*`;
2. snapshot OpenAPI 3.1 → geração determinística → cliente Fetch e tipos
   TypeScript versionados;
3. push ou pull request → jobs independentes de validação Python e TypeScript.

O primeiro fluxo não chama o `ScoreEngine`. O segundo usa o contrato HTTP como
fonte de verdade, e o terceiro impede que a geração do cliente masque uma
regressão no núcleo Python.

## Como o score funciona

O score oficial usa a escala de 0 a 100 e combina quatro dimensões:

| Dimensão | Peso |
| --- | ---: |
| Demanda observável | 30% |
| Economia da oferta | 30% |
| Atratividade competitiva | 20% |
| Adequação operacional | 20% |

Regras importantes:

- os cálculos internos preservam precisão decimal;
- o arredondamento para duas casas ocorre apenas na apresentação;
- o ranking utiliza o valor bruto, não o valor arredondado;
- oportunidades empatadas recebem a mesma posição oficial;
- a ausência de qualquer dimensão resulta em `official_score: null`;
- pesos ausentes não são redistribuídos;
- todo indicador `CALC-*` preserva método, versão e referências `OBS-*`;
- margem de contribuição não positiva reprova a oportunidade;
- custo mínimo de teste acima do orçamento reprova a oportunidade;
- cobertura, atualidade e diversidade das fontes controlam a suficiência dos dados.

As fórmulas econômicas autorizadas calculam margem de contribuição, margem percentual, CPA de equilíbrio e compatibilidade entre o custo mínimo do teste e o orçamento. As notas normalizadas de demanda, economia e concorrência devem ser fornecidas como indicadores `CALC-*` versionados; o motor não cria fórmulas para preencher essas dimensões.

## Estrutura do projeto

```text
analisador-de-oportunidades/
├── .github/workflows/       # validação contínua de Python e TypeScript
├── clients/typescript/      # cliente Fetch tipado gerado do OpenAPI
├── config/                  # configuração versionada do score
├── data/results/            # exemplos de resultados analíticos
├── fixtures/cases/          # cenários sintéticos executáveis pela CLI e API
├── fixtures/offer_intelligence/ # cenários do pacote de inteligência de ofertas
├── references/              # schemas e políticas do projeto
├── requirements.txt         # dependências versionadas da camada Web
├── src/
│   ├── api/                  # API REST desacoplada do núcleo determinístico
│   ├── cli.py               # interface executável da ferramenta completa
│   ├── pipeline.py          # execução end-to-end
│   ├── interpretation/      # geração rastreável de INF-* e REC-*
│   ├── scoring/             # score oficial e pacote isolado de inteligência
│   └── validation/          # validadores de entrada e saída
└── tests/                   # testes e fixtures sintéticos
```

Os principais contratos estão em:

- `references/input-schema.json`: entrada da análise;
- `references/scoring-context-schema.json`: referências usadas pelo motor;
- `references/calculated-indicator-schema.json`: indicadores determinísticos;
- `references/output-schema.json`: relatório analítico final;
- `references/pipeline-output-schema.json`: envelope técnico do pipeline;
- `config/score-v0.1.json`: regras autorizadas do score;
- `references/offer-intelligence-contract.md`: regras do pacote de inteligência de ofertas;
- `references/offer-intelligence-input-schema.json`: entrada normalizada do pacote;
- `references/offer-intelligence-output-schema.json`: envelope independente do pacote;
- `config/offer-intelligence-v0.1.json`: fórmulas e políticas autorizadas do pacote.

## Requisitos

- Git;
- Python 3.11 ou superior.
- Node.js 22 ou superior e npm, somente para gerar ou validar o cliente TypeScript.

O núcleo determinístico utiliza somente a biblioteca padrão do Python. Para
executar a API Web, instale as dependências versionadas do projeto:

```bash
python -m pip install -r requirements.txt
```

## Preparação do ambiente

Clone o repositório e entre na pasta do projeto:

```bash
git clone https://github.com/JVitorDkx/analisador-de-oportunidades.git
cd analisador-de-oportunidades
```

Opcionalmente, confirme a versão do Python:

```bash
python --version
```

Em alguns sistemas o executável pode se chamar `python3`.

## Executar os testes

No PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONWARNINGS = "error"
python -m unittest discover -s tests -p "test_*.py" -v
```

No Linux ou macOS:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS=error python3 -m unittest discover -s tests -p "test_*.py" -v
```

## Validar entradas e saídas

Validar o exemplo principal de entrada:

```bash
python -m src.validation.validate_input tests/fixtures/pre-test-basic.json
```

Validar um relatório contra a entrada que o originou:

```bash
python -m src.validation.validate_output data/results/pre-test-basic-result.md tests/fixtures/pre-test-basic.json
```

Os comandos retornam um resultado estruturado e um código de saída diferente de zero quando a validação falha.

## Executar o pipeline end-to-end

O runner `src/pipeline.py` executa estas etapas:

1. valida a entrada anterior ao score;
2. resolve as referências explícitas de `scoring_context`;
3. executa o Motor Determinístico v0.1;
4. adiciona os indicadores `CALC-*` a uma cópia da entrada;
5. valida novamente a entrada enriquecida;
6. opcionalmente, valida o relatório analítico final.

Processar uma entrada e imprimir o envelope JSON no terminal:

```bash
python -m src.pipeline caminho/entrada.json
```

Processar a entrada e também validar um relatório final JSON ou Markdown:

```bash
python -m src.pipeline caminho/entrada.json --final-output caminho/resultado.md
```

Salvar o envelope técnico em um arquivo:

```bash
python -m src.pipeline caminho/entrada.json --output caminho/pipeline-result.json
```

Para usar o motor diretamente como biblioteca:

```python
from src.scoring.engine import ScoreEngine

engine = ScoreEngine.from_file("config/score-v0.1.json")
```

## Executar a ferramenta completa

A CLI executa o pipeline determinístico, gera as interpretações `INF-*`, cria
as recomendações rastreáveis `REC-*`, valida o relatório e salva o JSON final:

```bash
python -m src.cli --input caminho/entrada.json --output reports/analysis_result.json
```

Além do arquivo completo, o terminal exibe os scores oficiais, o status de cada
oportunidade, filtros eliminatórios, avisos e recomendações principais. Um
resultado `collect_more_data` ou `reject_for_now` é uma conclusão válida; o
código de saída diferente de zero fica reservado para falhas de entrada,
execução ou validação global.

### Executar os três casos demonstrativos

Execute os comandos abaixo a partir da raiz do repositório. A CLI cria a pasta
`reports/` automaticamente quando ela ainda não existe.

#### 1. Oportunidade viável

```bash
python -m src.cli --input fixtures/cases/opportunity_viable.json --output reports/opportunity_viable_result.json
```

Resultado esperado: score oficial `90.4`, status da oportunidade `scored` e
recomendação `prioritize_test`, sustentada pelos registros `OBS-*` e `CALC-*`
do fixture.

#### 2. Oportunidade reprovada por kill switch

```bash
python -m src.cli --input fixtures/cases/opportunity_kill_switch.json --output reports/opportunity_kill_switch_result.json
```

Resultado esperado: `official_score: null`, status da oportunidade `rejected`,
kill switch `non_positive_contribution_margin` e recomendação `reject_for_now`
para descarte ou correção da inviabilidade econômica.

#### 3. Oportunidade com dados insuficientes

```bash
python -m src.cli --input fixtures/cases/opportunity_insufficient_data.json --output reports/opportunity_insufficient_data_result.json
```

Resultado esperado: `official_score: null`, status global `insufficient` e
recomendação `collect_more_data`. O relatório identifica exatamente
`demand_signal_bundle` como a evidência necessária para destravar a análise.

Cada comando apresenta um resumo legível no terminal e grava o relatório JSON
completo no caminho informado por `--output`. Em sistemas onde o executável se
chama `python3`, substitua apenas `python` por `python3`.

Os três fixtures são integralmente sintéticos e servem somente para
demonstração e testes. Seus valores não representam produtos, fornecedores,
mercados ou resultados comerciais reais.

## Executar a inteligência de ofertas

O pacote `OFFER-INTELLIGENCE-0.1.0` calcula, de forma determinística e
independente, sinais de anúncios e ofertas normalizados. Ele não participa da
soma ponderada, não aciona kill switches e nunca cria ou altera o
`official_score` produzido pelo `SCORE-0.1.0`.

Os oito indicadores autorizados cobrem:

- contagem atual e crescimento percentual de anúncios ativos;
- churn de criativos entre o baseline e o snapshot atual;
- densidade de anunciantes por 100 ofertas ativas;
- posição percentil do preço dentro da amostra na mesma moeda;
- participação dos formatos `quiz`, `vsl` e `direct`.

O pacote recebe observações previamente normalizadas. Coleta, scraping,
conversão cambial e estimativas de vendas, faturamento, ROAS ou conversão não
fazem parte desse motor.

Executar o cenário de crescimento de uma oferta:

```bash
python -m src.scoring.offer_intelligence.cli --input fixtures/offer_intelligence/offer_growth.json --output reports/offer_growth_result.json
```

Executar o cenário de maior saturação de mercado:

```bash
python -m src.scoring.offer_intelligence.cli --input fixtures/offer_intelligence/market_saturation.json --output reports/market_saturation_result.json
```

Executar o cenário com dados de mercado insuficientes:

```bash
python -m src.scoring.offer_intelligence.cli --input fixtures/offer_intelligence/insufficient_market_data.json --output reports/insufficient_market_data_result.json
```

Os dois primeiros fixtures geram status `complete`. O terceiro gera status
`partial`, mantém somente os indicadores calculáveis e lista precisamente os
dados ausentes. As saídas contratuais esperadas estão em
`fixtures/offer_intelligence/expected/`.

As fórmulas, amostras mínimas, políticas de ausência e taxonomias estão
congeladas em `references/offer-intelligence-contract.md`. Qualquer alteração
nessas regras exige uma nova versão do pacote.

## Executar a API Web

A API FastAPI expõe o mesmo pipeline usado pela CLI, sem duplicar ou alterar as
regras do núcleo determinístico. Inicie o servidor de desenvolvimento:

```bash
python -m uvicorn src.api.app:app --reload
```

A documentação interativa ficará disponível em `http://127.0.0.1:8000/docs` e
o contrato OpenAPI 3.1 em `http://127.0.0.1:8000/openapi.json`. O contrato usa
modelos estritos, identificadores de operação estáveis e inclui os três
fixtures oficiais como exemplos de requisição.

Endpoints disponíveis:

| Método | Caminho | Finalidade |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Verifica a API e a configuração autorizada do score. |
| `POST` | `/api/v1/validate-input` | Valida a entrada sem executar o score ou gerar relatório. |
| `POST` | `/api/v1/analyze` | Executa o pipeline completo e retorna o relatório v1.1.0. |

O endpoint de análise recebe diretamente o payload JSON de entrada:

```text
POST /api/v1/analyze
Content-Type: application/json
```

Uma entrada válida retorna HTTP `200` com o relatório completo no schema
`1.1.0`. Uma entrada que viola o contrato estrutural ou semântico retorna HTTP
`422`. Falhas contratuais internas retornam HTTP `500`, e indisponibilidade de
uma dependência verificada pelo endpoint de saúde retorna HTTP `503`.

Os erros seguem o formato RFC 9457 e usam o media type
`application/problem+json`, com `type`, `title`, `status`, `detail` textual,
`instance`, código estável e uma lista estruturada de campos inválidos quando
aplicável. Toda resposta devolve o header `X-Request-ID`: a API preserva um
identificador válido enviado pelo cliente ou gera um novo identificador.

O endpoint preserva `official_score`, indicadores `CALC-*`, kill switches e a
rastreabilidade `OBS-*` → `CALC-*` → `REC-*`.

## Usar o cliente TypeScript

O diretório `clients/typescript/` contém um cliente Fetch e tipos TypeScript
gerados a partir do snapshot OpenAPI congelado em
`tests/api/snapshots/openapi.json`. As operações tipadas preservam os
`operationId` estáveis da API:

- `analyzeOpportunity`;
- `getHealth`;
- `validateOpportunityInput`.

Instalar as dependências fixadas no lockfile e validar o cliente:

```bash
cd clients/typescript
npm ci --ignore-scripts
npm run typecheck
npm run check:generated
```

Configuração mínima para consumir a API em uma aplicação TypeScript:

```typescript
import { client, getHealth } from "./src/index";

client.setConfig({ baseUrl: "http://127.0.0.1:8000" });

const health = await getHealth();
if (health.error) {
  throw health.error;
}

console.log(health.data);
```

Arquivos em `clients/typescript/src/generated/` não devem ser editados
manualmente. Depois de uma alteração intencional no contrato OpenAPI, execute:

```bash
npm run generate
npm run check:generated
npm run build
```

`generate` recria tipos e cliente Fetch, `typecheck` executa `tsc --noEmit`,
`check:generated` compara uma nova geração com os arquivos versionados e
`build` executa geração e verificação de tipos.

## Requisitos do `scoring_context`

Cada oportunidade processada pelo pipeline deve declarar um `scoring_context` compatível com `references/scoring-context-schema.json`.

O contexto aponta para registros `OBS-*` existentes que representam:

- dados econômicos;
- custo mínimo do teste;
- orçamento do operador;
- adequação operacional;
- prazo logístico, quando disponível.

Cada item de `independent_source_ids` deve corresponder ao `source_url` de pelo menos uma evidência observada. Identificadores sem evidência não aumentam a contagem de fontes independentes.

A idade das evidências é calculada a partir de `generated_at` e `collected_at`. Quando um indicador de dimensão referencia mais de uma evidência, o pipeline utiliza conservadoramente a evidência mais antiga.

## Status possíveis do pipeline

- `completed`: processamento determinístico concluído;
- `partial`: uma ou mais oportunidades não possuem dados suficientes para o score;
- `invalid`: a entrada, o envelope ou o relatório final viola um contrato obrigatório.

Uma oportunidade também pode ser reprovada por um filtro eliminatório autorizado. Isso é um resultado determinístico concluído, não uma falha de execução.

## Segurança e limitações

As regras obrigatórias para preços, webhooks, isolamento multi-tenant e
prevenção de escalação de privilégios estão em `SECURITY_POLICY.md`. A suíte
negativa correspondente fica em `tests/security/` e deve acompanhar qualquer
futura funcionalidade SaaS.

O projeto:

- não estima faturamento sem um modelo autorizado;
- não apresenta sinais públicos como prova de vendas;
- não promete lucro, ROAS ou conversão;
- não executa campanhas nem altera orçamentos;
- não preenche dados ausentes silenciosamente;
- não permite que a IA modifique scores ou pesos oficiais;
- trata conteúdo coletado externamente como dado não confiável.

O score ajuda a priorizar hipóteses e próximos testes. Ele não garante que uma oportunidade terá vendas ou rentabilidade.

## Integração contínua

O workflow `.github/workflows/ci.yml` é executado em pull requests e em pushes
para `main`. As validações ficam separadas em dois jobs independentes:

- `Python test suite`: instala `requirements.txt` e executa toda a suíte,
  incluindo os testes de segurança e seus subtests, com warnings tratados como
  erro;
- `TypeScript SDK`: instala pelo `package-lock.json`, executa
  `npm run typecheck` e confirma com `npm run check:generated` que o cliente
  versionado corresponde ao snapshot OpenAPI.

Essa separação mantém falhas da camada de cliente isoladas do motor Python e
torna explícito qual contrato precisa de correção.

## Desenvolvimento

Antes de enviar uma alteração:

1. execute toda a suíte de testes;
2. em `clients/typescript/`, execute `npm run typecheck` e
   `npm run check:generated`;
3. valide os exemplos afetados;
4. confirme que schemas, configuração e documentação continuam coerentes;
5. não altere pesos, regras ou enums sem versionar o contrato correspondente.
