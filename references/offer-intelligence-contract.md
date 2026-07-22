# Contrato OFFER-INTELLIGENCE-0.1.0

## 1. Finalidade e isolamento

`OFFER-INTELLIGENCE-0.1.0` produz indicadores determinísticos de observação de
ofertas e anúncios. Ele é um pacote paralelo ao `SCORE-0.1.0` e não participa
da soma ponderada, do ranking oficial ou dos kill switches.

Este contrato proíbe o pacote de:

- criar, alterar ou substituir `official_score`;
- modificar pesos, dimensões ou regras de elegibilidade do score;
- estimar vendas, faturamento, lucro, ROAS ou conversão;
- tratar anúncios ativos como prova de vendas;
- converter moedas sem uma regra externa explicitamente versionada;
- preencher dados ausentes com zero, média ou qualquer valor inventado.

Os dados de entrada são observações normalizadas. Coleta, scraping e chamadas a
plataformas externas não fazem parte do motor.

## 2. Versões e arquivos autoritativos

- versão do pacote: `OFFER-INTELLIGENCE-0.1.0`;
- schema de entrada: `offer-intelligence-input-schema.json` versão `1.0.0`;
- schema de saída: `offer-intelligence-output-schema.json` versão `1.0.0`;
- configuração: `config/offer-intelligence-v0.1.json`;
- schema da configuração:
  `config/schemas/offer-intelligence-config-schema.json`.

Qualquer mudança de fórmula, denominador, janela, amostra mínima, taxonomia ou
política de ausência exige uma nova versão do pacote.

## 3. Taxonomia

### Plataformas

Valores autorizados: `meta`, `tiktok`, `google` e `other`.

Todos os snapshots usados em uma análise devem pertencer à plataforma da
oferta-alvo. Registros de mercado de outra plataforma não compõem a amostra.

### Formatos de oferta

- `quiz`: fluxo em que perguntas antecedem a apresentação ou checkout;
- `vsl`: página cuja apresentação principal é uma video sales letter;
- `direct`: página direta de oferta, produto ou checkout;
- `other`: formato observado, mas fora das três categorias autorizadas;
- `unknown`: evidência insuficiente para classificar o formato.

Somente `quiz`, `vsl` e `direct` entram no denominador de participação por
formato. `other` e `unknown` são preservados, mas excluídos desse denominador.

## 4. Seleção temporal

A janela usa limites inclusivos. Snapshots fora da janela não são utilizados.
Registros da amostra de mercado fora da janela também não são utilizados.

- snapshots são ordenados por `observed_at` e depois por `snapshot_id`, ambos
  em ordem crescente;
- baseline: primeiro snapshot da ordenação;
- atual: último snapshot da ordenação;
- timestamps devem conter fuso horário;
- `window.start_at` não pode ser posterior a `window.end_at`;
- `calculation_timestamp` não pode ser anterior ao fim da janela.

Para crescimento e churn, baseline e atual devem ser snapshots distintos da
mesma plataforma. A contagem atual pode ser calculada com apenas um snapshot.

## 5. Filtros da amostra de mercado

Uma oferta é válida para densidade quando:

1. pertence à plataforma da oferta-alvo;
2. possui o mesmo `subniche` da oferta-alvo por comparação exata;
3. está marcada como ativa;
4. possui identificadores não vazios de anunciante e oferta.

Preço utiliza o mesmo conjunto e ainda exige `ticket_amount` não nulo e moeda
idêntica à moeda da oferta-alvo. Não há conversão cambial.

Participação por formato utiliza ofertas válidas cuja classificação seja
`quiz`, `vsl` ou `direct`.

Identificadores `sample_id`, `snapshot_id`, `advertiser_id`, `offer_id` e
`creative_ids` não podem se repetir dentro do escopo em que são únicos.

## 6. Fórmulas autorizadas

Todos os cálculos internos usam decimal exato. O arredondamento para duas casas
é apenas de apresentação e nunca altera o valor interno.

### 6.1 Anúncios ativos atuais

```text
active_ads_current = current_snapshot.active_ads_count
```

- ID: `CALC-ACTIVE-ADS-CURRENT-{opportunity_id}`;
- unidade: `ads`;
- evidência: `source_evidence_ids` do snapshot atual.

### 6.2 Crescimento de anúncios ativos

```text
active_ads_growth_percent =
    (current_count - baseline_count) / baseline_count * 100
```

- ID: `CALC-ACTIVE-ADS-GROWTH-{opportunity_id}`;
- unidade: `percent`;
- mínimo: dois snapshots comparáveis;
- baseline igual a zero: indicador omitido e warning
  `active_ads_growth_zero_baseline`.

Valores negativos são válidos e representam retração da contagem observada.

### 6.3 Churn de criativos

```text
retained = count(baseline_creative_ids ∩ current_creative_ids)
creative_churn_percent =
    (count(baseline_creative_ids) - retained)
    / count(baseline_creative_ids) * 100
```

- ID: `CALC-CREATIVE-CHURN-{opportunity_id}`;
- unidade: `percent`;
- mínimo: dois snapshots com conjuntos de criativos;
- baseline sem criativos: indicador omitido e warning
  `creative_churn_empty_baseline`.

O indicador mede a parcela dos criativos do baseline que deixou de aparecer no
snapshot atual. Ele não afirma por que um criativo desapareceu.

### 6.4 Densidade de anunciantes

```text
advertiser_density_per_100_offers =
    distinct_valid_advertisers / valid_active_offers * 100
```

- ID: `CALC-ADVERTISER-DENSITY-{opportunity_id}`;
- unidade: `advertisers_per_100_offers`;
- mínimo: cinco ofertas válidas.

O indicador mede diversidade de anunciantes dentro da amostra, não o tamanho
absoluto do mercado.

### 6.5 Posição de preço

O percentil utiliza midrank para tratar empates:

```text
lower = count(sample_price < target_price)
equal = count(sample_price == target_price)
price_position_percentile = (lower + 0.5 * equal) / sample_size * 100
```

- ID: `CALC-PRICE-POSITION-{opportunity_id}`;
- unidade: `percentile_0_100`;
- mínimo: cinco ofertas comparáveis na mesma moeda;
- a oferta-alvo não é adicionada automaticamente à amostra.

### 6.6 Participação por formato

Para cada formato reconhecido:

```text
format_share_percent =
    offers_of_format / recognized_format_offers * 100
```

- IDs:
  - `CALC-OFFER-FORMAT-SHARE-QUIZ-{opportunity_id}`;
  - `CALC-OFFER-FORMAT-SHARE-VSL-{opportunity_id}`;
  - `CALC-OFFER-FORMAT-SHARE-DIRECT-{opportunity_id}`;
- unidade: `percent`;
- mínimo: cinco ofertas com formato reconhecido.

Os três valores devem somar 100 antes do arredondamento de apresentação.

## 7. Evidência e qualidade

Todo indicador deve citar pelo menos um `OBS-*` existente na entrada. A lista
de evidências é a união sem duplicatas das observações efetivamente usadas,
ordenada pela primeira ocorrência determinística.

A qualidade agregada é o menor nível entre as fontes usadas, nesta ordem:
`high`, `medium`, `low`, `unknown`. Uma qualidade ausente equivale a `unknown`.

Sinais públicos representam somente o que foi observado. Contagem de anúncios,
densidade, preço e formato não comprovam vendas ou rentabilidade.

## 8. Ausência, warnings e status

O motor nunca cria um `CALC-*` com valor `null`. Quando uma fórmula não puder
ser executada, o indicador é omitido e `missing_inputs` identifica exatamente
o campo e as entradas necessárias.

- `complete`: os oito indicadores autorizados foram gerados;
- `partial`: a entrada é válida, mas um ou mais indicadores foram omitidos;
- `invalid`: a estrutura ou uma regra semântica obrigatória foi violada.

Um resultado `invalid` não contém indicadores. Warnings não substituem
`missing_inputs` e não autorizam estimativas.

## 9. Ordem determinística de saída

Os indicadores são serializados na ordem declarada em
`indicator_definitions`. `missing_inputs` segue a mesma ordem. Warnings são
ordenados por `code` e, em seguida, pela representação dos `evidence_ids`.

## 10. Resultados esperados dos fixtures

| Fixture | Status esperado | Valores principais antes do arredondamento |
| --- | --- | --- |
| `offer_growth.json` | `complete` | atual 15; crescimento 50%; churn 50%; densidade 66,666…; preço 41,666…; formatos 33,333… cada |
| `market_saturation.json` | `complete` | atual 44; crescimento 10%; churn 25%; densidade 100; preço 75%; Quiz 60%; VSL 20%; Direta 20% |
| `insufficient_market_data.json` | `partial` | somente anúncios ativos atuais igual a 3 |

Os fixtures são sintéticos e não representam produtos, anunciantes, mercados
ou resultados comerciais reais.
