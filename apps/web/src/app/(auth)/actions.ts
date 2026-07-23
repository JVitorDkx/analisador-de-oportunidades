"use server";

import { revalidatePath } from "next/cache";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { loginSchema, registerSchema } from "@/lib/auth/schemas";
import { getSupabaseConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

export type AuthActionState = {
  error?: string;
  message?: string;
};

export async function loginAction(
  _previousState: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  const parsed = loginSchema.safeParse({
    email: formData.get("email"),
    password: formData.get("password"),
  });

  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? "Revise os dados informados." };
  }

  if (!getSupabaseConfig()) {
    return { error: "Configure o Supabase no arquivo .env.local para autenticar." };
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword(parsed.data);
  if (error) {
    return { error: "Não foi possível entrar. Confira suas credenciais e tente novamente." };
  }

  revalidatePath("/", "layout");
  redirect("/workspace");
}

export async function registerAction(
  _previousState: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  const parsed = registerSchema.safeParse({
    displayName: formData.get("displayName"),
    email: formData.get("email"),
    password: formData.get("password"),
  });

  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? "Revise os dados informados." };
  }

  if (!getSupabaseConfig()) {
    return { error: "Configure o Supabase no arquivo .env.local para criar uma conta." };
  }

  const requestHeaders = await headers();
  const origin = requestHeaders.get("origin") ?? process.env.NEXT_PUBLIC_SITE_URL;
  const supabase = await createClient();
  const { error } = await supabase.auth.signUp({
    email: parsed.data.email,
    password: parsed.data.password,
    options: {
      data: { display_name: parsed.data.displayName },
      emailRedirectTo: origin ? `${origin}/auth/confirm` : undefined,
    },
  });

  if (error) {
    return { error: "Não foi possível concluir o cadastro. Revise os dados e tente novamente." };
  }

  return { message: "Cadastro recebido. Verifique seu e-mail para confirmar a conta." };
}
