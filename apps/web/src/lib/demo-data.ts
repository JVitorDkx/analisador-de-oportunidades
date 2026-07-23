/**
 * Visual preview sourced from fixtures/cases/opportunity_viable.json and its
 * deterministic SCORE-0.1.0 result. It is never presented as customer data.
 */
export const demoOpportunity = {
  source: "fixtures/cases/opportunity_viable.json",
  analysisId: "ANL-CASE-VIABLE-001",
  name: "Organizador modular demonstrativo",
  category: "Casa e organização",
  officialScore: 90.4,
  status: "Análise concluída",
  recommendation: "Priorizar teste controlado",
  confidence: "Alta",
  coverage: 95,
  evidenceCount: 7,
  killSwitches: 0,
  budget: "R$ 1.000",
  duration: "7 dias",
  dimensions: [
    { label: "Demanda observável", value: 92, weight: "30%", id: "CALC-VIABLE-DEMAND-SCORE" },
    { label: "Economia da oferta", value: 88, weight: "30%", id: "CALC-VIABLE-ECONOMICS-SCORE" },
    {
      label: "Atratividade competitiva",
      value: 82,
      weight: "20%",
      id: "CALC-VIABLE-COMPETITIVE-SCORE",
    },
    { label: "Adequação operacional", value: 100, weight: "20%", id: "CALC-OPERATIONAL-FIT" },
  ],
} as const;
