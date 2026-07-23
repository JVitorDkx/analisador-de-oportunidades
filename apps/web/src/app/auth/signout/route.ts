import { revalidatePath } from "next/cache";
import { type NextRequest, NextResponse } from "next/server";

import { getSupabaseConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  if (getSupabaseConfig()) {
    const supabase = await createClient();
    const { data: claimsData } = await supabase.auth.getClaims();
    const claims = claimsData?.claims;
    if (claims) {
      await supabase.auth.signOut();
    }
  }

  revalidatePath("/", "layout");
  return NextResponse.redirect(new URL("/login", request.url), { status: 302 });
}
