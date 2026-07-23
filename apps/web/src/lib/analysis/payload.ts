import type {
  AnalyzeRequest,
  CalculatedIndicatorRequest,
  ObservedEvidenceRequest,
} from "@opportunity-analyzer/typescript-sdk";

import type { AnalysisFormValues } from "./schema";

type PayloadMetadata = {
  generatedAt?: string;
  id?: string;
};

export function buildAnalyzeRequest(
  values: AnalysisFormValues,
  metadata: PayloadMetadata = {},
): AnalyzeRequest {
  const generatedAt = metadata.generatedAt ?? new Date().toISOString();
  const id = (metadata.id ?? crypto.randomUUID()).replaceAll("-", "").slice(0, 12).toUpperCase();
  const analysisId = `ANL-WEB-${id}`;
  const opportunityId = `OPP-WEB-${id}`;
  const sourceUrl = values.sourceUrl || "web-input://manual";
  const evidenceIds = {
    competitive: `OBS-WEB-COMPETITIVE-${id}`,
    demand: `OBS-WEB-DEMAND-${id}`,
    economics: `OBS-WEB-ECONOMICS-${id}`,
    fit: `OBS-WEB-FIT-${id}`,
    minimumTest: `OBS-WEB-MIN-TEST-${id}`,
    budget: `OBS-WEB-BUDGET-${id}`,
  };

  const observedEvidence: ObservedEvidenceRequest[] = [
    {
      evidence_id: evidenceIds.economics,
      opportunity_id: opportunityId,
      source_type: "operator_input",
      source_url: sourceUrl,
      collected_at: generatedAt,
      field: "economic_inputs",
      value: {
        selling_price: values.sellingPrice,
        product_cost: values.productCost,
        variable_fees: values.variableFees,
        taxes: values.taxes,
        shipping_subsidy: values.shippingSubsidy,
        other_variable_costs: values.otherVariableCosts,
        currency: "BRL",
      },
      value_type: "object",
      collection_method: "web_form",
      quality: "medium",
      notes: "Valores declarados pelo operador; não representam promessa de resultado.",
    },
    {
      evidence_id: evidenceIds.minimumTest,
      opportunity_id: opportunityId,
      source_type: "operator_input",
      source_url: sourceUrl,
      collected_at: generatedAt,
      field: "minimum_test_cost",
      value: values.minimumTestCost,
      value_type: "number",
      collection_method: "web_form",
      quality: "medium",
    },
    {
      evidence_id: evidenceIds.budget,
      opportunity_id: opportunityId,
      source_type: "operator_input",
      source_url: sourceUrl,
      collected_at: generatedAt,
      field: "operator_test_budget",
      value: values.testBudget,
      value_type: "number",
      collection_method: "web_form",
      quality: "high",
    },
    {
      evidence_id: evidenceIds.fit,
      opportunity_id: opportunityId,
      source_type: "operator_input",
      source_url: sourceUrl,
      collected_at: generatedAt,
      field: "operational_fit",
      value: values.operationalFit,
      value_type: "string",
      collection_method: "web_form",
      quality: "medium",
    },
    {
      evidence_id: evidenceIds.demand,
      opportunity_id: opportunityId,
      source_type: "analyst_input",
      source_url: sourceUrl,
      collected_at: generatedAt,
      field: "demand_signal_bundle",
      value: { normalized_score: values.demandScore, origin: "analyst_supplied" },
      value_type: "object",
      collection_method: "web_form",
      quality: "medium",
      notes: "Pontuação normalizada fornecida pelo analista; o navegador não a estima.",
    },
    {
      evidence_id: evidenceIds.competitive,
      opportunity_id: opportunityId,
      source_type: "analyst_input",
      source_url: sourceUrl,
      collected_at: generatedAt,
      field: "competitive_signal_bundle",
      value: { normalized_score: values.competitiveScore, origin: "analyst_supplied" },
      value_type: "object",
      collection_method: "web_form",
      quality: "medium",
      notes: "Pontuação normalizada fornecida pelo analista; o navegador não a estima.",
    },
  ];

  const normalizedInputs: Array<[string, string, number, string]> = [
    ["DEMAND", "demand_score", values.demandScore, evidenceIds.demand],
    ["ECONOMICS", "economics_score", values.economicsScore, evidenceIds.economics],
    [
      "COMPETITIVE",
      "competitive_attractiveness_score",
      values.competitiveScore,
      evidenceIds.competitive,
    ],
  ];
  const calculatedIndicators: CalculatedIndicatorRequest[] = normalizedInputs.map(
    ([indicatorName, field, value, sourceEvidenceId]) => ({
    indicator_id: `CALC-WEB-${indicatorName}-${id}`,
    opportunity_id: opportunityId,
    field,
    value,
    value_type: Number.isInteger(value) ? "integer" : "number",
    unit: "0-100",
    calculation_method: "analyst_supplied_normalized_input_v1",
    calculation_version: "WEB-INPUT-1.0.0",
    calculated_at: generatedAt,
    source_evidence_ids: [sourceEvidenceId],
    quality: "medium",
    warnings: [],
    }),
  );

  return {
    schema_version: "1.0.0",
    analysis_id: analysisId,
    generated_at: generatedAt,
    analysis_mode: "campaign_diagnosis",
    requested_output_language: "pt-BR",
    user_context: {
      country: "BR",
      language: "pt-BR",
      experience_level: "intermediate",
      business_model: values.businessModel,
      primary_channel: values.primaryChannel,
      test_budget_brl: values.testBudget,
      maximum_test_days: values.maximumTestDays,
      operational_constraints: [],
      excluded_categories: [],
      objectives: ["validate_demand_with_controlled_test"],
    },
    opportunities: [
      {
        opportunity_id: opportunityId,
        name: values.name,
        category: values.category,
        description: values.description || null,
        source_urls: [sourceUrl],
        observed_evidence: observedEvidence,
        calculated_indicators: calculatedIndicators,
        campaign_metrics: null,
        collection_errors: [],
        risk_flags: [],
        data_quality: {
          status: "complete",
          coverage_percent: 100,
          freshness: "current",
          source_agreement: "medium",
        },
        scoring_context: {
          economic_inputs_evidence_id: evidenceIds.economics,
          minimum_test_cost_evidence_id: evidenceIds.minimumTest,
          operator_budget_evidence_id: evidenceIds.budget,
          operational_fit_evidence_id: evidenceIds.fit,
          logistics_evidence_id: null,
          independent_source_ids: [sourceUrl],
          calculation_quality: "medium",
        },
      },
    ],
    score_configuration: {
      version: "SCORE-0.1.0",
      weights: {},
      calculation_timestamp: generatedAt,
      engine: "deterministic-score-engine",
    },
  };
}
