import { describe, expect, it } from "vitest";

import { parseSupabaseConfig } from "@/lib/supabase/config";

describe("Supabase public configuration", () => {
  it("accepts hosted HTTPS and loopback development endpoints", () => {
    expect(
      parseSupabaseConfig({
        url: "https://project.supabase.co",
        publishableKey: "sb_publishable_valid",
      }),
    ).toEqual({
      url: "https://project.supabase.co",
      publishableKey: "sb_publishable_valid",
    });
    expect(
      parseSupabaseConfig({
        url: "http://127.0.0.1:54321",
        publishableKey: "local-publishable-key",
      }),
    ).not.toBeNull();
  });

  it("rejects placeholders, insecure remote URLs and missing values", () => {
    expect(
      parseSupabaseConfig({
        url: "https://your-project-ref.supabase.co",
        publishableKey: "your-supabase-publishable-key",
      }),
    ).toBeNull();
    expect(
      parseSupabaseConfig({
        url: "http://remote.example.net",
        publishableKey: "sb_publishable_valid",
      }),
    ).toBeNull();
    expect(parseSupabaseConfig({})).toBeNull();
  });
});
