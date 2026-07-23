"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { tenantSelectionSchema, workspaceSchema } from "@/lib/auth/schemas";
import { getSupabaseConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

export type WorkspaceActionState = {
  error?: string;
};

export async function createWorkspaceAction(
  _previousState: WorkspaceActionState,
  formData: FormData,
): Promise<WorkspaceActionState> {
  const parsed = workspaceSchema.safeParse({ name: formData.get("name") });
  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? "Nome de workspace inválido." };
  }

  if (!getSupabaseConfig()) {
    return { error: "Configure o Supabase para criar um workspace real." };
  }

  const supabase = await createClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  const claims = claimsData?.claims;
  const userId = typeof claims?.sub === "string" ? claims.sub : null;
  if (!userId) {
    redirect("/login");
  }

  const { data, error } = await supabase
    .from("tenants")
    .insert({ name: parsed.data.name, owner_user_id: userId })
    .select("id")
    .single();

  if (error || !data) {
    return { error: "Não foi possível criar o workspace. Tente novamente." };
  }

  const cookieStore = await cookies();
  cookieStore.set("od_tenant_id", data.id, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });
  redirect("/");
}

export async function selectWorkspaceAction(formData: FormData) {
  const parsed = tenantSelectionSchema.safeParse({ tenantId: formData.get("tenantId") });
  if (!parsed.success || !getSupabaseConfig()) {
    redirect("/workspace?error=invalid_workspace");
  }

  const supabase = await createClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  const claims = claimsData?.claims;
  const userId = typeof claims?.sub === "string" ? claims.sub : null;
  if (!userId) {
    redirect("/login");
  }

  const { data } = await supabase
    .from("tenant_memberships")
    .select("tenant_id")
    .eq("tenant_id", parsed.data.tenantId)
    .eq("user_id", userId)
    .maybeSingle();

  if (!data) {
    redirect("/workspace?error=workspace_not_available");
  }

  const cookieStore = await cookies();
  cookieStore.set("od_tenant_id", parsed.data.tenantId, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });
  redirect("/");
}
