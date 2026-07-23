import Link from "next/link";

import { registerAction } from "@/app/(auth)/actions";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthShell } from "@/components/auth/auth-shell";

export default function RegisterPage() {
  return (
    <AuthShell
      eyebrow="Novo acesso"
      title="Crie sua conta"
      description="Seu perfil será vinculado ao Supabase Auth; workspaces e dados permanecem protegidos por RLS."
    >
      <AuthForm action={registerAction} mode="register" />
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Já possui uma conta?{" "}
        <Link className="font-semibold text-foreground underline-offset-4 hover:underline" href="/login">
          Entrar
        </Link>
      </p>
    </AuthShell>
  );
}
