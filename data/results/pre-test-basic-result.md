```json
{
  "schema_version": "1.0.0",
  "analysis_id": "ANL-FIXTURE-0001",
  "analysis_mode": "pre_test",
  "processed_at": "2026-07-20T17:12:00-03:00",
  "input_status": "partial",
  "security_status": {
    "prompt_injection_detected": false,
    "suspicious_fields": [],
    "sensitive_data_detected": false
  },
  "versions": {
    "skill_version": "1.0.1",
    "input_schema_version": "1.0.0",
    "output_schema_version": "1.0.0",
    "score_version": "SCORE-0.1.0"
  },
  "recommended_opportunity_id": null,
  "recommendation": "collect_more_data",
  "confidence": "inconclusive",
  "executive_summary": "A entrada é estruturalmente válida, mas possui qualidade parcial e não contém os componentes necessários para determinar economia da oferta ou compatibilidade do teste com o orçamento. Os scores oficiais foram preservados, sem recálculo, e não sustentam sozinhos a escolha de uma oportunidade.",
  "context_assessment": {
    "fit": "unknown",
    "budget_compatibility": "unknown",
    "channel_compatibility": "unknown",
    "operational_constraints": [
      "operacao_individual"
    ],
    "explanation": "O operador está no Brasil, informa orçamento de R$ 500 e Meta Ads como canal principal, mas o custo mínimo de teste, a economia da oferta e a capacidade criativa necessária não estão disponíveis. Não é possível afirmar que qualquer oportunidade cabe no orçamento."
  },
  "ranking": [
    {
      "position": 1,
      "opportunity_id": "OPP-001",
      "official_score": 64,
      "official_score_scale": "0-100",
      "official_score_rank": 1,
      "contextual_recommendation_rank": 1,
      "context_fit": "unknown",
      "strengths": [
        {
          "statement": "O motor determinístico forneceu score oficial 64 na escala 0-100.",
          "evidence_ids": [
            "CALC-OPPORTUNITY-SCORE-001"
          ]
        },
        {
          "statement": "O fixture registra três ângulos criativos sintéticos para investigação posterior.",
          "evidence_ids": [
            "OBS-FIXTURE-002"
          ]
        }
      ],
      "weaknesses": [
        {
          "statement": "A evidência de preço é sintética e classificada como de baixa qualidade.",
          "evidence_ids": [
            "OBS-FIXTURE-001"
          ]
        }
      ],
      "risks": [
        {
          "risk": "Economia da oferta não determinável com os campos disponíveis.",
          "severity": "high",
          "evidence_ids": []
        }
      ],
      "module_assessments": {
        "operator_context": "Compatibilidade com orçamento e capacidade operacional não determinável.",
        "validation": "Estrutura válida, com cobertura parcial de 70% declarada pelo fixture.",
        "offer_economics": "breakeven_not_determinable",
        "traffic": null,
        "trends": "O indicador sintético de demanda é 57; ele não representa vendas ou faturamento."
      },
      "evidence_ids": [
        "OBS-FIXTURE-001",
        "OBS-FIXTURE-002",
        "CALC-OPPORTUNITY-SCORE-001",
        "CALC-DEMAND-001"
      ]
    },
    {
      "position": 2,
      "opportunity_id": "OPP-002",
      "official_score": 58,
      "official_score_scale": "0-100",
      "official_score_rank": 2,
      "contextual_recommendation_rank": 2,
      "context_fit": "unknown",
      "strengths": [
        {
          "statement": "O motor determinístico forneceu score oficial 58 na escala 0-100.",
          "evidence_ids": [
            "CALC-OPPORTUNITY-SCORE-002"
          ]
        }
      ],
      "weaknesses": [
        {
          "statement": "As evidências de preço e prazo são sintéticas e classificadas como de baixa qualidade.",
          "evidence_ids": [
            "OBS-FIXTURE-003",
            "OBS-FIXTURE-004"
          ]
        }
      ],
      "risks": [
        {
          "risk": "Economia da oferta não determinável com os campos disponíveis.",
          "severity": "high",
          "evidence_ids": []
        }
      ],
      "module_assessments": {
        "operator_context": "Compatibilidade com orçamento e capacidade operacional não determinável.",
        "validation": "Estrutura válida, com cobertura parcial de 65% declarada pelo fixture.",
        "offer_economics": "breakeven_not_determinable",
        "traffic": null,
        "trends": "O indicador sintético de demanda é 53; ele não representa vendas ou faturamento."
      },
      "evidence_ids": [
        "OBS-FIXTURE-003",
        "OBS-FIXTURE-004",
        "CALC-OPPORTUNITY-SCORE-002",
        "CALC-DEMAND-002"
      ]
    }
  ],
  "favorable_evidence": [
    {
      "statement": "As duas oportunidades possuem scores oficiais e indicadores sintéticos de demanda produzidos pelo motor do fixture.",
      "evidence_ids": [
        "CALC-OPPORTUNITY-SCORE-001",
        "CALC-DEMAND-001",
        "CALC-OPPORTUNITY-SCORE-002",
        "CALC-DEMAND-002"
      ]
    }
  ],
  "contrary_evidence": [
    {
      "statement": "Todas as evidências observadas são sintéticas e de baixa qualidade, o que limita qualquer conclusão de mercado.",
      "evidence_ids": [
        "OBS-FIXTURE-001",
        "OBS-FIXTURE-002",
        "OBS-FIXTURE-003",
        "OBS-FIXTURE-004"
      ]
    }
  ],
  "inferences": [
    {
      "inference_id": "INF-001",
      "statement": "A quantidade sintética de três ângulos criativos pode justificar uma coleta controlada sobre variedade criativa, mas não comprova adequação ao Meta Ads.",
      "evidence_ids": [
        "OBS-FIXTURE-002"
      ],
      "certainty": "weak"
    },
    {
      "inference_id": "INF-002",
      "statement": "O prazo sintético de 12 dias pode representar uma restrição operacional se for confirmado por fonte rastreável.",
      "evidence_ids": [
        "OBS-FIXTURE-004"
      ],
      "certainty": "weak"
    }
  ],
  "source_conflicts": [],
  "missing_data": [
    {
      "field": "offer_economics",
      "importance": "critical",
      "reason": "Custos do produto, logística, taxas, impostos, margem e breakeven não foram fornecidos.",
      "collection_suggestion": "Coletar componentes financeiros com origem, moeda e data; enviar ao motor determinístico para cálculo."
    },
    {
      "field": "minimum_test_cost",
      "importance": "high",
      "reason": "Não é possível confirmar compatibilidade com o orçamento de R$ 500 sem custo mínimo calculado.",
      "collection_suggestion": "Definir o desenho do teste e calcular seu custo máximo em processo determinístico autorizado."
    },
    {
      "field": "source_validation",
      "importance": "high",
      "reason": "As observações pertencem a um fixture sintético e não representam fontes de mercado.",
      "collection_suggestion": "Substituir ou complementar os OBS-* sintéticos por fontes rastreáveis e datadas."
    }
  ],
  "calculation_warnings": [],
  "next_experiment": {
    "experiment_id": "EXP-FIXTURE-001",
    "objective": "Completar os dados econômicos e validar a origem das evidências antes de autorizar teste de mídia.",
    "hypothesis": "Se os componentes econômicos e as fontes forem coletados de forma rastreável, o motor poderá produzir indicadores suficientes para uma comparação contextual defensável.",
    "primary_variable": "completude_dos_dados_economicos",
    "control_variable": null,
    "minimum_action": "Coletar para ambas as oportunidades os custos do produto, logística, taxas e evidências de fornecedor com origem e data, sem executar campanha.",
    "maximum_budget": null,
    "currency": "BRL",
    "duration_days": null,
    "success_metrics": [
      "campos_financeiros_rastreaveis",
      "indicadores_calc_economicos_disponiveis",
      "qualidade_das_fontes"
    ],
    "success_conditions": [
      "Componentes econômicos essenciais presentes para ambas as oportunidades",
      "Indicadores econômicos produzidos pelo motor determinístico",
      "Evidências com origem e data verificáveis"
    ],
    "stop_conditions": [
      "Fonte sem origem rastreável",
      "Conflito material entre dados financeiros",
      "Necessidade de gasto não autorizado"
    ],
    "required_feedback_fields": [
      "product_cost",
      "logistics_cost",
      "fees",
      "taxes_if_provided",
      "calculated_margin",
      "calculated_breakeven",
      "source_reference",
      "collected_at"
    ]
  },
  "conditions_that_would_change_recommendation": [
    "Economia positiva segundo novos CALC-* autorizados",
    "Custo de teste calculado compatível com o orçamento de R$ 500",
    "Evidências rastreáveis com qualidade suficiente",
    "Risco crítico ou restrição operacional confirmada"
  ],
  "human_review": {
    "required": false,
    "reasons": []
  },
  "disclaimer": "Esta análise prioriza hipóteses e próximos testes com base nos dados fornecidos; não garante vendas, faturamento ou rentabilidade."
}
```

# Diagnóstico Executivo

A entrada é válida, porém parcial. A recomendação é `collect_more_data`, com confiança `inconclusive`. O motor forneceu scores oficiais para as duas oportunidades, mas as evidências são sintéticas e não existem dados suficientes sobre economia da oferta ou custo do teste. Nenhuma oportunidade foi declarada vencedora.

# Adequação ao Contexto do Operador

O fixture informa operador brasileiro, iniciante, com operação individual, Meta Ads como canal e orçamento de R$ 500. Como o custo mínimo de teste não foi fornecido nem calculado, a compatibilidade orçamentária é desconhecida. Também não há dados suficientes sobre capacidade criativa, logística ou margem.

# Ranking das Oportunidades

1. `OPP-001` — score oficial 64; ranking oficial 1; ranking contextual 1. Forças: score oficial e registro sintético de três ângulos criativos (`CALC-OPPORTUNITY-SCORE-001`, `OBS-FIXTURE-002`). Fraqueza: evidência de preço sintética e de baixa qualidade (`OBS-FIXTURE-001`).
2. `OPP-002` — score oficial 58; ranking oficial 2; ranking contextual 2. Força: score oficial (`CALC-OPPORTUNITY-SCORE-002`). Fraqueza: evidências sintéticas de preço e prazo, ambas de baixa qualidade (`OBS-FIXTURE-003`, `OBS-FIXTURE-004`).

# Oportunidade Recomendada

Não há oportunidade recomendada. Os scores oficiais foram preservados, mas não substituem dados econômicos, confirmação de fontes ou compatibilidade com o orçamento.

# Fatos Observados

- `OBS-FIXTURE-001`: preço fictício de R$ 79,90 para `OPP-001`, qualidade baixa.
- `OBS-FIXTURE-002`: três ângulos criativos fictícios para `OPP-001`, qualidade baixa.
- `OBS-FIXTURE-003`: preço fictício de R$ 69,90 para `OPP-002`, qualidade baixa.
- `OBS-FIXTURE-004`: prazo fictício de fornecedor de 12 dias para `OPP-002`, qualidade baixa.

# Indicadores Calculados

- `CALC-OPPORTUNITY-SCORE-001`: score oficial 64 em escala 0-100.
- `CALC-DEMAND-001`: sinal sintético de demanda 57 em escala 0-100.
- `CALC-OPPORTUNITY-SCORE-002`: score oficial 58 em escala 0-100.
- `CALC-DEMAND-002`: sinal sintético de demanda 53 em escala 0-100.

Os valores foram lidos e preservados sem recálculo.

# Interpretações

- `INF-001` (fraca): três ângulos criativos podem justificar coleta controlada sobre variedade criativa, mas não comprovam adequação ao Meta Ads (`OBS-FIXTURE-002`).
- `INF-002` (fraca): o prazo de 12 dias pode representar restrição operacional se for confirmado por fonte rastreável (`OBS-FIXTURE-004`).

# Evidências Favoráveis

Há scores oficiais e sinais sintéticos de demanda para as duas oportunidades (`CALC-OPPORTUNITY-SCORE-001`, `CALC-DEMAND-001`, `CALC-OPPORTUNITY-SCORE-002`, `CALC-DEMAND-002`).

# Evidências Contrárias

Todas as evidências observadas são sintéticas e de baixa qualidade (`OBS-FIXTURE-001`, `OBS-FIXTURE-002`, `OBS-FIXTURE-003`, `OBS-FIXTURE-004`).

# Economia da Oferta

`breakeven_not_determinable`. Não foram fornecidos custos de produto, logística, taxas, impostos, margem, breakeven, LTV ou upsell. Nenhum valor econômico foi calculado ou estimado pela IA.

# Tendências e Demanda

Os sinais `CALC-DEMAND-001` e `CALC-DEMAND-002` são sintéticos e relativos. Eles não representam volume absoluto, vendas, faturamento, conversão ou lucro.

# Principais Riscos

- Alto: economia da oferta não determinável para ambas as oportunidades.
- Alto: compatibilidade do teste com o orçamento de R$ 500 não determinável.
- Alto: fontes sintéticas não validam demanda real.

# Conflitos entre Fontes

Nenhum conflito foi declarado no fixture. A ausência de fontes independentes impede avaliar concordância real.

# Dados Ausentes

- Componentes econômicos da oferta: custo do produto, logística, taxas, impostos informados, margem e breakeven.
- Custo mínimo calculado do teste.
- Evidências de mercado rastreáveis e datadas.
- Dados de criativos, página e campanha reais; não aplicáveis nesta fase até nova coleta.

# Próximo Experimento

Hipótese: dados econômicos e fontes rastreáveis permitirão ao motor produzir indicadores suficientes para comparação. Ação: coletar os componentes financeiros e evidências de fornecedor para ambas as oportunidades, sem executar campanha. Duração e orçamento permanecem `null` porque não foram fornecidos ou calculados. O sucesso exige campos essenciais completos, CALC-* econômicos do motor e fontes verificáveis.

# Condições de Interrupção

- Fonte sem origem rastreável.
- Conflito material entre dados financeiros.
- Necessidade de gasto não autorizado.
- Detecção de risco crítico ou inconsistência de dados.

# O Que Faria a Recomendação Mudar

- Economia positiva segundo novos CALC-* autorizados.
- Custo de teste calculado compatível com R$ 500.
- Evidências rastreáveis com qualidade suficiente.
- Confirmação de risco crítico ou restrição operacional.

# Limitações

O fixture é integralmente sintético. Os sinais não comprovam vendas, faturamento, conversão ou rentabilidade. O ranking oficial não é garantia de sucesso, e nenhuma campanha, compra ou alteração de orçamento foi executada.
