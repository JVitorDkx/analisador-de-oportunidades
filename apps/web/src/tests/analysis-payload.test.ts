import { describe, expect, it } from "vitest";

import { buildAnalyzeRequest } from "@/lib/analysis/payload";
import { syntheticAnalysisExample } from "@/lib/analysis/schema";

const metadata = {
  generatedAt: "2026-07-22T12:00:00.000Z",
  id: "12345678-abcd-4321-bbbb-1234567890ab",
};

describe("FastAPI analysis payload builder", () => {
  it("builds the frozen input contract without an authoritative score", () => {
    const result = buildAnalyzeRequest(syntheticAnalysisExample, metadata);
    const opportunity = result.opportunities[0];

    expect(result.analysis_id).toBe("ANL-WEB-12345678ABCD");
    expect(result.schema_version).toBe("1.0.0");
    expect(result.score_configuration.version).toBe("SCORE-0.1.0");
    expect(opportunity).not.toHaveProperty("official_score");
    expect(opportunity?.calculated_indicators.map((item) => item.value)).toEqual([92, 88, 82]);
    expect(opportunity?.calculated_indicators.map((item) => item.value_type)).toEqual([
      "integer",
      "integer",
      "integer",
    ]);
    expect(opportunity?.calculated_indicators.every((item) => item.warnings.length === 0)).toBe(true);
  });

  it("preserves declared economic values and their evidence references", () => {
    const result = buildAnalyzeRequest(syntheticAnalysisExample, metadata);
    const opportunity = result.opportunities[0]!;
    const economics = opportunity.observed_evidence.find((item) => item.field === "economic_inputs");

    expect(economics?.value).toMatchObject({
      selling_price: 149.9,
      product_cost: 35,
      currency: "BRL",
    });
    expect(opportunity.scoring_context?.economic_inputs_evidence_id).toBe(economics?.evidence_id);
    expect(opportunity.source_urls).toEqual(["web-input://manual"]);
  });

  it("does not mutate the submitted form values", () => {
    const values = structuredClone(syntheticAnalysisExample);
    const before = structuredClone(values);
    buildAnalyzeRequest(values, metadata);
    expect(values).toEqual(before);
  });
});
