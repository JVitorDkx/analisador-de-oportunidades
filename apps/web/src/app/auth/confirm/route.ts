import type { EmailOtpType } from "@supabase/supabase-js";
import { type NextRequest, NextResponse } from "next/server";

import { getSupabaseConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const tokenHash = request.nextUrl.searchParams.get("token_hash");
  const type = request.nextUrl.searchParams.get("type") as EmailOtpType | null;
  const destination = new URL("/workspace", request.url);

  if (!getSupabaseConfig() || !tokenHash || !type) {
    destination.pathname = "/login";
    destination.searchParams.set("error", "invalid_confirmation");
    return NextResponse.redirect(destination);
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.verifyOtp({ token_hash: tokenHash, type });
  if (error) {
    destination.pathname = "/login";
    destination.searchParams.set("error", "invalid_confirmation");
  }

  return NextResponse.redirect(destination);
}
