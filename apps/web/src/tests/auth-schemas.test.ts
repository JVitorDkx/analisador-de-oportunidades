import { describe, expect, it } from "vitest";

import {
  loginSchema,
  registerSchema,
  tenantSelectionSchema,
  workspaceSchema,
} from "@/lib/auth/schemas";

describe("auth transport schemas", () => {
  it("accepts valid login and registration data", () => {
    expect(loginSchema.safeParse({ email: "analista@example.com", password: "segura123" }).success).toBe(true);
    expect(
      registerSchema.safeParse({
        displayName: "Analista",
        email: "analista@example.com",
        password: "segura123",
      }).success,
    ).toBe(true);
  });

  it("rejects extra privilege fields", () => {
    expect(
      registerSchema.safeParse({
        displayName: "Analista",
        email: "analista@example.com",
        password: "segura123",
        role: "admin",
      }).success,
    ).toBe(false);
  });

  it("validates workspace names and tenant identifiers strictly", () => {
    expect(workspaceSchema.safeParse({ name: "Operação Brasil" }).success).toBe(true);
    expect(tenantSelectionSchema.safeParse({ tenantId: "not-a-uuid" }).success).toBe(false);
    expect(
      tenantSelectionSchema.safeParse({
        tenantId: "31f863d1-80cb-4ab8-9e02-a15de5cb5737",
        isAdmin: true,
      }).success,
    ).toBe(false);
  });
});
