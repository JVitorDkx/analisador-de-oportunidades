"use client";

import { createBrowserClient } from "@supabase/ssr";

import { getSupabaseConfig } from "./config";

export function createClient() {
  const config = getSupabaseConfig();
  if (!config) {
    throw new Error("Supabase public configuration is unavailable.");
  }

  return createBrowserClient(config.url, config.publishableKey);
}
