import { describe, expect, it } from "vitest";

import { isDemoMode } from "@/lib/demo-mode";

describe("demo mode boundary", () => {
  it("requires an explicit local flag", () => {
    expect(isDemoMode({})).toBe(false);
    expect(isDemoMode({ APP_ENV: "development", ENABLE_DEMO_MODE: "true" })).toBe(true);
  });

  it("cannot be enabled in production", () => {
    expect(isDemoMode({ APP_ENV: "production", ENABLE_DEMO_MODE: "true" })).toBe(false);
  });
});
