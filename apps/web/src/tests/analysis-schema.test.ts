import { describe, expect, it } from "vitest";

import {
  analysisFormSchema,
  syntheticAnalysisExample,
} from "@/lib/analysis/schema";

describe("new analysis form contract", () => {
  it("accepts the official synthetic web example", () => {
    expect(analysisFormSchema.safeParse(syntheticAnalysisExample).success).toBe(true);
  });

  it("rejects unknown authoritative fields and out-of-range scores", () => {
    expect(
      analysisFormSchema.safeParse({
        ...syntheticAnalysisExample,
        official_score: 100,
      }).success,
    ).toBe(false);
    expect(
      analysisFormSchema.safeParse({
        ...syntheticAnalysisExample,
        demandScore: 101,
      }).success,
    ).toBe(false);
  });

  it("rejects negative economics and invalid remote source URLs", () => {
    expect(
      analysisFormSchema.safeParse({
        ...syntheticAnalysisExample,
        productCost: -1,
      }).success,
    ).toBe(false);
    expect(
      analysisFormSchema.safeParse({
        ...syntheticAnalysisExample,
        sourceUrl: "not a URL",
      }).success,
    ).toBe(false);
  });

  it("accepts comma or point decimal formatting", () => {
    const comma = analysisFormSchema.parse({
      ...syntheticAnalysisExample,
      sellingPrice: "149,90",
      productCost: "1.234,56",
    });
    const point = analysisFormSchema.parse({
      ...syntheticAnalysisExample,
      sellingPrice: "149.90",
      productCost: "1234.56",
    });

    expect(comma.sellingPrice).toBe(149.9);
    expect(comma.productCost).toBe(1234.56);
    expect(point.sellingPrice).toBe(149.9);
    expect(point.productCost).toBe(1234.56);
  });
});
